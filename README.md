# Samsung Smart Troubleshooter

A compact troubleshooting engine that accepts a user issue and Samsung SIIS response text, extracts a structured goal, matches it to the device deeplink catalog, and returns a JSON response payload with validation and fallback behavior.

## Project layout

- `src/api.py` – FastAPI app with `/health` and `/v1/troubleshoot`
- `src/extract.py` – extraction of a Goal-shaped object from query + SIIS content
- `src/validators.py` – rule validation and output sanitization
- `src/match_deeplink.py` – BM25 + dense candidate matching and `dummy_positive` fallback
- `src/order_actions.py` – action sequencing and grouping
- `src/enrich_query.py` – normalized query variants and semantic cache logic
- `src/schema.py` – Pydantic response schema
- `validate_schema.py` – sample validation script
- `tests/` – regression and validation tests
- `samples/` – ground truth inputs and schema sample payloads

## Requirements

- Python 3.11+
- pip

## Setup

From the project directory:

```bash
cd /path/to/SamsungSmartTroubleShooter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the app

### Option 1: direct entry point

```bash
cd /path/to/SamsungSmartTroubleShooter
source .venv/bin/activate
python3 main.py
```

### Option 2: uvicorn

```bash
cd /path/to/SamsungSmartTroubleShooter
source .venv/bin/activate
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

The app listens on:

- `http://localhost:8000/health`
- `http://localhost:8000/v1/troubleshoot`

## Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status": "ok"}
```

## Troubleshoot request

```bash
curl -X POST http://localhost:8000/v1/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{
    "query": "My Galaxy phone screen is blank",
    "siis_response": {
      "title": "Blank or black display on a Samsung phone or tablet",
      "content": "## Step 1: Check the charger and USB cable. ## Step 2: Force a restart. ## Step 3: Charge for 1 hour."
    }
  }'
```

The API returns JSON-only payloads with:

- `query`
- `response`
- `query_variations`
- `meta`
- `fallback` when applicable

## Validation and checks

Run the regression suite:

```bash
cd /path/to/SamsungSmartTroubleShooter
source .venv/bin/activate
pytest -q
```

Run schema validation against the sample data:

```bash
cd /path/to/SamsungSmartTroubleShooter
source .venv/bin/activate
python3 validate_schema.py
```

## Notes

- The app never fabricates a plan without source-backed data.
- Deeplink selection is grounded in catalog text, not URI string matching.
- Missing or low-confidence matches fall back to the literal `bixby://dummy_positive` placeholder.
- Output is sanitized to remove markdown fences and non-JSON conversational preambles.
