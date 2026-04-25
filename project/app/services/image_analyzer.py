import json
from pathlib import Path

from app.models.schemas import ImageAnalysisResult
from app.services.llm_client import generate_json_with_gemini_multimodal


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "image_prompt.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def analyze_restaurant_images(
    restaurant_name: str,
    cuisine: str,
    photo_urls: list[str],
) -> ImageAnalysisResult:
    cleaned_urls = [url for url in photo_urls if url]
    if not cleaned_urls:
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
        )
        return ImageAnalysisResult.model_validate(payload)
    except Exception:
        return ImageAnalysisResult()
