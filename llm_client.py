"""Provider-agnostic LLM wrapper. Every LLM call in the pipeline goes through
call_llm_json() so swapping providers is a single env var (LLM_PROVIDER) and all
JSON-forcing/parsing/retry logic lives in exactly one place.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when the provider call itself fails (auth/network/API error)."""


class LLMJSONError(Exception):
    """Raised when the LLM response can't be parsed into valid, schema-conformant JSON."""


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        """Send prompt to the provider, return the raw text response."""


class GroqClient(BaseLLMClient):
    def __init__(self) -> None:
        from groq import Groq  # lazy import: only required if LLM_PROVIDER=groq

        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set")
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    def complete(self, prompt: str) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=settings.llm_temperature,
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # provider SDK exceptions vary; normalize to LLMError
            raise LLMError(f"Groq call failed: {exc}") from exc
        return resp.choices[0].message.content


class GeminiClient(BaseLLMClient):
    def __init__(self) -> None:
        import google.generativeai as genai  # lazy import: only if LLM_PROVIDER=gemini

        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not set")
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)

    def complete(self, prompt: str) -> str:
        try:
            resp = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": settings.llm_temperature,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            raise LLMError(f"Gemini call failed: {exc}") from exc
        return resp.text


class OllamaClient(BaseLLMClient):
    def __init__(self) -> None:
        import requests  # lazy import

        self._requests = requests
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model

    def complete(self, prompt: str) -> str:
        try:
            resp = self._requests.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": settings.llm_temperature},
                },
                timeout=120,
            )
            resp.raise_for_status()
        except Exception as exc:
            raise LLMError(f"Ollama call failed: {exc}") from exc
        return resp.json()["response"]


_PROVIDERS = {
    "groq": GroqClient,
    "gemini": GeminiClient,
    "ollama": OllamaClient,
}

_client_instance: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """Returns a process-wide cached client for the configured LLM_PROVIDER."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    provider = settings.llm_provider
    if provider not in _PROVIDERS:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Must be one of {list(_PROVIDERS)}.")
    _client_instance = _PROVIDERS[provider]()
    return _client_instance


def reset_llm_client() -> None:
    """Clears the cached client. Used by tests when swapping providers at runtime."""
    global _client_instance
    _client_instance = None


_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip()).strip()


def _build_json_prompt(prompt: str, schema: Type[BaseModel]) -> str:
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    return (
        f"{prompt}\n\n"
        "Respond with ONLY valid JSON matching this JSON Schema. No markdown "
        "code fences, no commentary, no explanation — JSON only:\n"
        f"{schema_json}"
    )


@retry(
    stop=stop_after_attempt(settings.llm_max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((LLMError, LLMJSONError)),
    reraise=True,
)
def call_llm_json(prompt: str, schema: Type[T]) -> dict:
    """Every LLM call in the pipeline goes through this function.

    Sends `prompt` (augmented with the target JSON Schema) to the configured
    provider, parses the response as JSON, validates it against `schema`, and
    returns the validated data as a plain dict. Retries on provider errors or
    malformed/non-conformant JSON, up to LLM_MAX_RETRIES attempts.
    """
    client = get_llm_client()
    full_prompt = _build_json_prompt(prompt, schema)
    raw = client.complete(full_prompt)
    cleaned = _strip_markdown_fence(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMJSONError(f"LLM response was not valid JSON: {exc}\nRaw: {raw[:500]}") from exc

    try:
        validated = schema.model_validate(data)
    except ValidationError as exc:
        raise LLMJSONError(f"LLM JSON did not match schema {schema.__name__}: {exc}") from exc

    return validated.model_dump()
