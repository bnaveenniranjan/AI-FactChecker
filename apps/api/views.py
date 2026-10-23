"""
REST API views for the AI Government Scheme Fact Checker.

All external API calls (Gemini, source retrieval) happen in the service layer.
Views only handle request/response marshalling, validation, and HTTP concerns.
"""

from __future__ import annotations

import logging
import time
import json

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.schemes.models import Scheme
from apps.budgets.models import BudgetRecord
from apps.timeline.models import TimelineEvent
from apps.leadership.models import SchemeResponsibility
from apps.factcheck.models import Claim, ClaimEvidence, FactCheckResult
from apps.search.models import ResearchJob
from apps.sources.models import Source

from .serializers import (
    SchemeListSerializer,
    SchemeDetailSerializer,
    BudgetRecordSerializer,
    TimelineEventSerializer,
    SchemeResponsibilitySerializer,
    ClaimSerializer,
    FactCheckResultSerializer,
    ResearchJobSerializer,
    ResearchRequestSerializer,
    FactCheckRequestSerializer,
    SourceSerializer,
)

log = logging.getLogger('apps.api')


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------

class ResearchView(APIView):
    """
    POST /api/v1/research/

    Start or execute a scheme research request.
    Returns the research job with status and result (if synchronous).
    """

    def post(self, request):
        # Attempt to parse JSON payload safely, handling potential BOM or malformed data
        try:
            data = request.data
        except Exception as exc:
            # Fallback: manually load raw body, stripping possible UTF-8 BOM
            try:
                raw = request.body.decode('utf-8-sig')
                data = json.loads(raw)
            except Exception as exc2:
                log.error('JSON parse error in research request: %s / %s', exc, exc2)
                return Response(
                    {'detail': f'Invalid JSON payload: {exc2}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        # Validate input using serializer
        serializer = ResearchRequestSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data['query']

        # Create a job record
        job = ResearchJob.objects.create(query=query)

        try:
            from apps.search.orchestrator import orchestrator
            result = orchestrator.execute(query, job=job)
            job.refresh_from_db()
            return Response(ResearchJobSerializer(job).data, status=status.HTTP_201_CREATED)
        except Exception as exc:
            log.error('Research pipeline failed: %s', exc, exc_info=True)
            # Job is already marked failed inside orchestrator.execute
            job.refresh_from_db()
            return Response(
                {
                    'error': 'Research failed. Please try again.',
                    'job': ResearchJobSerializer(job).data,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class ResearchDetailView(generics.RetrieveAPIView):
    """GET /api/v1/research/{id}/ — Retrieve research job status and results."""

    queryset = ResearchJob.objects.all()
    serializer_class = ResearchJobSerializer


# ---------------------------------------------------------------------------
# Schemes
# ---------------------------------------------------------------------------

class SchemeListView(generics.ListAPIView):
    """
    GET /api/v1/schemes/

    Search schemes. Supports ?q=<query>, ?category=<cat>, ?jurisdiction=<j>.
    """

    serializer_class = SchemeListSerializer

    def get_queryset(self):
        qs = Scheme.objects.all()
        q = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        jurisdiction = self.request.query_params.get('jurisdiction', '').strip()

        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(abbreviation__icontains=q) | qs.filter(aliases__alias__icontains=q)
            qs = qs.distinct()
        if category:
            qs = qs.filter(category=category)
        if jurisdiction:
            qs = qs.filter(jurisdiction=jurisdiction)
        return qs.order_by('name')


class SchemeDetailView(generics.RetrieveAPIView):
    """GET /api/v1/schemes/{id}/ — Full scheme details."""

    queryset = Scheme.objects.prefetch_related('aliases', 'benefits', 'eligibility_rules')
    serializer_class = SchemeDetailSerializer
    lookup_field = 'pk'


class SchemeTimelineView(APIView):
    """
    GET /api/v1/schemes/{id}/timeline/

    Chronological events for a scheme.
    Supports ?event_type=<type>&year=<year> filters.
    """

    def get(self, request, pk):
        scheme = get_object_or_404(Scheme, pk=pk)
        qs = TimelineEvent.objects.filter(scheme=scheme).select_related(
            'government', 'responsible_ministry', 'responsible_leader',
        ).prefetch_related('sources')

        event_type = request.query_params.get('event_type', '').strip()
        year = request.query_params.get('year', '').strip()

        if event_type:
            qs = qs.filter(event_type=event_type)
        if year:
            try:
                qs = qs.filter(event_date__year=int(year))
            except ValueError:
                pass

        serializer = TimelineEventSerializer(qs.order_by('event_date'), many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class SchemeBudgetView(APIView):
    """GET /api/v1/schemes/{id}/budgets/ — Budget history for a scheme."""

    def get(self, request, pk):
        scheme = get_object_or_404(Scheme, pk=pk)
        qs = BudgetRecord.objects.filter(scheme=scheme).select_related('source').order_by('financial_year_start')
        serializer = BudgetRecordSerializer(qs, many=True)
        return Response({'count': qs.count(), 'results': serializer.data})


class SchemeLeadershipView(APIView):
    """GET /api/v1/schemes/{id}/leadership/ — Historical leadership for a scheme."""

    def get(self, request, pk):
        from django.db.models import Q
        scheme = get_object_or_404(Scheme, pk=pk)
        qs = SchemeResponsibility.objects.filter(scheme=scheme).select_related(
            'ministerial_tenure__leader',
            'ministerial_tenure__ministry',
            'ministerial_tenure__government',
            'ministry',
        ).order_by('effective_from')

        seen_leaders = set()
        results = []
        if qs.exists():
            serializer = SchemeResponsibilitySerializer(qs, many=True)
            for item in serializer.data:
                leader = item.get('ministerial_tenure', {}).get('leader', {})
                name = leader.get('full_name') if leader else None
                if name:
                    seen_leaders.add(name.lower())
                results.append(item)

        # Supplement with distinct leaders and ministers recorded in timeline events
        events_with_leaders = scheme.timeline_events.filter(
            Q(responsible_leader__isnull=False) | Q(responsible_ministry__isnull=False)
        ).select_related(
            'responsible_leader__party',
            'responsible_ministry',
            'government__ruling_party'
        ).order_by('event_date')

        for idx, ev in enumerate(events_with_leaders, start=len(results) + 1):
            leader_name = ev.responsible_leader.full_name if ev.responsible_leader else None
            if leader_name and leader_name.lower() in seen_leaders:
                continue
            if leader_name:
                seen_leaders.add(leader_name.lower())
            elif not results:
                leader_name = 'Union Executive'
            else:
                continue

            min_name = ev.responsible_ministry.name if ev.responsible_ministry else 'Administering Ministry'
            role = 'Prime Minister' if 'Prime Minister' in (ev.title + (leader_name or '')) else ('Union Minister' if 'Minister' in (ev.title + (leader_name or '')) else 'Minister In-Charge')
            results.append({
                'id': idx,
                'responsibility_type': ev.event_type,
                'leader_name': leader_name,
                'role': role,
                'portfolio': f'{role} — {min_name}' if min_name else role,
                'ministry': min_name,
                'party': ev.responsible_leader.party.abbreviation if ev.responsible_leader and ev.responsible_leader.party else (ev.government.ruling_party.abbreviation if ev.government and ev.government.ruling_party else 'Central Government'),
                'government': ev.government.name if ev.government else 'Government of India',
                'effective_from': str(ev.event_date) if ev.event_date else str(scheme.launch_date or ''),
                'effective_to': None,
                'notes': ev.title,
                'ministerial_tenure': {
                    'leader': {
                        'full_name': leader_name,
                        'party': {
                            'name': ev.responsible_leader.party.name,
                            'abbreviation': ev.responsible_leader.party.abbreviation
                        } if ev.responsible_leader and ev.responsible_leader.party else None,
                    },
                    'ministry': {'name': min_name},
                    'role': role,
                    'portfolio': f'{role} — {min_name}' if min_name else role,
                    'tenure_start': str(ev.event_date) if ev.event_date else None,
                    'tenure_end': None,
                }
            })

        return Response({'count': len(results), 'results': results})


# ---------------------------------------------------------------------------
# Fact-checking
# ---------------------------------------------------------------------------

class FactCheckView(APIView):
    """
    POST /api/v1/fact-check/

    Verify a user-supplied factual claim against retrieved sources.
    """

    def post(self, request):
        serializer = FactCheckRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        claim_text = serializer.validated_data['claim']
        scheme_id = serializer.validated_data.get('scheme_id')

        scheme = None
        if scheme_id:
            scheme = get_object_or_404(Scheme, pk=scheme_id)

        from apps.sources.retrieval import fetch_url_content
        from apps.ai_service.client import gemini_client
        from apps.sources.models import Source, EvidenceExcerpt
        from django.utils import timezone

        start_time = time.monotonic()

        # Create claim record
        claim = Claim.objects.create(
            claim_text=claim_text,
            scheme=scheme,
        )

        try:
            # Build candidate URLs from scheme name or generic search
            scheme_name = scheme.name if scheme else claim_text[:50]
            candidate_urls = [
                f'https://pib.gov.in/allRel.aspx?query={scheme_name}',
                f'https://myscheme.gov.in/schemes',
            ]

            passages = []
            for url in candidate_urls[:5]:
                content = fetch_url_content(url)
                if content and content.get('text'):
                    passages.append(content)

            verdict = gemini_client.fact_check_claim(claim_text, passages, allow_fallback=True)

            # Persist verdict to claim
            claim.verdict = verdict.verdict.value
            claim.explanation = verdict.explanation
            claim.confidence = verdict.confidence.value
            claim.confidence_explanation = verdict.confidence_explanation
            claim.verified_at = timezone.now()
            claim.save()

            # Persist evidence links
            all_evidence = verdict.supporting_evidence + verdict.contradicting_evidence
            for ev in all_evidence:
                source, _ = Source.objects.get_or_create(
                    url=ev.source_url,
                    defaults={
                        'title': ev.source_title or '',
                        'publisher': ev.publisher or '',
                    },
                )
                excerpt = EvidenceExcerpt.objects.create(
                    source=source,
                    text=ev.text[:2000],
                    scheme=scheme,
                )
                ClaimEvidence.objects.create(
                    claim=claim,
                    excerpt=excerpt,
                    source=source,
                    stance=ev.stance,
                    publication_date=None,
                )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            result = FactCheckResult.objects.create(
                claim=claim,
                ai_model_used=gemini_client._model_name,
                raw_ai_response=verdict.model_dump(),
                processing_time_ms=elapsed_ms,
                sources_searched=len(candidate_urls),
                sources_used=len(passages),
            )

            return Response(
                FactCheckResultSerializer(result).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            log.error('Fact-check failed: %s', exc, exc_info=True)
            claim.verdict = Claim.STATUS_INSUFFICIENT
            claim.explanation = 'Fact-checking failed due to a technical error.'
            claim.save()
            return Response(
                {'error': 'Fact-check failed. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class SourceDetailView(generics.RetrieveAPIView):
    """GET /api/v1/sources/{id}/ — Source metadata and evidence."""

    queryset = Source.objects.prefetch_related('excerpts')
    serializer_class = SourceSerializer


# ---------------------------------------------------------------------------
# Gemini AI Configuration
# ---------------------------------------------------------------------------

class GeminiStatusView(APIView):
    """GET /api/v1/gemini/status/ — Check Gemini API status and active model."""

    def get(self, request):
        from apps.ai_service.client import gemini_client
        configured = gemini_client.is_configured()
        masked_key = ''
        if configured and gemini_client._api_key:
            k = gemini_client._api_key.strip()
            masked_key = f'{k[:4]}...{k[-4:]}' if len(k) >= 8 else '****'

        return Response({
            'configured': configured,
            'model': gemini_client._model_name,
            'status': 'Connected (Live Google Gemini)' if configured else 'Demo / Offline Synthesis Mode',
            'masked_key': masked_key,
        })


class GeminiConfigureView(APIView):
    """POST /api/v1/gemini/configure/ — Set Gemini API key and model dynamically."""

    def post(self, request):
        api_key = request.data.get('api_key', '').strip()
        model_name = request.data.get('model', '').strip()

        if not api_key:
            return Response({'error': 'api_key is required'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.ai_service.client import gemini_client
        import os
        from django.conf import settings

        # Update both OpenRouter and legacy Gemini env vars for compatibility
        gemini_client.set_api_key(api_key)
        if model_name:
            gemini_client._model_name = model_name

        os.environ['OPENROUTER_API_KEY'] = api_key
        os.environ['GEMINI_API_KEY'] = api_key  # keep for backward compatibility
        setattr(settings, 'OPENROUTER_API_KEY', api_key)
        setattr(settings, 'GEMINI_API_KEY', api_key)

        log.info('OpenRouter (and legacy Gemini) API key updated at runtime (in-memory only).')

        return Response({
            'success': True,
            'message': 'OpenRouter AI connected successfully! The key is active for this session.',
            'model': gemini_client._model_name,
            'configured': True,
        })
