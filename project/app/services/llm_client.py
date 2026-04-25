import base64
import json
import mimetypes
import os
import re
from typing import Any

import httpx


GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)


def _resolve_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required in environment variables.")
    return api_key


def _build_gemini_url(model: str) -> str:
    return GEMINI_URL_TEMPLATE.format(model=model, api_key=_resolve_gemini_api_key())


async def generate_json_with_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
) -> dict[str, Any]:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }
    data = await _call_gemini(_build_gemini_url(model), payload)
    return _safe_json_parse(_extract_response_text(data))


async def generate_json_with_gemini_multimodal(
    prompt: str,
    image_urls: list[str],
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
) -> dict[str, Any]:
    cleaned_urls = [url.strip() for url in image_urls if url and url.strip()]
    if not cleaned_urls:
        return await generate_json_with_gemini(
            prompt=prompt,
            model=model,
            temperature=temperature,
        )

    url = _build_gemini_url(model)
    direct_payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
                + [
                    {
                        "file_data": {
                            "file_uri": image_url,
                            "mime_type": "image/jpeg",
                        }
                    }
                    for image_url in cleaned_urls
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }

    try:
        direct_data = await _call_gemini(url, direct_payload)
        return _safe_json_parse(_extract_response_text(direct_data))
    except Exception:
        pass

    inline_data_payload = await _build_inline_image_payload(
        prompt=prompt,
        image_urls=cleaned_urls,
        temperature=temperature,
    )
    inline_response = await _call_gemini(url, inline_data_payload)
    return _safe_json_parse(_extract_response_text(inline_response))


async def _build_inline_image_payload(
    prompt: str,
    image_urls: list[str],
    temperature: float,
) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"text": prompt}]
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for image_url in image_urls:
            try:
                response = await client.get(image_url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                mime_type = _resolve_mime_type(image_url, content_type)
                encoded_bytes = base64.b64encode(response.content).decode("ascii")
                parts.append(
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_bytes,
                        }
                    }
                )
            except Exception:
                continue

    if len(parts) == 1:
        parts.append(
            {
                "text": (
                    "No image bytes were retrievable from provided URLs. "
                    "Return conservative 'unknown' values."
                )
            }
        )

    return {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
        },
    }


def _resolve_mime_type(image_url: str, content_type_header: str) -> str:
    content_type = content_type_header.split(";")[0].strip().lower()
    if content_type.startswith("image/"):
        return content_type
    guessed, _ = mimetypes.guess_type(image_url)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


async def _call_gemini(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


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
