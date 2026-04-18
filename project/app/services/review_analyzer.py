import json
from pathlib import Path

from app.models.schemas import ReviewAnalysisResult
from app.services.llm_client import generate_json_with_gemini


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "review_prompt.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def analyze_reviews(
    restaurant_name: str,
    cuisine: str,
    reviews: list[dict],
) -> ReviewAnalysisResult:
    if not reviews:
        return ReviewAnalysisResult(
            signature_dishes=[],
            service="Unknown",
            value="Unknown",
            wait_impression="Unknown",
            vibe="Unknown",
            pros=["No review content available."],
            cons=[],
        )

    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        restaurant_name=restaurant_name,
        cuisine=cuisine,
        reviews_json=json.dumps(reviews, ensure_ascii=True),
    )

    payload = await generate_json_with_gemini(prompt=prompt)
    return ReviewAnalysisResult.model_validate(payload)
