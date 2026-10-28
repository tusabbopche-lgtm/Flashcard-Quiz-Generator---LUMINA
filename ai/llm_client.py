"""Minimal client for OpenAI-compatible chat-completion endpoints.

The app talks to any server that implements ``POST {base_url}/chat/completions``
(Ollama, LM Studio, vLLM, llama.cpp server, OpenAI itself, ...). The client is
deliberately dependency-light: it only uses ``requests`` and returns plain
dicts so it can be unit tested without a network.
"""

import json
import re
from typing import Any, Dict, Optional

import requests

DEFAULT_TIMEOUT = 180
DEFAULT_MODEL = 'gpt-3.5-turbo'


class LLMError(RuntimeError):
    """Raised when the remote model cannot be reached or returns garbage."""


def normalize_base_url(base_url: str) -> str:
    """Return the base URL used to build the chat-completions endpoint."""
    url = (base_url or '').strip().rstrip('/')
    if not url:
        raise LLMError('LLM base URL is not configured')
    if url.endswith('/chat/completions'):
        return url[: -len('/chat/completions')]
    if not url.endswith('/v1'):
        url = url + '/v1'
    return url


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Parse the first JSON object found in ``raw``.

    Models sometimes wrap JSON in markdown fences or add a sentence before it,
    so the raw text is scanned for a balanced object instead of being parsed
    directly.
    """
    if not raw or not raw.strip():
        raise LLMError('Empty response from model')

    text = raw.strip()
    fence = re.match(r'^```(?:json)?\s*(.*?)\s*```$', text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        parsed = None

    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        return {'items': parsed}

    start = text.find('{')
    while start != -1:
        try:
            candidate, _ = json.JSONDecoder().raw_decode(text[start:])
        except ValueError:
            candidate = None
        if isinstance(candidate, dict):
            return candidate
        start = text.find('{', start + 1)

    raise LLMError('Could not parse a JSON object from the model response')


class OpenAICompatibleClient:
    """Thin wrapper around the chat-completions API."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        self.base_url = normalize_base_url(base_url)
        self.api_key = (api_key or '').strip() or None
        self.model = (model or '').strip() or DEFAULT_MODEL
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def endpoint(self) -> str:
        return f'{self.base_url}/chat/completions'

    def _headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def _payload(self, system_prompt: str, user_prompt: str, json_mode: bool) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }
        if json_mode:
            payload['response_format'] = {'type': 'json_object'}
        return payload

    def _post(self, payload: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                self.endpoint,
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LLMError(f'Could not reach the model endpoint: {exc}') from exc

        if response.status_code >= 400:
            raise LLMError(
                f'Model endpoint returned HTTP {response.status_code}: {response.text[:400]}'
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMError('Model endpoint did not return JSON') from exc

        try:
            return body['choices'][0]['message']['content'] or ''
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f'Unexpected response shape from model: {str(body)[:400]}') from exc

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the raw assistant text for the given prompt pair."""
        payload = self._payload(system_prompt, user_prompt, json_mode=False)
        try:
            return self._post(payload)
        except LLMError:
            # Some servers reject unknown/unsupported fields; retry with the
            # smallest possible payload before giving up.
            fallback = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
            }
            return self._post(fallback)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        repair_prompt: str = '',
    ) -> Dict[str, Any]:
        """Return a parsed JSON object, repairing the output once if needed."""
        payload = self._payload(system_prompt, user_prompt, json_mode=True)
        raw = ''
        try:
            raw = self._post(payload)
        except LLMError:
            raw = self.complete(system_prompt, user_prompt)

        try:
            return extract_json_object(raw)
        except LLMError:
            if not raw.strip():
                raise
            repair = repair_prompt or 'Return only the corrected JSON object.'
            repaired_raw = self._post(
                self._payload(repair, raw[:8000], json_mode=False)
            )
            return extract_json_object(repaired_raw)
