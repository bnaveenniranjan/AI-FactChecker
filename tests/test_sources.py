"""Tests for the sources app and retrieval utilities."""

import pytest
from unittest.mock import patch, MagicMock

from apps.sources.models import Source, EvidenceExcerpt
from apps.schemes.models import Scheme


@pytest.fixture
def scheme(db):
    return Scheme.objects.create(name='MGNREGA Test')


@pytest.mark.django_db
class TestSourceModel:
    """Test Source model creation and deduplication."""

    def test_source_created_with_url(self):
        source = Source.objects.create(url='https://pib.gov.in/test-release')
        assert source.pk is not None

    def test_content_hash_auto_generated(self):
        source = Source.objects.create(url='https://pib.gov.in/some-url')
        assert len(source.content_hash) == 64  # SHA-256 hex

    def test_duplicate_url_raises(self):
        Source.objects.create(url='https://pib.gov.in/release-1')
        with pytest.raises(Exception):
            Source.objects.create(url='https://pib.gov.in/release-1')

    def test_str_uses_title_when_available(self):
        source = Source.objects.create(
            url='https://pib.gov.in/release-2',
            title='PM-KISAN Launch Press Release',
        )
        assert 'PM-KISAN Launch Press Release' in str(source)

    def test_str_falls_back_to_url(self):
        source = Source.objects.create(url='https://pib.gov.in/release-3')
        assert 'pib.gov.in' in str(source)

    def test_scheme_linked_via_m2m(self, scheme):
        source = Source.objects.create(url='https://india.gov.in/scheme-info')
        source.schemes.add(scheme)
        assert scheme in source.schemes.all()

    def test_evidence_excerpt_linked_to_source(self, scheme):
        source = Source.objects.create(url='https://pib.gov.in/release-4')
        excerpt = EvidenceExcerpt.objects.create(
            source=source,
            text='The scheme was launched with an initial budget of ₹75,000 crore.',
            scheme=scheme,
        )
        assert excerpt.source == source
        assert 'pib.gov.in' in str(excerpt)

    def test_excerpt_preview_in_str(self):
        source = Source.objects.create(url='https://pib.gov.in/release-5')
        excerpt = EvidenceExcerpt.objects.create(
            source=source,
            text='Short text.',
        )
        assert 'Short text.' in str(excerpt)


class TestSourceRetrieval:
    """Test source retrieval utilities with mocked HTTP."""

    def test_allowlisted_url_fetched(self):
        from apps.sources.retrieval import _is_allowed_url
        assert _is_allowed_url('https://pib.gov.in/release') is True

    def test_non_allowlisted_url_blocked(self):
        from apps.sources.retrieval import _is_allowed_url
        assert _is_allowed_url('https://unknown-site.com/page') is False

    def test_www_prefix_handled(self):
        from apps.sources.retrieval import _is_allowed_url
        assert _is_allowed_url('https://www.thehindu.com/article') is True

    @patch('apps.sources.retrieval.requests.get')
    def test_fetch_returns_sanitised_content(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><head><title>PM-KISAN News</title></head><body><p>Scheme launched in 2019.</p></body></html>'
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        from apps.sources.retrieval import WebConnector
        connector = WebConnector()
        result = connector.fetch('https://pib.gov.in/some-release')

        assert result is not None
        assert 'Scheme launched in 2019' in result['text']
        assert result['title'] == 'PM-KISAN News'

    @patch('apps.sources.retrieval.requests.get')
    def test_fetch_returns_none_on_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout()

        from apps.sources.retrieval import WebConnector
        connector = WebConnector()
        result = connector.fetch('https://pib.gov.in/timeout-url')
        assert result is None

    def test_fetch_blocked_for_disallowed_url(self):
        from apps.sources.retrieval import WebConnector
        connector = WebConnector()
        result = connector.fetch('https://malicious-site.com/steal-data')
        assert result is None
