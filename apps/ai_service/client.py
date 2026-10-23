"""
Gemini API client abstraction.

This module is the ONLY place in the codebase that talks to Google's Gemini API.
All other modules call GeminiClient, never the SDK directly.

Responsibilities:
- Construct and submit requests.
- Parse and validate structured JSON responses via Pydantic.
- Handle timeouts, rate limits, and transient failures with bounded backoff.
- Log request metadata WITHOUT exposing the API key or raw user data.
- Support model configuration via environment variables.
- Raise typed exceptions so callers can handle failures gracefully.
"""

from __future__ import annotations

import json
import logging
import time
import requests
from typing import Type, TypeVar

from django.conf import settings
from pydantic import BaseModel, ValidationError

from .prompts import build_scheme_research_prompt, build_fact_check_prompt
from .schemas import ResearchResultSchema, FactCheckVerdictSchema

log = logging.getLogger('apps.ai_service')

T = TypeVar('T', bound=BaseModel)

# Backoff configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_S = 2.0
BACKOFF_MULTIPLIER = 2.0


class GeminiError(Exception):
    """Base exception for Gemini API errors."""


class GeminiRateLimitError(GeminiError):
    """Raised when the API quota is exhausted."""


class GeminiValidationError(GeminiError):
    """Raised when the AI response does not match the expected schema."""

    def __init__(self, message: str, raw_response: str = ''):
        super().__init__(message)
        self.raw_response = raw_response


class GeminiClient:
    """
    Provider-agnostic AI client with Gemini as the current backend.

    To switch AI providers in the future, replace this class's internals
    while keeping the same public interface.
    """

    def __init__(self):
        # OpenRouter credentials and model
        self._api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or ''
        self._model_name = getattr(settings, 'OPENROUTER_MODEL', 'google/gemma-4-31b-it:free') or 'google/gemma-4-31b-it:free'
        self._client = None  # kept for backward compatibility; not used

    def is_configured(self) -> bool:
        """Check if an OpenRouter API key is configured and valid."""
        import os
        key = self._api_key or os.environ.get('OPENROUTER_API_KEY') or getattr(settings, 'OPENROUTER_API_KEY', '')
        return bool(key and str(key).strip())

    def set_api_key(self, api_key: str):
        """Update API key at runtime."""
        self._api_key = api_key.strip()
        self._client = None

    def _get_client(self):
        """Placeholder for compatibility – OpenRouter does not need a client object."""
        return None

    def _call_with_retry(self, prompt: str) -> str:
        """Call OpenRouter with exponential backoff on transient errors.

        Returns the raw text response.
        Raises GeminiError (used for compatibility) for unrecoverable errors.
        """
        backoff = INITIAL_BACKOFF_S
        openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', '') or ''
        openrouter_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        if not openrouter_key:
            raise GeminiError('OPENROUTER_API_KEY is not configured.')
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.debug(
                    'OpenRouter request: model=%s attempt=%d prompt_len=%d',
                    self._model_name,
                    attempt,
                    len(prompt),
                )
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self._model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "reasoning": {"enabled": True},
                }
                resp = requests.post(openrouter_endpoint, headers=headers, data=json.dumps(payload), timeout=30)
                resp.raise_for_status()
                data = resp.json()
                text = data['choices'][0]['message']['content']
                log.debug('OpenRouter response received: len=%d', len(text) if text else 0)
                return text or ''
            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = any(kw in exc_str for kw in ('quota', 'rate', '429', 'resource_exhausted'))
                is_transient = any(kw in exc_str for kw in ('500', '503', 'timeout', 'unavailable'))
                if (is_rate_limit or is_transient) and attempt < MAX_RETRIES:
                    log.warning(
                        'OpenRouter transient error (attempt %d/%d): %s. Retrying in %.1fs.',
                        attempt, MAX_RETRIES, exc, backoff,
                    )
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                    continue
                log.error('OpenRouter unrecoverable error: %s', exc, exc_info=True)
                raise GeminiError(f'OpenRouter API error: {exc}') from exc
        raise GeminiError('OpenRouter call failed after all retries.')

    def _parse_json_response(self, raw: str, schema: Type[T]) -> T:
        """
        Parse and validate a JSON response against a Pydantic schema.

        Strips markdown code fences if present (Gemini sometimes adds them
        even when instructed not to).
        """
        # Strip markdown code fences
        text = raw.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove first and last fence lines
            text = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            log.error('Gemini returned non-JSON response: %s', text[:200])
            raise GeminiValidationError(
                f'Gemini response was not valid JSON: {exc}',
                raw_response=raw,
            ) from exc

        try:
            return schema.model_validate(data)
        except ValidationError as exc:
            log.error('Gemini response failed schema validation: %s', exc)
            raise GeminiValidationError(
                f'Gemini response did not match expected schema: {exc}',
                raw_response=raw,
            ) from exc

    def research_scheme(
        self,
        query: str,
        retrieved_passages: list[dict],
        allow_fallback: bool = False,
    ) -> ResearchResultSchema:
        """
        Run a scheme research query using retrieved evidence as context.
        Uses live Gemini API when configured; otherwise falls back to local evidence synthesis.
        """
        if not self.is_configured():
            from .fallback import fallback_research_scheme
            log.info('GEMINI_API_KEY not set. Using local fallback synthesis for: %s', query[:50])
            return fallback_research_scheme(query, retrieved_passages)

        try:
            prompt = build_scheme_research_prompt(query, retrieved_passages)
            raw = self._call_with_retry(prompt)
            result = self._parse_json_response(raw, ResearchResultSchema)
            result.ai_model_used = self._model_name
            return result
        except Exception as exc:
            if allow_fallback:
                log.warning('Gemini call failed (%s). Falling back to local evidence synthesis.', exc)
                from .fallback import fallback_research_scheme
                result = fallback_research_scheme(query, retrieved_passages)
                result.ai_model_used = f'{self._model_name} (fallback: {str(exc)[:40]})'
                return result
            raise

    def fact_check_claim(
        self,
        claim: str,
        retrieved_passages: list[dict],
        allow_fallback: bool = False,
    ) -> FactCheckVerdictSchema:
        """
        Verify a single factual claim against retrieved evidence.
        Uses live Gemini API when configured; otherwise falls back to local evidence synthesis.
        """
        if not self.is_configured():
            from .fallback import fallback_fact_check_claim
            log.info('GEMINI_API_KEY not set. Using local fallback fact check for claim: %s', claim[:50])
            return fallback_fact_check_claim(claim, retrieved_passages)

        try:
            prompt = build_fact_check_prompt(claim, retrieved_passages)
            raw = self._call_with_retry(prompt)
            return self._parse_json_response(raw, FactCheckVerdictSchema)
        except Exception as exc:
            if allow_fallback:
                log.warning('Gemini fact-check failed (%s). Falling back to local evidence synthesis.', exc)
                from .fallback import fallback_fact_check_claim
                return fallback_fact_check_claim(claim, retrieved_passages)
            raise


# Module-level singleton — use this instead of constructing GeminiClient directly
gemini_client = GeminiClient()  # Alias kept for backward compatibility
