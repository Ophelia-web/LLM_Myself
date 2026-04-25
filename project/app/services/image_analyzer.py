import json
import logging
from pathlib import Path

from app.models.schemas import ImageAnalysisResult
from app.services.llm_client import generate_json_with_gemini_multimodal


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "image_prompt.txt"
logger = logging.getLogger(__name__)


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def analyze_restaurant_images(
    restaurant_name: str,
    cuisine: str,
    photo_urls: list[str],
    gemini_api_key: str | None = None,
) -> ImageAnalysisResult:
    cleaned_urls = [url for url in photo_urls if url]
    logger.info("[VLM] incoming photo_urls=%s", cleaned_urls)
    logger.info(
        "Starting image analysis for '%s' with %s photo URLs.",
        restaurant_name,
        len(cleaned_urls),
    )
    if not cleaned_urls:
        logger.info("Skipping image analysis for '%s': no photo URLs.", restaurant_name)
        return ImageAnalysisResult()

    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        restaurant_name=restaurant_name,
        cuisine=cuisine,
        photo_urls_json=json.dumps(cleaned_urls, ensure_ascii=True),
    )

    try:
        payload = await generate_json_with_gemini_multimodal(
            prompt=prompt,
            image_urls=cleaned_urls,
            api_key=gemini_api_key,
            model="gemini-2.5-flash",
        )
        return ImageAnalysisResult.model_validate(payload)
    except Exception as exc:
        print("[VLM ERROR]", repr(exc))
        logger.exception(
            "Image analysis failed for '%s'. Falling back to unknown values. reason=%s",
            restaurant_name,
            exc,
        )
        return ImageAnalysisResult()
