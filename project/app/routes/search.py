import os

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    APIResponse,
    DossierResult,
    ImageAnalysisResult,
    ReviewAnalysisResult,
    SearchRequest,
)
from app.services.dossier_generator import build_dossier
from app.services.geocode_zip import geocode_zip
from app.services.image_analyzer import analyze_restaurant_images
from app.services.photo_fetcher import build_photo_url
from app.services.places_retriever import retrieve_restaurant_candidates
from app.services.ranker import rank_dossiers
from app.services.report_writer import write_markdown_dossier
from app.services.review_rag import (
    build_review_chunks,
    retrieve_relevant_review_evidence,
)
from app.services.review_analyzer import analyze_reviews


router = APIRouter(tags=["search"])


@router.post("/api/search", response_model=APIResponse)
async def search_restaurants(payload: SearchRequest) -> APIResponse:
    try:
        maps_api_key = payload.googleMapsApiKey
        os.environ["GEMINI_API_KEY"] = payload.geminiApiKey

        geocode_result = await geocode_zip(payload.zipCode, maps_api_key=maps_api_key)

        candidates = await retrieve_restaurant_candidates(
            lat=geocode_result.lat,
            lng=geocode_result.lng,
            cuisine=payload.cuisine,
            maps_api_key=maps_api_key,
            limit=10,
        )

        if not candidates:
            return APIResponse(
                query=payload,
                total_candidates=0,
                top_results=[],
                notes=["No restaurants found for the requested location/cuisine."],
            )

        dossiers = []
        skipped_candidates = 0
        for candidate in candidates:
            try:
                review_chunks = build_review_chunks(candidate)
                relevant_evidence = retrieve_relevant_review_evidence(
                    chunks=review_chunks,
                    user_request=payload,
                    top_k=3,
                )
                review_analysis = await analyze_reviews(
                    restaurant_name=candidate.name,
                    cuisine=payload.cuisine,
                    evidence=relevant_evidence,
                )
            except Exception:
                review_analysis = ReviewAnalysisResult(
                    signature_dishes=[],
                    service="Unknown",
                    value="Unknown",
                    wait_impression="Unknown",
                    vibe="Unknown",
                    pros=["Review analysis failed for this candidate."],
                    cons=[],
                    evidence=[],
                )

            photo_urls = _build_photo_urls(candidate.photos, maps_api_key)

            try:
                image_analysis = await analyze_restaurant_images(
                    restaurant_name=candidate.name,
                    cuisine=payload.cuisine,
                    photo_urls=photo_urls,
                )
            except Exception:
                image_analysis = ImageAnalysisResult()

            try:
                dossier = await build_dossier(
                    place=candidate,
                    review_analysis=review_analysis,
                    user_request=payload,
                    image_analysis=image_analysis,
                    photo_urls=photo_urls,
                )
                dossiers.append(dossier)
            except Exception:
                skipped_candidates += 1
                fallback_dossier = _build_fallback_dossier(
                    candidate_name=candidate.name,
                    candidate_rating=candidate.rating,
                    candidate_price_level=candidate.price_level,
                    candidate_address=candidate.formatted_address,
                    candidate_types=candidate.types,
                    candidate_user_rating_count=candidate.user_rating_count,
                    candidate_location=candidate.location.model_dump(),
                    candidate_photos=candidate.photos,
                    candidate_reviews=candidate.reviews,
                    review_analysis=review_analysis,
                    image_analysis=image_analysis,
                    photo_urls=photo_urls,
                    reservation_link=candidate.reservation_link,
                    reservable=candidate.reservable,
                    maps_link=candidate.maps_link,
                    cuisine=payload.cuisine,
                )
                dossiers.append(fallback_dossier)

        if not dossiers:
            return APIResponse(
                query=payload,
                total_candidates=len(candidates),
                top_results=[],
                notes=[
                    "Candidate processing failed for all restaurants.",
                    "Check API keys, quotas, and provider availability.",
                ],
            )

        ranked = rank_dossiers(dossiers, payload)
        top_results = ranked[:3]

        for ranked_result in top_results:
            try:
                write_markdown_dossier(ranked_result)
            except Exception:
                continue

        return APIResponse(
            query=payload,
            total_candidates=len(candidates),
            top_results=top_results,
            notes=[
                "Ranked with rule-based scoring using cuisine, budget, ratings, review and visual evidence.",
                "Dossiers were written to output/dossiers as markdown files.",
                f"Skipped candidates due to processing errors: {skipped_candidates}.",
            ],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search pipeline failed: {exc}",
        ) from exc


def _build_photo_urls(photos: list[dict], maps_api_key: str) -> list[str]:
    if not photos:
        return []

    os.environ["GOOGLE_MAPS_API_KEY"] = maps_api_key
    photo_urls: list[str] = []
    for photo in photos[:3]:
        reference = str(photo.get("photo_reference", "")).strip()
        if not reference:
            continue
        photo_url = build_photo_url(reference, max_width=900)
        if photo_url:
            photo_urls.append(photo_url)
    return photo_urls


def _build_fallback_dossier(
    candidate_name: str,
    candidate_rating: float,
    candidate_price_level: int,
    candidate_address: str,
    candidate_types: list[str],
    candidate_user_rating_count: int,
    candidate_location: dict,
    candidate_photos: list[dict],
    candidate_reviews: list[dict],
    review_analysis: ReviewAnalysisResult,
    image_analysis: ImageAnalysisResult,
    photo_urls: list[str],
    reservation_link: str | None,
    reservable: bool | None,
    maps_link: str | None,
    cuisine: str,
) -> DossierResult:
    return DossierResult.model_validate(
        {
            "restaurant_name": candidate_name,
            "rating": candidate_rating,
            "price_level": candidate_price_level,
            "address": candidate_address,
            "signature_dishes": review_analysis.signature_dishes,
            "service": review_analysis.service,
            "value": review_analysis.value,
            "wait_impression": review_analysis.wait_impression,
            "vibe": review_analysis.vibe,
            "why_recommended": (
                f"Strong {cuisine} candidate with available structured place data."
            ),
            "types": candidate_types,
            "user_rating_count": candidate_user_rating_count,
            "location": candidate_location,
            "photos": candidate_photos,
            "reviews": candidate_reviews,
            "review_evidence": [item.model_dump() for item in review_analysis.evidence],
            "image_analysis": image_analysis.model_dump(),
            "photo_urls": photo_urls,
            "recommendation_confidence": "low",
            "reservation_link": reservation_link,
            "reservable": reservable,
            "maps_link": maps_link,
        }
    )
