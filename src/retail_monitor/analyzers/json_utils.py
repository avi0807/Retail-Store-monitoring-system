"""JSON helpers for parsing LLM responses defensively."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def parse_json_response(text: str) -> dict[str, Any]:
    """Robustly extract a JSON object from an LLM response string."""
    if not text:
        raise ValueError("Empty response from LLM")

    cleaned = text.strip()

    fence_match = _FENCE_RE.search(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"No JSON object found in response: {text[:200]!r}")

    candidate = cleaned[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        logger.debug("Initial JSON parse failed: %s", exc)

    # Tolerate trailing commas as a last resort.
    sanitized = re.sub(r",(\s*[}\]])", r"\1", candidate)
    return json.loads(sanitized)


def sanitize_items_list(items: Any) -> list:
    """Coerce LLM-produced lists of items to a list of dicts."""
    if not isinstance(items, list):
        return []
    out = []
    for item in items:
        if isinstance(item, dict):
            out.append(item)
        elif isinstance(item, str):
            out.append(
                {
                    "object": item,
                    "current_location": "unknown",
                    "should_be": "unknown",
                }
            )
    return out
