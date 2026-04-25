from app.models.schemas import DossierResult, RankedResult, ScoreBreakdown, SearchRequest


def rank_dossiers(dossiers: list[DossierResult], request: SearchRequest) -> list[RankedResult]:
    ranked: list[RankedResult] = []
    target_price = _budget_to_price_level(request.budget)
    cuisine_lower = request.cuisine.lower()

    for dossier in dossiers:
        cuisine_match = 30 if any(cuisine_lower in t.lower() for t in dossier.types) else 10

        budget_distance = abs((dossier.price_level or 2) - target_price)
        budget_match = max(0.0, 20 - budget_distance * 6.5)

        rating_score = min(20.0, (dossier.rating / 5.0) * 20)

        value_text = dossier.value.lower()
        if "great" in value_text or "excellent" in value_text:
            review_value_match = 10
        elif "good" in value_text:
            review_value_match = 8
        elif "poor" in value_text or "overpriced" in value_text:
            review_value_match = 1
        else:
            review_value_match = 5

        vibe_text = dossier.vibe.lower()
        if request.partySize >= 6 and ("spacious" in vibe_text or "group" in vibe_text):
            vibe_fit = 10
        elif request.partySize <= 2 and (
            "cozy" in vibe_text or "romantic" in vibe_text or "casual" in vibe_text
        ):
            vibe_fit = 10
        else:
            vibe_fit = 5

        visual_vibe_fit = _visual_vibe_fit(request.partySize, dossier)
        evidence_quality = _evidence_quality_score(dossier)

        wait_text = dossier.wait_impression.lower()
        if "long" in wait_text or "busy" in wait_text:
            wait_penalty = -10
        elif "moderate" in wait_text:
            wait_penalty = -4
        else:
            wait_penalty = 0

        total = (
            cuisine_match
            + budget_match
            + rating_score
            + review_value_match
            + vibe_fit
            + visual_vibe_fit
            + evidence_quality
            + wait_penalty
        )

        score_breakdown = ScoreBreakdown(
            cuisine_match=round(cuisine_match, 2),
            budget_match=round(budget_match, 2),
            rating=round(rating_score, 2),
            review_value_match=round(review_value_match, 2),
            vibe_fit=round(vibe_fit, 2),
            visual_vibe_fit=round(visual_vibe_fit, 2),
            evidence_quality=round(evidence_quality, 2),
            wait_penalty=round(wait_penalty, 2),
            total=round(total, 2),
        )

        ranked.append(RankedResult(score=score_breakdown, dossier=dossier))

    ranked.sort(key=lambda r: r.score.total, reverse=True)
    return ranked


def _budget_to_price_level(budget: str) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
        "luxury": 4,
    }.get((budget or "").lower(), 2)


def _evidence_quality_score(dossier: DossierResult) -> float:
    evidence_count = len(dossier.review_evidence)
    if evidence_count == 0:
        return 0
    if evidence_count == 1:
        return 5
    return 10


def _visual_vibe_fit(party_size: int, dossier: DossierResult) -> float:
    if not dossier.photo_urls:
        return 0

    visual = dossier.image_analysis.visual_vibe.lower()
    group_note = dossier.image_analysis.group_suitability.lower()
    summary = dossier.image_analysis.image_evidence_summary.lower()
    if "unavailable" in summary and dossier.image_analysis.visual_confidence.lower() == "low":
        return 0

    group_friendly_terms = {"spacious", "group", "large", "roomy", "family"}
    cozy_terms = {"cozy", "intimate", "casual", "small"}
    merged_text = f"{visual} {group_note} {summary}"

    if party_size >= 5 and any(term in merged_text for term in group_friendly_terms):
        return 10
    if party_size <= 2 and any(term in merged_text for term in cozy_terms):
        return 10
    if any(term in merged_text for term in group_friendly_terms.union(cozy_terms)):
        return 5
    return 0
