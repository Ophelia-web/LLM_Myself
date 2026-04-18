import json
import os
import re
from typing import Any

import httpx


GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)


async def generate_json_with_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required.")

    url = GEMINI_URL_TEMPLATE.format(model=model, api_key=api_key)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    text = _extract_response_text(data)
    return _safe_json_parse(text)


def _extract_response_text(response_json: dict[str, Any]) -> str:
    candidates = response_json.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("Gemini returned no content parts.")

    text = parts[0].get("text", "")
    if not text:
        raise ValueError("Gemini returned empty text.")

    return text


def _safe_json_parse(raw_text: str) -> dict[str, Any]:
    trimmed = raw_text.strip()

    if trimmed.startswith("```"):
        trimmed = re.sub(r"^```(?:json)?", "", trimmed).strip()
        trimmed = re.sub(r"```$", "", trimmed).strip()

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {trimmed}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object from model response.")

    return parsed
