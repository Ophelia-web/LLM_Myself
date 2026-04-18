from fastapi import APIRouter, HTTPException, status

from app.models.schemas import APIResponse, SearchQuery, SearchRequest
from app.services.dossier_generator import build_dossier
from app.services.geocode_zip import geocode_zip
from app.services.places_retriever import retrieve_restaurant_candidates
from app.services.ranker import rank_dossiers
from app.services.report_writer import write_markdown_dossier
from app.services.review_analyzer import analyze_reviews


router = APIRouter(tags=["search"])


@router.post("/api/search", response_model=APIResponse)
async def search_restaurants(payload: SearchRequest) -> APIResponse:
    try:
        maps_api_key = payload.googleMapsApiKey
        gemini_api_key = payload.geminiApiKey
        query = SearchQuery(
            zipCode=payload.zipCode,
            cuisine=payload.cuisine,
            partySize=payload.partySize,
            budget=payload.budget,
        )

        geocode_result = await geocode_zip(query.zipCode, maps_api_key=maps_api_key)

        candidates = await retrieve_restaurant_candidates(
            lat=geocode_result.lat,
            lng=geocode_result.lng,
            cuisine=query.cuisine,
            maps_api_key=maps_api_key,
            limit=10,
        )

        if not candidates:
            return APIResponse(
                query=query,
                total_candidates=0,
                top_results=[],
                notes=["No restaurants found for the requested location/cuisine."],
            )

        dossiers = []
        skipped_candidates = 0
        for candidate in candidates:
            try:
                review_analysis = await analyze_reviews(
                    restaurant_name=candidate.name,
                    cuisine=query.cuisine,
                    reviews=candidate.reviews,
                    gemini_api_key=gemini_api_key,
                )
                dossier = await build_dossier(
                    place=candidate,
                    review_analysis=review_analysis,
                    user_request=query,
                    gemini_api_key=gemini_api_key,
                )
                dossiers.append(dossier)
            except Exception:
                skipped_candidates += 1
                continue

        if not dossiers:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Candidate processing failed for all restaurants. "
                    "Check API keys, quotas, and provider availability."
                ),
            )

        ranked = rank_dossiers(dossiers, query)
        top_results = ranked[:3]

        for ranked_result in top_results:
            write_markdown_dossier(ranked_result)

        return APIResponse(
            query=query,
            total_candidates=len(candidates),
            top_results=top_results,
            notes=[
                "Ranked with rule-based scoring using cuisine, budget, ratings, vibe, and wait fit.",
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
