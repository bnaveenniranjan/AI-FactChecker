"""Tests for the Gemini AI client — all calls are mocked."""

import pytest
import json
from unittest.mock import patch, MagicMock

from apps.ai_service.client import GeminiClient, GeminiError, GeminiValidationError, GeminiRateLimitError
from apps.ai_service.schemas import ResearchResultSchema, FactCheckVerdictSchema


VALID_RESEARCH_RESPONSE = {
    "query": "PM-KISAN history",
    "scheme_name": "PM-KISAN",
    "overview": {
        "name": "Pradhan Mantri Kisan Samman Nidhi",
        "abbreviation": "PM-KISAN",
        "category": "agriculture",
        "jurisdiction": "central",
        "country": "India",
        "launch_date": "2019-02-24",
        "original_objectives": "Income support to small and marginal farmers",
        "confidence": "medium",
        "data_gaps": [],
        "source_urls": ["https://pmkisan.gov.in"]
    },
    "timeline_events": [],
    "amendments": [],
    "budget_records": [],
    "leadership_records": [],
    "source_urls_searched": ["https://pmkisan.gov.in"],
    "confidence": "medium",
    "data_gaps": [],
    "ai_model_used": None,
}

VALID_FACTCHECK_RESPONSE = {
    "original_claim": "PM-KISAN provides ₹6000 per year to farmers",
    "verdict": "supported",
    "explanation": "The claim is directly supported by the scheme's official documentation.",
    "supporting_evidence": [
        {
            "text": "Farmers receive ₹6000 per year in 3 instalments.",
            "source_url": "https://pmkisan.gov.in",
            "stance": "supports"
        }
    ],
    "contradicting_evidence": [],
    "confidence": "high",
    "confidence_explanation": "Official portal confirms the amount.",
    "data_gaps": []
}


class TestGeminiClient:
    """Test GeminiClient with mocked SDK."""

    def _make_client(self):
        client = GeminiClient()
        client._api_key = 'fake-key'
        client._model_name = 'gemini-3.8-flash'
        return client

    def _mock_genai_response(self, text: str):
        mock_resp = MagicMock()
        mock_resp.text = text
        return mock_resp

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_research_scheme_parses_valid_response(self, mock_get_client):
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.return_value = self._mock_genai_response(
            json.dumps(VALID_RESEARCH_RESPONSE)
        )
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        result = client.research_scheme("PM-KISAN history", [])

        assert isinstance(result, ResearchResultSchema)
        assert result.scheme_name == 'PM-KISAN'
        assert result.ai_model_used == 'gemini-3.8-flash'

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_fact_check_parses_valid_response(self, mock_get_client):
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.return_value = self._mock_genai_response(
            json.dumps(VALID_FACTCHECK_RESPONSE)
        )
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        result = client.fact_check_claim("PM-KISAN provides ₹6000 per year", [])

        assert isinstance(result, FactCheckVerdictSchema)
        assert result.verdict.value == 'supported'
        assert result.confidence.value == 'high'

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_invalid_json_raises_validation_error(self, mock_get_client):
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.return_value = self._mock_genai_response(
            "This is not JSON at all."
        )
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        with pytest.raises(GeminiValidationError):
            client.research_scheme("some query", [])

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_schema_mismatch_raises_validation_error(self, mock_get_client):
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.return_value = self._mock_genai_response(
            json.dumps({"unexpected": "structure"})
        )
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        # Schema mismatch: 'query' field is required by ResearchResultSchema
        with pytest.raises(GeminiValidationError):
            client.research_scheme("some query", [])

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_rate_limit_error_after_max_retries(self, mock_get_client):
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.side_effect = Exception('429 resource_exhausted quota exceeded')
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        with patch('apps.ai_service.client.time.sleep'):  # don't actually sleep in tests
            with pytest.raises(GeminiRateLimitError):
                client.research_scheme("some query", [])

    @patch('apps.ai_service.client.GeminiClient._get_client')
    def test_markdown_fences_stripped(self, mock_get_client):
        """Gemini sometimes wraps JSON in ```json ... ``` — client must strip this."""
        fenced = f'```json\n{json.dumps(VALID_RESEARCH_RESPONSE)}\n```'
        mock_sdk = MagicMock()
        mock_sdk.models.generate_content.return_value = self._mock_genai_response(fenced)
        mock_get_client.return_value = mock_sdk

        client = self._make_client()
        result = client.research_scheme("PM-KISAN history", [])
        assert result.scheme_name == 'PM-KISAN'

    def test_missing_api_key_raises_gemini_error(self, monkeypatch):
        from django.conf import settings
        monkeypatch.setattr(settings, 'GEMINI_API_KEY', '')
        monkeypatch.delenv('GEMINI_API_KEY', raising=False)
        client = GeminiClient()
        client._api_key = ''
        with pytest.raises(GeminiError, match='GEMINI_API_KEY'):
            client._get_client()
