import json
from pathlib import Path

from app.models.schemas import DossierResult, PlaceResult, ReviewAnalysisResult, SearchQuery
from app.services.llm_client import generate_json_with_gemini


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "dossier_prompt.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def build_dossier(
    place: PlaceResult,
    review_analysis: ReviewAnalysisResult,
    user_request: SearchQuery,
    gemini_api_key: str,
) -> DossierResult:
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        user_request_json=json.dumps(user_request.model_dump(), ensure_ascii=True),
        place_json=json.dumps(place.model_dump(), ensure_ascii=True),
        review_analysis_json=json.dumps(review_analysis.model_dump(), ensure_ascii=True),
    )

    llm_payload = await generate_json_with_gemini(
        prompt=prompt,
        api_key=gemini_api_key,
    )

    merged = {
        "restaurant_name": place.name,
        "rating": place.rating,
        "price_level": place.price_level,
        "address": place.formatted_address,
        "summary": llm_payload.get(
            "summary",
            f"{place.name} is a well-rated option for {user_request.cuisine} in {user_request.zipCode}.",
        ),
        "signature_dishes": llm_payload.get(
            "signature_dishes", review_analysis.signature_dishes
        ),
        "service": llm_payload.get("service", review_analysis.service),
        "value": llm_payload.get("value", review_analysis.value),
        "wait_impression": llm_payload.get(
            "wait_impression", review_analysis.wait_impression
        ),
        "vibe": llm_payload.get("vibe", review_analysis.vibe),
        "why_recommended": llm_payload.get(
            "why_recommended",
            f"Matches requested cuisine ({user_request.cuisine}) with a rating of {place.rating}.",
        ),
        "types": place.types,
        "user_rating_count": place.user_rating_count,
        "location": place.location,
        "photos": place.photos,
        "reviews": place.reviews,
    }

    return DossierResult.model_validate(merged)
