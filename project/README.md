# Restaurant Recommendation Demo (FastAPI)

A minimal but runnable web demo that takes user preferences and returns top restaurant recommendations.

## Architecture summary

This project follows a modular pipeline inspired by lightweight agentic backends:

1. **Frontend form** (`templates/index.html` + `static/app.js`) submits user preferences.
2. **Search route** (`routes/search.py`) orchestrates all steps.
3. **Geocoder service** (`services/geocode_zip.py`) converts ZIP code to lat/lng.
4. **Places service** (`services/places_retriever.py`) fetches nearby restaurant candidates and details.
5. **Review analyzer** (`services/review_analyzer.py`) calls Gemini to extract structured review signals.
6. **Dossier generator** (`services/dossier_generator.py`) merges place metadata + review insights into a concise dossier.
7. **Rule ranker** (`services/ranker.py`) scores candidates with explicit breakdowns.
8. **Report writer** (`services/report_writer.py`) writes markdown dossiers to `output/dossiers/`.

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
      review_analyzer.py
      dossier_generator.py
      ranker.py
      report_writer.py
      llm_client.py
    models/
      schemas.py
    prompts/
      review_prompt.txt
      dossier_prompt.txt
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

## API key handling

No server-side API key env vars are required for normal usage.

Users enter their own `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY` in the web form.
The frontend sends keys with each `/api/search` request, and the backend does not echo
them back in the response payload.

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
        "cuisine_match": 20,
        "budget_match": 20,
        "rating": 22.5,
        "review_value_match": 10,
        "vibe_fit": 6,
        "wait_penalty": -4,
        "total": 74.5
      },
      "dossier": {
        "restaurant_name": "Example Restaurant",
        "rating": 4.5,
        "price_level": 2,
        "address": "123 Example St",
        "summary": "A reliable mid-priced Japanese spot with consistent feedback.",
        "signature_dishes": ["ramen", "karaage"],
        "service": "Friendly and attentive.",
        "value": "Good portions for the price.",
        "wait_impression": "Moderate waits during peak hours.",
        "vibe": "Casual and energetic.",
        "why_recommended": "Matches your cuisine and budget with strong ratings."
      }
    }
  ],
  "notes": ["..."]
}
```

## Notes

- The code uses async `httpx` calls for external APIs.
- LLM interactions are centralized in `services/llm_client.py`.
- Prompts are kept in `app/prompts/` for easy iteration.
- The pipeline is intentionally modular and easy to extend.
