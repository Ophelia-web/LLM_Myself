from pathlib import Path
import re

from app.models.schemas import RankedResult


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "dossiers"


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def write_markdown_dossier(result: RankedResult) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    restaurant = result.dossier
    slug = _slugify(restaurant.restaurant_name) or "restaurant"
    file_path = OUTPUT_DIR / f"{slug}.md"

    lines = [
        f"# {restaurant.restaurant_name}",
        "",
        "## Recommendation Snapshot",
        f"- **Rating:** {restaurant.rating}",
        f"- **Address:** {restaurant.address}",
        (
            f"- **Reservation:** Available ({restaurant.reservation_link})"
            if restaurant.reservable and restaurant.reservation_link
            else (
                "- **Reservation:** Not available"
                if restaurant.reservable is False
                else (
                    f"- **Reservation details:** {restaurant.reservation_link}"
                    if restaurant.reservation_link
                    else "- **Reservation:** Unknown"
                )
            )
        ),
        f"- **Why recommended:** {restaurant.why_recommended}",
        "",
        "## Experience Dossier",
        f"- **Signature dishes:** {', '.join(restaurant.signature_dishes) if restaurant.signature_dishes else 'Not enough data'}",
        f"- **Service:** {restaurant.service}",
        f"- **Value:** {restaurant.value}",
        f"- **Vibe:** {restaurant.vibe}",
        f"- **Wait impression:** {restaurant.wait_impression}",
        "",
        "## Ranking Score Breakdown",
        f"- Cuisine match: {result.score.cuisine_match}",
        f"- Budget match: {result.score.budget_match}",
        f"- Rating: {result.score.rating}",
        f"- Review value match: {result.score.review_value_match}",
        f"- Vibe fit: {result.score.vibe_fit}",
        f"- Wait penalty: {result.score.wait_penalty}",
        f"- **Total score: {result.score.total}**",
        "",
    ]

    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path
