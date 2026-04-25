from __future__ import annotations

import re

from app.models.schemas import PlaceResult, ReviewEvidence, SearchRequest


def build_review_chunks(place: PlaceResult) -> list[ReviewEvidence]:
    chunks: list[ReviewEvidence] = []
    for review in place.reviews:
        text = str(review.get("text", "")).strip()
        if not text:
            continue
        chunks.append(
            ReviewEvidence(
                text=text,
                rating=review.get("rating", 0),
                author_name=str(review.get("author_name", "")).strip(),
                relative_time_description=str(
                    review.get("relative_time_description", "")
                ).strip(),
                source="Google Places review",
                matched_terms=[],
            )
        )
    return chunks


def retrieve_relevant_review_evidence(
    chunks: list[ReviewEvidence],
    user_request: SearchRequest,
    top_k: int = 3,
) -> list[ReviewEvidence]:
    if not chunks:
        return []

    query_terms = _build_request_terms(user_request)
    if not query_terms:
        return chunks[:top_k]

    ranked: list[tuple[int, int, ReviewEvidence]] = []
    for index, chunk in enumerate(chunks):
        chunk_terms = _tokenize(chunk.text)
        matches = sorted(query_terms.intersection(chunk_terms))
        score = len(matches)
        if score <= 0:
            continue
        ranked.append((score, -index, chunk.model_copy(update={"matched_terms": matches})))

    if not ranked:
        return chunks[:top_k]

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:top_k]]


def _build_request_terms(user_request: SearchRequest) -> set[str]:
    terms: set[str] = set()
    seed_text = [
        user_request.cuisine,
        user_request.budget,
        str(user_request.partySize),
        user_request.value,
        user_request.service,
        user_request.wait,
        user_request.vibe,
        user_request.group_suitability,
        user_request.portion,
        "signature dishes " + " ".join(user_request.signature_dishes or []),
        "group suitability",
        "portion size",
        "service quality",
        "wait time",
        "noisy" if user_request.noisy else "",
        "quiet" if user_request.quiet else "",
        "casual" if user_request.casual else "",
        "upscale" if user_request.upscale else "",
    ]
    for value in seed_text:
        terms.update(_tokenize(value))
    return terms


def _tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1}
