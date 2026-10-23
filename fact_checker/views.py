"""Frontend views for the AI Government Scheme Fact Checker."""

from django.shortcuts import render
from apps.schemes.models import Scheme
from apps.factcheck.models import Claim
from apps.ai_service.client import gemini_client


def home_view(request):
    """Main dashboard view serving the single-page application experience."""
    schemes = Scheme.objects.all().prefetch_related(
        'timeline_events',
        'budget_records',
        'scheme_responsibilities__ministerial_tenure__leader',
        'scheme_responsibilities__ministry',
    ).order_by('name')

    claims = Claim.objects.all().prefetch_related(
        'evidence_links__source'
    ).order_by('-verified_at')

    return render(request, 'index.html', {
        'schemes': schemes,
        'claims': claims,
        'gemini_configured': gemini_client.is_configured(),
        'gemini_model': gemini_client._model_name,
    })
