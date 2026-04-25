# Restaurant Recommendation Demo (FastAPI)

A runnable LLM + RAG + VLM demo that accepts dining preferences and returns transparent Top-3 recommendations with evidence.

## LLM + RAG + VLM Pipeline

1. **Google Places retrieval** finds nearby candidates with ratings, reviews, photos, and metadata.
2. **Lightweight review RAG** turns each review into an evidence chunk and retrieves the most relevant snippets using keyword overlap (no vector DB).
3. **Gemini review analysis** analyzes only retrieved review evidence and produces strict JSON.
4. **Gemini VLM image analysis** analyzes restaurant photos with multimodal prompting.
5. **Dossier generation** merges place metadata + review evidence + image evidence into a structured recommendation dossier.
6. **Rule-based ranking** scores candidates with an explicit score breakdown and returns Top-3 results.

## Folder tree

```text
project/
  app/
    main.py
    routes/
      search.py
    services/
      geocode_zip.py
      places_retriever.py
      review_rag.py
      review_analyzer.py
      photo_fetcher.py
      image_analyzer.py
      dossier_generator.py
      ranker.py
      report_writer.py
      llm_client.py
    models/
      schemas.py
    prompts/
      review_prompt.txt
      dossier_prompt.txt
      image_prompt.txt
    templates/
      index.html
    static/
      app.js
      styles.css
  output/
    dossiers/
  requirements.txt
  .env.example
  README.md
```

## Installation

```bash
cd project
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

The frontend sends API keys in each request. The backend sets them in process env for service clients:

- `GOOGLE_MAPS_API_KEY` (used for photo URL generation in the pipeline)
- `GEMINI_API_KEY` (used by text and multimodal Gemini calls)

You can still run local testing by entering both keys in the UI Advanced Settings.

## Run locally

```bash
cd project
uvicorn app.main:app --reload --port 8000
```

Open: `http://localhost:8000`

Health: `GET /health`

## Request/response shape

### Request (`POST /api/search`)

```json
{
  "googleMapsApiKey": "AIza...",
  "geminiApiKey": "AIza...",
  "zipCode": "94103",
  "cuisine": "japanese",
  "partySize": 4,
  "budget": "medium"
}
```

> API keys are supplied by the end user in the browser form and sent per request.
> The backend response does not include these keys.

### Response (truncated)

```json
{
  "query": {
    "zipCode": "94103",
    "cuisine": "japanese",
    "partySize": 4,
    "budget": "medium"
  },
  "total_candidates": 10,
  "top_results": [
    {
      "score": {
        "cuisine_match": 30,
        "budget_match": 20,
        "rating": 18,
        "review_value_match": 10,
        "vibe_fit": 7,
        "visual_vibe_fit": 8,
        "evidence_quality": 10,
        "wait_penalty": -4,
        "total": 79
      },
      "dossier": {
        "restaurant_name": "Example Restaurant",
        "rating": 4.5,
        "price_level": 2,
        "address": "123 Example St",
        "signature_dishes": ["ramen", "karaage"],
        "service": "Friendly and attentive.",
        "value": "Good portions for the price.",
        "wait_impression": "Moderate waits during peak hours.",
        "vibe": "Casual and energetic.",
        "photo_urls": ["https://maps.googleapis.com/maps/api/place/photo?..."],
        "review_evidence": [
          {
            "text": "Great service and cozy seating for small groups.",
            "rating": 5,
            "author_name": "Alex",
            "relative_time_description": "3 months ago",
            "source": "Google Places review",
            "matched_terms": ["service", "cozy", "groups"]
          }
        ],
        "image_analysis": {
          "visual_vibe": "casual and cozy",
          "space_impression": "small but comfortable",
          "food_visual_cues": ["simple plating"],
          "group_suitability": "better for small groups",
          "visual_confidence": "medium",
          "image_evidence_summary": "Photos show close table spacing and casual decor."
        },
        "reservable": true,
        "reservation_link": "https://maps.google.com/?cid=...",
        "why_recommended": "Matches your cuisine and budget with strong ratings."
      }
    }
  ],
  "notes": ["..."]
}
```

## API limitations

- Google Places results depend on location density, API quota, and detail availability.
- Review evidence retrieval is lexical keyword overlap, so semantic misses are possible.
- Gemini outputs may vary by model availability and provider-side behavior.
- Image analysis quality depends on photo quality and whether photo URLs are retrievable.

## Fallback behavior

The app is built to continue gracefully:

- no reviews -> empty review evidence + `Unknown` review analysis fields
- no photos -> empty `photo_urls`, image-analysis fallback values
- Gemini review failure on one candidate -> fallback analysis for that candidate
- VLM failure on one candidate -> fallback image analysis for that candidate
- partial Google Places records -> best-effort normalized place metadata

If one candidate fails during module processing, the route continues processing remaining candidates and still returns valid JSON.

## Class demo script (quick talk track)

1. Enter ZIP, cuisine, party size, and budget.
2. Show that results include evidence-backed rationale, not only ratings.
3. Open **Review RAG Evidence** to show retrieved snippets.
4. Open **VLM Image Analysis** to show visual cues and confidence.
5. Open **Score Breakdown** to explain transparent ranking logic.
6. Mention fallback behavior for missing reviews/photos and module failures.

## Notes

- Async `httpx` calls are used for external APIs.
- LLM calls are centralized in `services/llm_client.py`.
- Prompts are versioned in `app/prompts/`.
- The pipeline is modular for easy extension (vector retrieval, deeper ranking rules, etc.).
