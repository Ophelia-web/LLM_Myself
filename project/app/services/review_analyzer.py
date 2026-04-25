import json
from pathlib import Path

from app.models.schemas import ReviewAnalysisResult, ReviewEvidence
from app.services.llm_client import generate_json_with_gemini


PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "review_prompt.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


async def analyze_reviews(
    restaurant_name: str,
    cuisine: str,
    evidence: list[ReviewEvidence],
) -> ReviewAnalysisResult:
    if not evidence:
        return ReviewAnalysisResult(
            signature_dishes=[],
            service="Unknown",
            value="Unknown",
            wait_impression="Unknown",
            vibe="Unknown",
            pros=["No review evidence was available."],
            cons=[],
            evidence=[],
        )

    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        restaurant_name=restaurant_name,
        cuisine=cuisine,
        evidence_json=json.dumps([item.model_dump() for item in evidence], ensure_ascii=True),
    )

    try:
        payload = await generate_json_with_gemini(prompt=prompt)
    except Exception:
        return ReviewAnalysisResult(
            signature_dishes=[],
            service="Unknown",
            value="Unknown",
            wait_impression="Unknown",
            vibe="Unknown",
            pros=["Review analysis was unavailable."],
            cons=[],
            evidence=evidence,
        )

    merged_payload = {
        "signature_dishes": payload.get("signature_dishes", []),
        "service": payload.get("service", "Unknown"),
        "value": payload.get("value", "Unknown"),
        "wait_impression": payload.get("wait_impression", "Unknown"),
        "vibe": payload.get("vibe", "Unknown"),
        "pros": payload.get("pros", []),
        "cons": payload.get("cons", []),
        "evidence": payload.get("evidence", [item.model_dump() for item in evidence]),
    }
    return ReviewAnalysisResult.model_validate(merged_payload)
