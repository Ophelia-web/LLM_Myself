import base64
import json
import logging
import mimetypes
import os
import re
from typing import Any

import httpx

logger = logging.getLogger(__name__)


GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)


def _resolve_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is required in environment variables.")
    return api_key


def _resolve_api_key(api_key: str | None = None) -> str:
    if api_key and api_key.strip():
        return api_key.strip()
    return _resolve_gemini_api_key()


def _build_gemini_url(model: str, api_key: str | None = None) -> str:
    return GEMINI_URL_TEMPLATE.format(model=model, api_key=_resolve_api_key(api_key))


async def generate_json_with_gemini(
    prompt: str,
    api_key: str | None = None,
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
    data = await _call_gemini(_build_gemini_url(model, api_key=api_key), payload)
    return _safe_json_parse(_extract_response_text(data))


async def generate_json_with_gemini_multimodal(
    prompt: str,
    image_urls: list[str],
    api_key: str | None = None,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.2,
) -> dict[str, Any]:
    cleaned_urls = [url.strip() for url in image_urls if url and url.strip()]
    logger.info("VLM multimodal request received with %s image URLs.", len(cleaned_urls))
    if not cleaned_urls:
        raise ValueError("No photo URLs available for multimodal analysis.")

    url = _build_gemini_url(model, api_key=api_key)
    inline_data_payload = await _build_inline_image_payload(
        prompt=prompt,
        image_urls=cleaned_urls[:3],
        temperature=temperature,
    )
    inline_response = await _call_gemini(url, inline_data_payload)
    return _safe_json_parse(_extract_response_text(inline_response))


async def _build_inline_image_payload(
    prompt: str,
    image_urls: list[str],
    temperature: float,
) -> dict[str, Any]:
    logger.info("[VLM] fetching image bytes for %s URLs", len(image_urls))
    parts: list[dict[str, Any]] = [{"text": prompt}]
    inline_images = 0
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for image_url in image_urls:
            try:
                response = await client.get(image_url)
                logger.info(
                    "[VLM] fetch status=%s content-type=%s url=%s",
                    response.status_code,
                    response.headers.get("content-type", ""),
                    image_url,
                )
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if not content_type.lower().startswith("image/"):
                    raise ValueError(
                        f"URL did not return image content-type: {content_type}"
                    )
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
                inline_images += 1
            except Exception as exc:
                logger.exception(
                    "Failed to fetch/encode image for multimodal analysis url=%s reason=%s",
                    image_url,
                    exc,
                )
                continue

    if inline_images == 0:
        raise ValueError("No image bytes were retrievable from the provided photo URLs.")

    logger.info("Prepared %s inline images for Gemini request.", inline_images)

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
        return "image/jpeg" if content_type == "image/jpg" else content_type
    guessed, _ = mimetypes.guess_type(image_url)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/jpeg"


async def _call_gemini(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            logger.info("[VLM] calling Gemini multimodal")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info("[VLM] raw Gemini response: %s", json.dumps(data)[:1500])
            return data
        except httpx.HTTPStatusError as exc:
            logger.exception(
                "Gemini API HTTP error status=%s body=%s",
                exc.response.status_code,
                exc.response.text,
            )
            raise
        except Exception as exc:
            logger.exception("Gemini API request failed: %s", exc)
            raise


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
        logger.exception("Failed to parse Gemini JSON response: %s", trimmed[:4000])
        raise ValueError(f"Model response was not valid JSON: {trimmed}") from exc

    if not isinstance(parsed, dict):
        logger.error("Gemini response was not a JSON object: %s", type(parsed).__name__)
        raise ValueError("Expected a JSON object from model response.")

    return parsed
