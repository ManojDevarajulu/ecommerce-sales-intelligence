"""OpenRouter API client wrapper with fallback resilience."""
import json
import re

import httpx
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.ai_reports import ReportMeta, ReportNarrative


class OpenRouterSettings(BaseSettings):
    """Configuration settings for OpenRouter API integration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Kept identical to `.env.example`'s documented value, so a run without
    # `OPENROUTER_MODEL` set behaves the same as the documented setup rather
    # than silently using some other model.
    openrouter_model: str = "nvidia/nemotron-3-super-120b-a12b:free"


settings = OpenRouterSettings()

_NARRATIVE_JSON_INSTRUCTIONS = """Respond with ONLY a JSON object (no markdown fences, no commentary before or \
after) with exactly these keys:
{
  "summary": "1-2 sentence executive summary",
  "key_insights": ["3-5 short bullet-point observations"],
  "recommendations": ["2-4 short actionable recommendations"]
}
Base every claim strictly on the numbers given below - do not invent or estimate any number not provided."""


def _extract_json_object(text: str) -> dict:
    """Free models routinely wrap JSON in markdown fences or add a stray
    sentence before/after despite instructions - take the first {...} block
    rather than requiring the whole response to be pure JSON."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in model response")
    return json.loads(match.group(0))


def chat_completion(prompt: str, temperature: float = 0.3) -> str | None:
    """The one place the OpenRouter chat API is called — shared by the
    business reports and the RAG assistant, so there is one key, one model
    id and one failure contract across the whole application.

    Returns the raw text content of the model's reply, or None on any
    failure (no key configured, network error, non-2xx, unexpected shape).
    Never raises - every failure mode here is a "fall back" signal, not a
    "propagate to the caller" one; each caller decides what its fallback is.

    `temperature` defaults to 0.3 for report narratives (low but not 0 - a
    narrative, not a deterministic calculation); RAG passes 0.1 because a
    grounded answer should vary as little as possible for the same context.
    """
    if not settings.openrouter_api_key:
        return None
    try:
        response = httpx.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": settings.openrouter_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError):
        return None


def generate_narrative(prompt: str, fallback: ReportNarrative) -> tuple[ReportNarrative, ReportMeta]:
    """The one entry point every report calls. `prompt` should already
    contain the deterministic numbers to narrate (the caller's job, not
    this module's - this module knows nothing about orders/ratings/RFM).
    `fallback` is the deterministic ReportNarrative to use if the LLM path
    fails for any reason.
    """
    raw = chat_completion(f"{prompt}\n\n{_NARRATIVE_JSON_INSTRUCTIONS}")
    if raw is None:
        return fallback, ReportMeta(generated_by="deterministic_fallback", model=None)

    try:
        parsed = _extract_json_object(raw)
        narrative = ReportNarrative.model_validate(parsed)
    except (ValueError, json.JSONDecodeError, ValidationError):
        return fallback, ReportMeta(generated_by="deterministic_fallback", model=None)

    return narrative, ReportMeta(generated_by="openrouter", model=settings.openrouter_model)
