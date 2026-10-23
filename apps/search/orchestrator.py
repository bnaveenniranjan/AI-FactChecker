"""
Research orchestrator — coordinates source discovery, retrieval, and AI synthesis.

Pipeline:
  1. Normalize query.
  2. Check cache for fresh result.
  3. Discover candidate source URLs from scheme name / query.
  4. Fetch accessible content from allowlisted sources.
  5. Send retrieved evidence to Gemini for synthesis.
  6. Validate and persist result.
  7. Store retrieved sources and evidence excerpts.
  8. Update cache.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import timedelta
from typing import List, Optional
from urllib.parse import quote_plus

from django.conf import settings
from django.utils import timezone

log = logging.getLogger('apps.search')

# Candidate URL patterns for common Indian government sources
# {scheme} is replaced with the URL-encoded scheme name / abbreviation
SOURCE_URL_TEMPLATES = [
    'https://pib.gov.in/allRel.aspx?query={scheme}',
    'https://india.gov.in/spotlight/{scheme}',
    'https://myscheme.gov.in/schemes/{scheme}',
    'https://vikaspedia.in/social-welfare/{scheme}',
]

PIB_SEARCH_TEMPLATE = 'https://pib.gov.in/search.aspx?reg=3&lang=1&kw={scheme}'


def normalize_query(query: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace."""
    q = query.lower()
    q = re.sub(r'[^\w\s]', ' ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q


def make_cache_key(normalized_query: str) -> str:
    """SHA-256 hash of normalized query for use as cache key."""
    return hashlib.sha256(normalized_query.encode()).hexdigest()


def _get_candidate_urls(scheme_name: str, query: str) -> List[str]:
    """
    Build candidate source URLs from the scheme name.

    These are best-effort guesses — many will return 404.
    The fetcher handles failures gracefully.
    """
    slug = quote_plus(scheme_name.lower().replace(' ', '-'))
    kw = quote_plus(scheme_name)

    urls = [
        f'https://en.wikipedia.org/wiki/{quote_plus(scheme_name.replace(" ", "_"))}',
        f'https://pib.gov.in/allRel.aspx?query={kw}',
        f'https://pib.gov.in/search.aspx?reg=3&lang=1&kw={kw}',
        f'https://myscheme.gov.in/schemes',
        f'https://india.gov.in/spotlight/{slug}',
        f'https://vikaspedia.in/social-welfare/{slug}',
        f'https://prsindia.org/policy?term={kw}',
        f'https://indiabudget.gov.in/doc/eb/stat.pdf',
        f'https://dea.gov.in/budget',
    ]
    return urls


class ResearchOrchestrator:
    """
    Orchestrates the full research pipeline for a scheme query.

    Uses lazy imports to avoid circular dependencies between apps.
    """

    def __init__(self):
        self._gemini = None

    @property
    def gemini(self):
        if self._gemini is None:
            from apps.ai_service.client import gemini_client
            self._gemini = gemini_client
        return self._gemini

    def _get_fresh_cache(self, cache_key: str):
        """Return a fresh cache entry or None."""
        from .models import ResearchCache
        try:
            entry = ResearchCache.objects.get(cache_key=cache_key)
            if entry.is_fresh:
                log.info('Cache hit for key %s…', cache_key[:8])
                return entry
        except ResearchCache.DoesNotExist:
            pass
        return None

    def _store_sources(self, passages: List[dict], scheme=None):
        """Persist fetched sources to the database, deduplicating by URL."""
        from apps.sources.models import Source, EvidenceExcerpt
        stored = []
        for p in passages:
            url = p.get('url', '')
            if not url:
                continue
            source, _ = Source.objects.get_or_create(
                url=url,
                defaults={
                    'title': p.get('title', ''),
                    'publisher': p.get('publisher', ''),
                    'published_date': None,
                    'retrieved_at': timezone.now(),
                    'source_category': Source.CATEGORY_OFFICIAL_PORTAL,
                },
            )
            if scheme:
                source.schemes.add(scheme)

            text = p.get('text', '')
            if text:
                EvidenceExcerpt.objects.get_or_create(
                    source=source,
                    text=text[:2000],
                    defaults={'scheme': scheme},
                )
            stored.append(source)
        return stored

    def _update_cache(self, cache_key: str, normalized_query: str, result_dict: dict, scheme=None):
        """Update the research cache with a fresh result."""
        from .models import ResearchCache
        ttl = getattr(settings, 'RESEARCH_CACHE_TTL_SECONDS', 3600)
        expires_at = timezone.now() + timedelta(seconds=ttl)

        ResearchCache.objects.update_or_create(
            cache_key=cache_key,
            defaults={
                'normalized_query': normalized_query,
                'scheme': scheme,
                'result': result_dict,
                'expires_at': expires_at,
            },
        )

    def execute(self, query: str, job=None) -> dict:
        """
        Run the full research pipeline.

        Args:
            query: User's search query.
            job: Optional ResearchJob instance to update with progress.

        Returns:
            ResearchResultSchema serialized as dict.
        """
        from apps.sources.retrieval import fetch_url_content

        normalized = normalize_query(query)
        cache_key = make_cache_key(normalized)

        # Step 1: Check cache
        cached = self._get_fresh_cache(cache_key)
        if cached:
            if job:
                job.scheme = cached.scheme
                job.mark_completed(cached.result)
            return cached.result

        if job:
            job.mark_started()

        # Step 2: Discover candidate URLs
        # Use a simple heuristic: extract likely scheme name from query
        scheme_name = self._extract_scheme_name(query)
        candidate_urls = _get_candidate_urls(scheme_name, query)
        log.info('Discovered %d candidate URLs for query: %s', len(candidate_urls), query[:60])

        # Step 3: Fetch sources — higher limit gives Gemini more timeline context
        passages = []
        for url in candidate_urls[:12]:  # Increased from 8 to 12 for fuller timeline coverage
            content = fetch_url_content(url)
            if content and content.get('text'):
                passages.append(content)
                log.debug('Fetched source: %s', url)

        if job:
            job.sources_found = len(candidate_urls)
            job.sources_fetched = len(passages)
            job.save(update_fields=['sources_found', 'sources_fetched'])

        log.info('Fetched %d/%d sources for query: %s', len(passages), len(candidate_urls), query[:60])

        # Step 4: Look up or create scheme in DB
        scheme = self._find_or_create_scheme(scheme_name) if scheme_name else None

        # Step 5: Persist sources
        self._store_sources(passages, scheme=scheme)

        # Step 6: Call Gemini with evidence
        try:
            result = self.gemini.research_scheme(query, passages, allow_fallback=True)
            result_dict = result.model_dump()
        except Exception as exc:
            log.error('Gemini research failed: %s', exc, exc_info=True)
            if job:
                job.mark_failed(str(exc))
            raise

        # Step 7: Enrich database records with research result
        if scheme and result_dict:
            self._enrich_scheme_data(scheme, result_dict)

        # Step 8: Update cache
        self._update_cache(cache_key, normalized, result_dict, scheme=scheme)

        if job:
            job.scheme = scheme
            job.mark_completed(result_dict)

        return result_dict

    def _enrich_scheme_data(self, scheme, result_dict: dict):
        """Enrich Scheme, TimelineEvent, and BudgetRecord database models."""
        from apps.timeline.models import TimelineEvent
        from apps.budgets.models import BudgetRecord
        from apps.leadership.models import Leader, MinisterialTenure, MinistryOrDepartment, SchemeResponsibility, Government

        overview = result_dict.get('overview') or {}
        if overview:
            if overview.get('launch_date') and not scheme.launch_date:
                try:
                    scheme.launch_date = overview.get('launch_date')
                except Exception:
                    pass
            if overview.get('original_objectives') and not scheme.original_objectives:
                scheme.original_objectives = overview.get('original_objectives')
            if overview.get('intended_beneficiaries') and not scheme.intended_beneficiaries:
                scheme.intended_beneficiaries = overview.get('intended_beneficiaries')
            if overview.get('application_portal') and not scheme.application_portal:
                scheme.application_portal = overview.get('application_portal')
            scheme.save()

        # Timeline events
        for ev in result_dict.get('timeline_events', []):
            try:
                min_obj = None
                min_name = ev.get('responsible_ministry')
                if min_name:
                    min_obj, _ = MinistryOrDepartment.objects.get_or_create(
                        name=min_name[:300]
                    )

                leader_obj = None
                leader_name = ev.get('responsible_leader')
                if leader_name:
                    leader_obj, _ = Leader.objects.get_or_create(
                        full_name=leader_name[:300]
                    )

                event_date = ev.get('event_date')
                if not event_date:
                    event_date = timezone.now().date()

                TimelineEvent.objects.get_or_create(
                    scheme=scheme,
                    title=ev.get('title', '')[:300],
                    defaults={
                        'event_type': ev.get('event_type') or TimelineEvent.EVENT_OTHER,
                        'event_date': event_date,
                        'description': ev.get('description', ''),
                        'responsible_ministry': min_obj,
                        'responsible_leader': leader_obj,
                        'verification_status': TimelineEvent.VERIFICATION_VERIFIED,
                    }
                )
            except Exception as e:
                log.debug('Could not persist timeline event: %s', e)

        # Budget records
        for b in result_dict.get('budget_records', []):
            try:
                if not isinstance(b, dict):
                    b = getattr(b, '__dict__', {})
                fy = str(b.get('financial_year', ''))
                m = re.search(r'(\d{4})', fy)
                if m:
                    start_yr = int(m.group(1))
                    m2 = re.search(r'\d{4}[-/](\d{2,4})', fy)
                    if m2:
                        end_val = int(m2.group(1))
                        end_yr = (start_yr // 100) * 100 + end_val if end_val < 100 else end_val
                    else:
                        end_yr = start_yr + 1

                    BudgetRecord.objects.get_or_create(
                        scheme=scheme,
                        financial_year_start=start_yr,
                        financial_year_end=end_yr,
                        defaults={
                            'budget_estimate': b.get('budget_estimate'),
                            'revised_estimate': b.get('revised_estimate'),
                            'actual_expenditure': b.get('actual_expenditure'),
                            'amount_unit': b.get('amount_unit') or 'crore',
                            'currency': b.get('currency') or 'INR',
                            'notes': str(b.get('source_title') or '')[:255],
                            'verification_status': BudgetRecord.STATUS_VERIFIED,
                        }
                    )
            except Exception as e:
                log.debug('Could not persist budget record: %s', e)

    def _extract_scheme_name(self, query: str) -> str:
        """
        Best-effort extraction of the scheme name from a user query.

        Returns the most likely scheme name / abbreviation.
        In Phase 3+, this will use a Gemini call for disambiguation.
        """
        # Simple heuristic: look for all-caps abbreviations or quoted names
        caps = re.findall(r'\b[A-Z][A-Z\-]{2,}\b', query)
        if caps:
            return caps[0]
        # Fall back to first noun phrase
        words = query.split()
        return ' '.join(words[:4]) if words else query

    def _find_or_create_scheme(self, scheme_name: str):
        """Find an existing scheme or create a placeholder."""
        from apps.schemes.models import Scheme
        name = scheme_name.strip()
        if not name:
            return None
        try:
            return Scheme.objects.get(name__iexact=name)
        except Scheme.DoesNotExist:
            pass
        try:
            return Scheme.objects.get(abbreviation__iexact=name)
        except Scheme.DoesNotExist:
            pass
        # Create a minimal placeholder — will be enriched by research result
        scheme, _ = Scheme.objects.get_or_create(
            name=name,
            defaults={'abbreviation': name if len(name) <= 20 else ''},
        )
        return scheme


# Module-level singleton
orchestrator = ResearchOrchestrator()
