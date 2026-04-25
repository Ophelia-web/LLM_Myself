import json
from pathlib import Path

from app.models.schemas import (
    DossierResult,
    ImageAnalysisResult,
    PlaceResult,
    ReviewAnalysisResult,
    SearchRequest,
)
from app.services.llm_client import generate_json_with_gemini


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "dossier_prompt.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def build_dossier(
    place: PlaceResult,
    review_analysis: ReviewAnalysisResult,
    user_request: SearchRequest,
    image_analysis: ImageAnalysisResult,
    photo_urls: list[str],
) -> DossierResult:
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        user_request_json=json.dumps(
            user_request.model_dump(exclude={"googleMapsApiKey", "geminiApiKey"}),
            ensure_ascii=True,
        ),
        place_json=json.dumps(place.model_dump(), ensure_ascii=True),
        review_analysis_json=json.dumps(review_analysis.model_dump(), ensure_ascii=True),
        review_evidence_json=json.dumps(
            [item.model_dump() for item in review_analysis.evidence],
            ensure_ascii=True,
        ),
        image_analysis_json=json.dumps(image_analysis.model_dump(), ensure_ascii=True),
        photo_urls_json=json.dumps(photo_urls, ensure_ascii=True),
    )

    llm_payload: dict = {}
    try:
        llm_payload = await generate_json_with_gemini(prompt=prompt)
    except Exception:
        llm_payload = {}

    evidence_mention = ""
    if review_analysis.evidence:
        evidence_mention = " supported by review snippets"
    if image_analysis.visual_confidence.lower() in {"medium", "high"}:
        evidence_mention += " and photos"
    fallback_reason = (
        f"Matches {user_request.cuisine} preferences with solid ratings"
        f"{evidence_mention}."
    )
    candidate_signature_dishes = _clean_signature_dishes(
        llm_payload.get("signature_dishes", [])
    ) or _clean_signature_dishes(review_analysis.signature_dishes)
    summary = _build_summary(
        llm_summary=llm_payload.get("summary", ""),
        review_analysis=review_analysis,
        image_analysis=image_analysis,
        signature_dishes=candidate_signature_dishes,
        user_request=user_request,
    )

    merged = {
        "restaurant_name": place.name,
        "rating": place.rating,
        "price_level": place.price_level,
        "address": place.formatted_address,
        "signature_dishes": candidate_signature_dishes,
        "service": llm_payload.get("service", review_analysis.service),
        "value": llm_payload.get("value", review_analysis.value),
        "wait_impression": llm_payload.get(
            "wait_impression", review_analysis.wait_impression
        ),
        "vibe": llm_payload.get("vibe", review_analysis.vibe),
        "summary": summary,
        "why_recommended": llm_payload.get(
            "why_recommended",
            fallback_reason,
        ),
        "types": place.types,
        "user_rating_count": place.user_rating_count,
        "location": place.location,
        "photos": place.photos,
        "reviews": place.reviews,
        "review_evidence": [item.model_dump() for item in review_analysis.evidence],
        "image_analysis": image_analysis.model_dump(),
        "photo_urls": photo_urls,
        "recommendation_confidence": _build_confidence(
            review_evidence_count=len(review_analysis.evidence),
            visual_confidence=image_analysis.visual_confidence,
        ),
        "reservable": place.reservable,
        "reservation_link": place.reservation_link,
        "maps_link": place.maps_link,
    }

    return DossierResult.model_validate(merged)


def _build_confidence(review_evidence_count: int, visual_confidence: str) -> str:
    visual = (visual_confidence or "low").lower()
    if review_evidence_count >= 2 and visual in {"medium", "high"}:
        return "high"
    if review_evidence_count == 0 and visual == "low":
        return "low"
    return "medium"


def _clean_signature_dishes(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in {"unknown", "not available", "n/a"}:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(text)
    return cleaned


def _is_meaningful_text(value: str | None) -> bool:
    if value is None:
        return False
    cleaned = str(value).strip()
    if not cleaned:
        return False
    return cleaned.lower() not in {"unknown", "not available", "n/a", "none"}


def _build_summary(
    llm_summary: str,
    review_analysis: ReviewAnalysisResult,
    image_analysis: ImageAnalysisResult,
    signature_dishes: list[str],
    user_request: SearchRequest,
) -> str:
    if _is_meaningful_text(llm_summary):
        return str(llm_summary).strip()

    parts: list[str] = []
    if signature_dishes:
        shown = ", ".join(signature_dishes[:2])
        parts.append(f"Known for {shown}")

    if _is_meaningful_text(review_analysis.value):
        parts.append(str(review_analysis.value).strip())
    if _is_meaningful_text(review_analysis.service):
        parts.append(f"service is {str(review_analysis.service).strip()}")
    if _is_meaningful_text(review_analysis.vibe):
        parts.append(f"vibe feels {str(review_analysis.vibe).strip()}")
    if _is_meaningful_text(review_analysis.wait_impression):
        parts.append(f"wait is {str(review_analysis.wait_impression).strip()}")

    if _is_meaningful_text(image_analysis.image_evidence_summary):
        image_summary = str(image_analysis.image_evidence_summary).strip()
        if "unavailable" not in image_summary.lower():
            parts.append(image_summary)

    fit_parts: list[str] = []
    if _is_meaningful_text(user_request.cuisine):
        fit_parts.append(f"{user_request.cuisine} cuisine")
    if _is_meaningful_text(user_request.budget):
        fit_parts.append(f"{user_request.budget} budget")
    if user_request.partySize:
        fit_parts.append(f"party size {user_request.partySize}")
    if fit_parts:
        parts.append(f"suitable for a {' and '.join(fit_parts)} plan")

    if not parts:
        return "Limited structured summary available from the current review evidence."

    summary = "; ".join(parts[:4]).strip()
    if not summary.endswith("."):
        summary = f"{summary}."
    return summary
