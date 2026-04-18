from app.models.schemas import DossierResult, RankedResult, ScoreBreakdown, SearchQuery


def _budget_to_price_level(budget: str) -> int:
    mapping = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "luxury": 4,
    }
    return mapping.get(budget.lower(), 2)


def rank_dossiers(dossiers: list[DossierResult], request: SearchQuery) -> list[RankedResult]:
    ranked: list[RankedResult] = []
    target_price = _budget_to_price_level(request.budget)
    cuisine_lower = request.cuisine.lower()

    for dossier in dossiers:
        cuisine_match = 20 if any(cuisine_lower in t.lower() for t in dossier.types) else 8

        budget_distance = abs((dossier.price_level or 2) - target_price)
        budget_match = max(0, 20 - budget_distance * 7)

        rating_score = min(25, (dossier.rating / 5.0) * 25)

        value_text = dossier.value.lower()
        if "great" in value_text or "excellent" in value_text:
            review_value_match = 15
        elif "good" in value_text:
            review_value_match = 10
        elif "poor" in value_text or "overpriced" in value_text:
            review_value_match = 3
        else:
            review_value_match = 7

        vibe_text = dossier.vibe.lower()
        if request.partySize >= 6 and ("spacious" in vibe_text or "group" in vibe_text):
            vibe_fit = 10
        elif request.partySize <= 2 and ("cozy" in vibe_text or "romantic" in vibe_text):
            vibe_fit = 10
        else:
            vibe_fit = 6

        wait_text = dossier.wait_impression.lower()
        if "long" in wait_text or "busy" in wait_text:
            wait_penalty = -8
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
            + wait_penalty
        )

        score_breakdown = ScoreBreakdown(
            cuisine_match=round(cuisine_match, 2),
            budget_match=round(budget_match, 2),
            rating=round(rating_score, 2),
            review_value_match=round(review_value_match, 2),
            vibe_fit=round(vibe_fit, 2),
            wait_penalty=round(wait_penalty, 2),
            total=round(total, 2),
        )

        ranked.append(RankedResult(score=score_breakdown, dossier=dossier))

    ranked.sort(key=lambda r: r.score.total, reverse=True)
    return ranked
