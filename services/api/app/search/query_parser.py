"""OpenRouter LLM-powered natural-language query parser for KnocDoc."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.search.normalizer import normalize_preferences
from app.search.schemas import SearchPreferences

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are KnocDoc's natural-language search query parser.
KnocDoc is a doctor discovery directory, NOT a diagnostic or treatment service.
Extract only intent explicitly stated or safely implied by the query. Never invent provider facts, diagnoses, or claim a doctor exists.
Return ONLY one valid JSON object with these keys:
{
  "specialty": string or null,
  "languages": array of strings,
  "language_mode": "any" or "all",
  "location": string or null,
  "radius_km": number or null,
  "budget_max": number or null,
  "budget_exact": number or null,
  "min_experience_years": number or null,
  "availability": "open_now" | "open_today" | "open_24_7" | "open_24_7_preferred" | "unspecified" | "tomorrow_HH:MM",
  "verification_required": boolean,
  "hard_constraints": array of strings,
  "preferences": array of "distance" | "cost" | "language" | "experience" | "rating" | "verification" | "availability",
  "ranking_profile": "balanced" | "nearest" | "budget_focused" | "experience_focused",
  "needs_clarification": boolean,
  "clarification_reason": string or null,
  "unanswerable": boolean,
  "unanswerable_reason": string or null
}

Rules:
- Normalize specialties when clear: cardiology, dermatology, pediatrics, general_physician, dental, orthopedic, gastroenterology, ent, emergency_care.
- "Hindi or Konkani" -> languages: ["Hindi", "Konkani"], language_mode: "any". Only use "all" if the user explicitly requires speaking both/all languages.
- "nearby" without a distance -> preferences includes "distance", ranking_profile: "nearest", radius_km: null.
- "affordable" without a price -> preferences includes "cost", ranking_profile: "budget_focused", budget_max: null.
- "under ₹1,000" / "below 1000" / "no more than 1000" -> budget_max: 1000, hard_constraints includes "budget_max:1000".
- "exactly ₹500" -> budget_exact: 500, budget_max: 500, hard_constraints includes "budget_exact:500".
- Convert miles to km (1 mile = 1.60934 km, rounded to 2 decimals) and metres to km.
- "must", "only", "mandatory", "never" indicate hard constraints. "prefer", "ideally", "I care more about" indicate soft preferences.
- If the user requires verified providers ("verified", "never include unverified"), set verification_required: true and include "verification:verified" in hard_constraints.
- Set needs_clarification: true if the user asks for exact current-location matching without supplying coordinates/city or critical details are missing.
- Set unanswerable: true for impossible/nonexistent specialties or languages, requests for medical diagnosis/guarantees, or impossible constraints.
- Return ONLY raw JSON with no markdown fences or commentary.
""".strip()


class QueryParserError(Exception):
    """Controlled error raised when LLM query parsing fails or is unavailable."""

    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from raw model output."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found in model output.")
    parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model output JSON must be an object.")
    return parsed


def _build_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        timeout=settings.openrouter_timeout_seconds,
        default_headers={
            "HTTP-Referer": "https://knocdoc.local",
            "X-Title": "KnocDoc Search",
        },
    )


async def parse_search_query(
    query: str,
    *,
    client: AsyncOpenAI | None = None,
    settings: Settings | None = None,
) -> SearchPreferences:
    """Parse a natural-language doctor search query via OpenRouter and validate with Pydantic."""
    cfg = settings or get_settings()
    cleaned_query = query.strip()
    if not cleaned_query:
        raise QueryParserError(
            "invalid_query", "Search query cannot be empty.", status_code=422
        )

    if not cfg.llm_search_enabled:
        raise QueryParserError(
            "llm_disabled",
            "Natural-language search is currently disabled.",
            status_code=503,
        )

    if client is None and not cfg.openrouter_api_key:
        raise QueryParserError(
            "missing_api_key",
            "OpenRouter API key is not configured on the server.",
            status_code=503,
        )

    active_client = client or _build_client(cfg)
    max_attempts = max(1, cfg.openrouter_max_retries + 1)
    last_error: Exception | None = None
    started = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        try:
            response = await active_client.chat.completions.create(
                model=cfg.openrouter_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": cleaned_query},
                ],
                temperature=0,
                max_tokens=700,
            )
            content = (response.choices[0].message.content or "").strip()
            raw_dict = extract_json_object(content)
            validated = SearchPreferences.model_validate(raw_dict)
            normalized = normalize_preferences(validated, raw_query=cleaned_query)

            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info(
                "query_parsed model=%s attempt=%d latency_ms=%.1f profile=%s",
                cfg.openrouter_model,
                attempt,
                latency_ms,
                normalized.ranking_profile,
            )
            return normalized

        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            logger.warning(
                "query_parse_invalid_output model=%s attempt=%d error=%s",
                cfg.openrouter_model,
                attempt,
                type(exc).__name__,
            )
            raise QueryParserError(
                "invalid_llm_output",
                "Could not interpret search query into valid structured parameters.",
                status_code=502,
            ) from exc

        except APITimeoutError as exc:
            last_error = exc
            logger.warning(
                "openrouter_timeout model=%s attempt=%d/%d",
                cfg.openrouter_model,
                attempt,
                max_attempts,
            )
        except RateLimitError as exc:
            last_error = exc
            logger.warning(
                "openrouter_rate_limited model=%s attempt=%d/%d",
                cfg.openrouter_model,
                attempt,
                max_attempts,
            )
        except APIConnectionError as exc:
            last_error = exc
            logger.warning(
                "openrouter_connection_error model=%s attempt=%d/%d",
                cfg.openrouter_model,
                attempt,
                max_attempts,
            )
        except APIStatusError as exc:
            last_error = exc
            status = getattr(exc, "status_code", 500)
            logger.warning(
                "openrouter_status_error model=%s status=%s attempt=%d/%d",
                cfg.openrouter_model,
                status,
                attempt,
                max_attempts,
            )
            if status < 500 and status != 429:
                raise QueryParserError(
                    "openrouter_provider_error",
                    f"LLM provider returned error status {status}.",
                    status_code=502,
                ) from exc

        if attempt < max_attempts:
            await asyncio.sleep(0.4 * attempt)

    if isinstance(last_error, APITimeoutError):
        raise QueryParserError(
            "openrouter_timeout",
            "Natural-language search timed out. Please try again.",
            status_code=504,
        ) from last_error
    if isinstance(last_error, RateLimitError):
        raise QueryParserError(
            "openrouter_rate_limited",
            "Natural-language search is temporarily rate-limited. Please try again shortly.",
            status_code=429,
        ) from last_error
    raise QueryParserError(
        "openrouter_unavailable",
        "Natural-language search service is temporarily unavailable.",
        status_code=503,
    ) from last_error
