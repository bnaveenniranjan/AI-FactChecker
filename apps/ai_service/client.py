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
        self._api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
        self._model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-3.8-flash') or 'gemini-3.8-flash'
        self._client = None

    def is_configured(self) -> bool:
        """Check if a Gemini API key is configured and valid."""
        import os
        key = self._api_key or os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        return bool(key and str(key).strip())

    def set_api_key(self, api_key: str):
        """Update API key at runtime."""
        self._api_key = api_key.strip()
        self._client = None

    def _get_client(self):
        """Lazy-initialise the Gemini SDK client."""
        import os
        key = self._api_key or os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', '')
        if not key or not str(key).strip():
            raise GeminiError(
                'GEMINI_API_KEY is not configured. '
                'Set it in your .env file or via settings.'
            )
        if self._client is None or self._api_key != key:
            self._api_key = key
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError as exc:
                raise GeminiError('google-genai package is not installed.') from exc
        return self._client

    def _call_with_retry(self, prompt: str) -> str:
        """
        Call Gemini with bounded exponential backoff on transient errors.

        Returns the raw text response.
        Raises GeminiRateLimitError if quota is exhausted after retries.
        Raises GeminiError for unrecoverable errors.
        """
        client = self._get_client()
        backoff = INITIAL_BACKOFF_S

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.debug(
                    'Gemini request: model=%s attempt=%d prompt_len=%d',
                    self._model_name,
                    attempt,
                    len(prompt),
                )
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                )
                text = response.text
                log.debug('Gemini response received: len=%d', len(text) if text else 0)
                return text or ''

            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limit = any(kw in exc_str for kw in ('quota', 'rate', '429', 'resource_exhausted'))
                is_transient = any(kw in exc_str for kw in ('500', '503', 'timeout', 'unavailable'))

                if is_rate_limit and attempt == MAX_RETRIES:
                    log.warning('Gemini rate limit exhausted after %d attempts.', MAX_RETRIES)
                    raise GeminiRateLimitError('Gemini API quota exhausted.') from exc

                if (is_rate_limit or is_transient) and attempt < MAX_RETRIES:
                    log.warning(
                        'Gemini transient error (attempt %d/%d): %s. Retrying in %.1fs.',
                        attempt, MAX_RETRIES, exc, backoff,
                    )
                    time.sleep(backoff)
                    backoff *= BACKOFF_MULTIPLIER
                    continue

                log.error('Gemini unrecoverable error: %s', exc, exc_info=True)
                raise GeminiError(f'Gemini API error: {exc}') from exc

        raise GeminiError('Gemini call failed after all retries.')

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
gemini_client = GeminiClient()
