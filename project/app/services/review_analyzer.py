import json
import re
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
        fallback_signature_dishes = _extract_signature_dishes_from_evidence(evidence)
        return ReviewAnalysisResult(
            signature_dishes=fallback_signature_dishes,
            service="Unknown",
            value="Unknown",
            wait_impression="Unknown",
            vibe="Unknown",
            pros=["Review analysis was unavailable."],
            cons=[],
            evidence=evidence,
        )

    llm_signature_dishes = payload.get("signature_dishes", [])
    fallback_signature_dishes = _extract_signature_dishes_from_evidence(evidence)
    normalized_signature_dishes = _merge_signature_dishes(
        llm_signature_dishes,
        fallback_signature_dishes,
    )

    merged_payload = {
        "signature_dishes": normalized_signature_dishes,
        "service": payload.get("service", "Unknown"),
        "value": payload.get("value", "Unknown"),
        "wait_impression": payload.get("wait_impression", "Unknown"),
        "vibe": payload.get("vibe", "Unknown"),
        "pros": payload.get("pros", []),
        "cons": payload.get("cons", []),
        "evidence": payload.get("evidence", [item.model_dump() for item in evidence]),
    }
    return ReviewAnalysisResult.model_validate(merged_payload)


def _merge_signature_dishes(
    llm_dishes: list[str],
    fallback_dishes: list[str],
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for dish in llm_dishes + fallback_dishes:
        cleaned = str(dish).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in {"unknown", "not available", "n/a"}:
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(cleaned)
        if len(normalized) >= 5:
            break
    return normalized


def _extract_signature_dishes_from_evidence(
    evidence: list[ReviewEvidence],
) -> list[str]:
    dish_patterns = [
        r"\bsashimi\b",
        r"\bedamame\b",
        r"\bramen\b",
        r"\bsushi\b",
        r"\brolls?\b",
        r"\bomakase\b",
        r"\bcurry\b",
        r"\bnoodles?\b",
        r"\bpasta\b",
        r"\bsteak\b",
        r"\bdumplings?\b",
        r"\btacos?\b",
        r"\bburgers?\b",
        r"\bpizza\b",
    ]
    found: list[str] = []
    seen: set[str] = set()
    for item in evidence:
        text = (item.text or "").lower()
        if not text:
            continue
        for pattern in dish_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            token = match.group(0).strip().lower()
            label = token[:-1] if token.endswith("s") else token
            if label in seen:
                continue
            seen.add(label)
            found.append(label)
            if len(found) >= 5:
                return found
    return found
