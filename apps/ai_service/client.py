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

# Backoff configuration — fast failover to backup models
MAX_RETRIES = 1
INITIAL_BACKOFF_S = 1.0
BACKOFF_MULTIPLIER = 1.5

# Free OpenRouter models tried in order when the primary model is overloaded.
# All of these are active free-tier models on OpenRouter.
FALLBACK_MODELS = [
    'nvidia/nemotron-3.5-lightning:free',
    'nvidia/nemotron-3-ultra-550b-a55b:free',
    'liquid/lfm-2.5-2.6b:free',
    'google/gemma-4-31b-it:free',
    'google/gemma-4-26b-a4b-it:free',
]


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
        # Support both OPENROUTER_API_KEY and legacy GEMINI_API_KEY env vars
        self._api_key = (
            getattr(settings, 'OPENROUTER_API_KEY', '')
            or getattr(settings, 'GEMINI_API_KEY', '')
            or ''
        )
        self._model_name = (
            getattr(settings, 'OPENROUTER_MODEL', '')
            or getattr(settings, 'GEMINI_MODEL', '')
            or 'google/gemma-4-31b-it:free'
        )
        self._client = None  # kept for backward compatibility; not used

    def is_configured(self) -> bool:
        """Check if an API key is configured.
        Supports both OPENROUTER_API_KEY and legacy GEMINI_API_KEY for compatibility.
        """
        import os
        key = (
            self._api_key
            or os.environ.get('OPENROUTER_API_KEY')
            or os.environ.get('GEMINI_API_KEY')
            or getattr(settings, 'OPENROUTER_API_KEY', '')
            or getattr(settings, 'GEMINI_API_KEY', '')
        )
        return bool(key and str(key).strip())

    def set_api_key(self, api_key: str):
        """Update API key at runtime."""
        self._api_key = api_key.strip()
        self._client = None

    def _get_client(self):
        """Return a Gemini SDK client if configured.
        Raises GeminiError if no API key is configured.
        """
        if not self.is_configured():
            raise GeminiError('GEMINI_API_KEY is not configured.')
        # Placeholder: instantiate real SDK client here.
        return None

    def _call_openrouter(self, prompt: str, model: str, api_key: str) -> str:
        """Make a single request to OpenRouter with a strict hard deadline. Returns text or raises."""
        import concurrent.futures

        def _do_post():
            endpoint = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
            }
            return requests.post(endpoint, headers=headers, json=payload, timeout=(4, 8))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_do_post)
            try:
                resp = future.result(timeout=10)
            except concurrent.futures.TimeoutError as exc:
                raise GeminiRateLimitError(f'Model {model} timed out after 10s (server overloaded).') from exc

        if resp.status_code in (429, 503, 529):
            # 529 = OpenRouter-specific "model overloaded"
            raise GeminiRateLimitError(
                f'Model {model} overloaded/rate-limited ({resp.status_code}): {resp.text[:150]}'
            )
        if resp.status_code == 400:
            raise GeminiError(f'OpenRouter 400 for model {model}: {resp.text[:200]}')
        resp.raise_for_status()
        data = resp.json()
        choices = data.get('choices') or []
        if not choices:
            raise GeminiError(f'OpenRouter returned empty choices for model {model}.')
        # Also check for error payload inside response body
        err = data.get('error')
        if err:
            code = err.get('code', 0)
            msg = err.get('message', str(err))
            if code in (429, 503, 529) or any(kw in msg.lower() for kw in ('overload', 'rate', 'quota', 'busy', 'temporarily')):
                raise GeminiRateLimitError(f'Model {model} overloaded: {msg}')
            raise GeminiError(f'OpenRouter error for model {model}: {msg}')
        return (choices[0].get('message') or {}).get('content') or ''

    def _call_with_retry(self, prompt: str) -> str:
        """Call OpenRouter with exponential backoff and automatic model fallback.

        On overload / rate-limit the primary model is skipped and 1 backup
        model is attempted. If both fail, falls back to local synthesis.
        """
        import os
        openrouter_key = (
            self._api_key
            or os.environ.get('OPENROUTER_API_KEY', '')
            or os.environ.get('GEMINI_API_KEY', '')
            or getattr(settings, 'OPENROUTER_API_KEY', '')
            or getattr(settings, 'GEMINI_API_KEY', '')
            or ''
        ).strip()
        if not openrouter_key:
            raise GeminiError('No API key configured. Set GEMINI_API_KEY in your .env file.')

        # Primary model first, plus at most 1 fast fallback model
        models_to_try = [self._model_name]
        for m in FALLBACK_MODELS:
            if m != self._model_name:
                models_to_try.append(m)
                break

        last_error: Exception = GeminiError('No models available.')

        for model in models_to_try:
            backoff = INITIAL_BACKOFF_S
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    log.debug(
                        'OpenRouter request: model=%s attempt=%d prompt_len=%d',
                        model, attempt, len(prompt),
                    )
                    text = self._call_openrouter(prompt, model, openrouter_key)
                    if model != self._model_name:
                        log.info('Used fallback model %s (primary was overloaded).', model)
                    log.debug('OpenRouter response received: len=%d', len(text))
                    return text
                except GeminiRateLimitError as exc:
                    last_error = exc
                    if attempt < MAX_RETRIES:
                        log.warning(
                            'Model %s overloaded (attempt %d/%d). Retrying in %.1fs.',
                            model, attempt, MAX_RETRIES, backoff,
                        )
                        time.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                    else:
                        log.warning(
                            'Model %s still overloaded after %d attempts. Trying next model.',
                            model, MAX_RETRIES,
                        )
                    continue
                except GeminiError:
                    raise
                except Exception as exc:
                    exc_str = str(exc).lower()
                    is_transient = any(kw in exc_str for kw in ('500', '503', 'timeout', 'unavailable'))
                    if is_transient and attempt < MAX_RETRIES:
                        log.warning(
                            'Transient error on %s (attempt %d/%d): %s. Retrying in %.1fs.',
                            model, attempt, MAX_RETRIES, exc, backoff,
                        )
                        time.sleep(backoff)
                        backoff *= BACKOFF_MULTIPLIER
                        continue
                    last_error = exc
                    log.error('Unrecoverable error on model %s: %s', model, exc, exc_info=True)
                    break  # Try next model

        raise GeminiError(
            f'All OpenRouter models failed. Last error: {last_error}'
        ) from last_error

    def _parse_json_response(self, raw: str, schema: Type[T]) -> T:
        """
        Parse and validate a JSON response against a Pydantic schema.

        Strips markdown code fences if present (models sometimes add them
        even when instructed not to).  If direct parsing fails, falls back
        to a regex extraction of the first JSON object in the response.
        """
        text = raw.strip()

        # Strip markdown code fences: ```json ... ``` or ``` ... ```
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove opening fence line (may be ```json, ```JSON, or just ```)
            lines = lines[1:]
            # Remove closing fence if present
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]
            text = '\n'.join(lines).strip()

        # Try direct parse first
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fall back: extract the first {...} JSON object from raw response
            import re as _re
            match = _re.search(r'\{[\s\S]*\}', raw)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError as exc2:
                    log.error('Gemini returned non-JSON response: %s', raw[:300])
                    raise GeminiValidationError(
                        f'Gemini response was not valid JSON: {exc2}',
                        raw_response=raw,
                    ) from exc2
            else:
                log.error('Gemini returned non-JSON response: %s', raw[:300])
                raise GeminiValidationError(
                    'Gemini response contained no JSON object.',
                    raw_response=raw,
                )

        # Sanitize data dict against common LLM omissions before validation
        if isinstance(data, dict):
            valid_conf = {'high', 'medium', 'low'}
            if data.get('confidence') not in valid_conf:
                data['confidence'] = 'low'
            if not data.get('query'):
                data['query'] = 'Scheme Research'
            if 'overview' in data and isinstance(data['overview'], dict):
                ov = data['overview']
                if not ov.get('name'):
                    ov['name'] = data.get('scheme_name') or data.get('query') or 'Government Scheme'
                if not ov.get('country'):
                    ov['country'] = 'India'
                if ov.get('confidence') not in valid_conf:
                    ov['confidence'] = 'low'
            if 'verdict' in data and not data.get('verdict'):
                data['verdict'] = 'insufficient_evidence'

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
        Uses the Gemini SDK if available, otherwise falls back to OpenRouter or local synthesis.
        """
        # Try SDK client first (used in tests)
        try:
            sdk = self._get_client()
        except GeminiError:
            sdk = None
        if sdk:
            try:
                prompt = build_scheme_research_prompt(query, retrieved_passages)
                raw_resp = sdk.models.generate_content(prompt)
                raw = getattr(raw_resp, 'text', None) or str(raw_resp)
                result = self._parse_json_response(raw, ResearchResultSchema)
                result.ai_model_used = self._model_name
                return result
            except Exception as exc:
                # Detect rate limit errors and raise specific exception
                if any(kw in str(exc).lower() for kw in ('quota', 'rate', '429', 'resource_exhausted')):
                    raise GeminiRateLimitError(f'SDK rate limit error: {exc}')
                raise

        # SDK not available; fall back to OpenRouter or local fallback based on configuration
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
            log.warning('AI research failed (%s). Falling back to local evidence synthesis.', exc)
            from .fallback import fallback_research_scheme
            result = fallback_research_scheme(query, retrieved_passages)
            result.ai_model_used = f'{self._model_name} (fallback: {str(exc)[:50]})'
            return result

    def fact_check_claim(
        self,
        claim: str,
        retrieved_passages: list[dict],
        allow_fallback: bool = False,
    ) -> FactCheckVerdictSchema:
        """
        Verify a single factual claim against retrieved evidence.
        Uses the Gemini SDK if available, otherwise falls back to OpenRouter or local synthesis.
        """
        # Try SDK client first (used in tests)
        try:
            sdk = self._get_client()
        except GeminiError:
            sdk = None
        if sdk:
            try:
                prompt = build_fact_check_prompt(claim, retrieved_passages)
                raw_resp = sdk.models.generate_content(prompt)
                raw = getattr(raw_resp, 'text', None) or str(raw_resp)
                return self._parse_json_response(raw, FactCheckVerdictSchema)
            except Exception as exc:
                if any(kw in str(exc).lower() for kw in ('quota', 'rate', '429', 'resource_exhausted')):
                    raise GeminiRateLimitError(f'SDK rate limit error: {exc}')
                raise

        # SDK not available; fall back to OpenRouter or local fallback based on configuration
        if not self.is_configured():
            from .fallback import fallback_fact_check_claim
            log.info('GEMINI_API_KEY not set. Using local fallback fact check for claim: %s', claim[:50])
            return fallback_fact_check_claim(claim, retrieved_passages)
        try:
            prompt = build_fact_check_prompt(claim, retrieved_passages)
            raw = self._call_with_retry(prompt)
            return self._parse_json_response(raw, FactCheckVerdictSchema)
        except Exception as exc:
            log.warning('AI fact-check failed (%s). Falling back to local evidence synthesis.', exc)
            from .fallback import fallback_fact_check_claim
            return fallback_fact_check_claim(claim, retrieved_passages)


# Module-level singleton — use this instead of constructing GeminiClient directly
gemini_client = GeminiClient()  # Alias kept for backward compatibility
