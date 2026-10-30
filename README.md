# Common Ground 🌍✨
> **A taste-fair group trip planner powered by Qloo's Cultural AI.**

Common Ground helps groups of friends plan unforgettable trips by analyzing everyone's unique cultural tastes (music, dining, fashion, art, architecture) and finding shared affinities and balanced, fair compromises for hotels, dining, and daily activities.

---

## 📁 Repository Structure

```text
CommonGround/
├── backend/                   # Python FastAPI & Qloo intelligence backend
│   ├── __init__.py
│   ├── models.py              # Pydantic schemas (Trip, Profile, Candidate, Plan, PlanStop)
│   ├── db.py                  # SQLite & SQLAlchemy models, migrations, and session management
│   ├── qloo_client.py         # Unified Qloo API client (caching, retries, audit logs)
│   ├── mock_data.py           # Realistic offline data for Lisbon & Tokyo (6 categories)
│   ├── scoring.py             # Taste-fairness algorithms (group score, taste debt, bridges)
│   ├── pipeline.py            # Modular trip generator for any group, city, or duration
│   ├── llm.py                 # Swappable LLM wrapper (OpenAI, Gemini, mock) with structured JSON
│   ├── validation.py          # Grounding validation (rejects hallucinations, fails safely)
│   ├── agent.py               # Autonomous planner with streaming progress & self-critique
│   ├── run_group_demo.py      # 4-friend live Lisbon demo script with real Qloo data
│   ├── run_cli.py             # CLI runner for agent pipeline, taste demo, and single queries
│   ├── main.py                # FastAPI REST endpoints with SSE streaming & CORS
│   ├── tests/                 # Unit & integration tests (49 automated test cases)
│   │   ├── test_agent_and_validation.py
│   │   ├── test_api.py        # Complete REST API lifecycle & endpoint tests
│   │   ├── test_qloo_integration.py
│   │   └── test_scoring.py
│   └── requirements.txt       # Python package dependencies
├── data/                      # Local SQLite database, audit logs & demo plan
│   ├── common_ground.db       # Local SQLite database (trips, profiles, plans, qloo_cache)
│   ├── demo_plan.json         # Reference plan JSON output
│   └── qloo_log.jsonl         # Raw Qloo request/response audit log
├── frontend/                  # Modern UI application (React / Next.js / Vite)
├── pytest.ini                 # Pytest configuration
├── .env.example               # Template for environment variables
├── .gitignore                 # Configured to ignore secrets, caches, and DB files
└── README.md                  # This guide
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
Make sure you have **Python 3.10 or newer** installed:
```bash
python3 --version
```

### 2. Set Up Virtual Environment & Dependencies

From the project root (`CommonGround/`):

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt
```

---

## ⚙️ Environment Configuration

Copy `.env.example` to create your local `.env`:

```bash
cp .env.example .env
```

Configure your credentials in `.env`:

```ini
# Your Qloo Hackathon API Key
QLOO_API_KEY=your_actual_qloo_api_key_here

# Base URL for Qloo Hackathon API
QLOO_BASE_URL=https://hackathon.api.qloo.com

# Mode toggle:
# Set QLOO_MOCK=false to use the LIVE QLOO API
# Set QLOO_MOCK=true to run offline with local catalogs
QLOO_MOCK=false

# LLM Configuration (supports openai, gemini, anthropic, or mock)
LLM_PROVIDER=mock
LLM_MODEL=gpt-4o

# SQLite Database path
DATABASE_URL=sqlite:///./data/common_ground.db
```

> 🔒 **Security Notice:** `.env` is included in `.gitignore` and is never committed to Git. The Qloo API client automatically scrubs all API keys and tokens before logging raw requests to `data/qloo_log.jsonl`.

---

## 🌐 Running the FastAPI REST Server

Start the live server with automatic reloading:

```bash
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qloo Health Status**: [http://localhost:8000/health/qloo](http://localhost:8000/health/qloo)
- **Recent Audit Logs**: [http://localhost:8000/api/logs](http://localhost:8000/api/logs)

---

## 📡 REST API Endpoints & `curl` Examples

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health/qloo` | Tests live Qloo connection and reports latency/status |
| `POST` | `/trips` | Initializes a new trip `{name, destination, days}` and returns invite URL |
| `GET` | `/trips/{id}` | Retrieves trip metadata, status, and joined friends |
| `GET` | `/entities/search?q=&type=` | Qloo entity autocomplete for frontend (artists, films, brands, places) |
| `POST` | `/trips/{id}/profiles` | Adds a friend with cultural favorites & travel constraints |
| `POST` | `/dev/demo-trip` | Pre-populates a test trip with 4 contrasting demo friends |
| `POST` | `/trips/{id}/generate` | Launches background plan generation with grounding & critique |
| `GET` | `/trips/{id}/progress` | Real-time Server-Sent Events (`text/event-stream`) for progress spinners |
| `GET` | `/trips/{id}/plan` | Retrieves the finalized itinerary JSON (`data/demo_plan.json` shape) |
| `POST` | `/trips/{id}/rebalance` | Re-ranks plan with adventurous/cultural sliders (0 new Qloo calls) |
| `GET` | `/trips/{id}/compare` | Side-by-side comparison between Plain LLM and Common Ground plan |

### Sequential `curl` Testing Flow

```bash
# 1. Health check
curl http://localhost:8000/health/qloo | jq .

# 2. Create a trip
curl -X POST http://localhost:8000/trips \
  -H "Content-Type: application/json" \
  -d '{"name": "Lisbon Taste Tour", "destination": "Lisbon", "days": 2}' | jq .

# 3. Autocomplete cultural entities
curl "http://localhost:8000/entities/search?q=Radiohead&type=artist" | jq .

# 4. Quick setup: prefill with 4 demo friends
DEMO_ID=$(curl -X POST http://localhost:8000/dev/demo-trip | jq -r .trip_id)
echo "Trip ID: $DEMO_ID"

# 5. Trigger plan generation in background
curl -X POST http://localhost:8000/trips/$DEMO_ID/generate | jq .

# 6. Stream real-time progress via SSE
curl -N http://localhost:8000/trips/$DEMO_ID/progress

# 7. Fetch finalized plan
curl http://localhost:8000/trips/$DEMO_ID/plan | jq .

# 8. Rebalance plan instantly
curl -X POST http://localhost:8000/trips/$DEMO_ID/rebalance \
  -H "Content-Type: application/json" \
  -d '{"adventurous": 0.85, "cultural": 0.90}' | jq .under_the_hood

# 9. Side-by-side comparison vs plain LLM
curl http://localhost:8000/trips/$DEMO_ID/compare | jq .comparison
```

---

## 🏃‍♂️ Running the 4-Friend Lisbon Live Demo

Run the end-to-end 4-friend test group (Aisha, Rohan, Meera, Kabir) through the live Qloo pipeline:

```bash
.venv/bin/python3 backend/run_group_demo.py
```

### Highlights of the Pipeline:
- **100% Grounded in Qloo**: Every venue is verified against Qloo's Cultural AI catalog (0 hallucinations).
- **Strict Boundary Enforcement**: Filters out venues outside Lisbon's metro area (e.g. across the Tagus River).
- **Hard Constraints**: Respects Meera's alcohol-free preference, Aisha's vegetarian diet, and Kabir's budget.
- **Fairness Guarantee**: Selects dedicated spotlights (★) and taste bridges (🌉) to minimize taste variance.
- **Audited Performance**: Caches requests in SQLite to maintain <200 API calls per plan.

---

## 🔬 Running Automated Tests (Pytest)

Run all 49 unit and integration tests:

```bash
.venv/bin/pytest -v
```

To test only the API endpoints:
```bash
.venv/bin/pytest backend/tests/test_api.py -v
```

---

## 🔍 How It Works Under the Hood

* **Single Source of Truth**: All network interactions with Qloo live in `backend/qloo_client.py`.
* **Single Parsing Function**: `parse_raw_candidate(...)` maps raw Qloo JSON into our internal `Candidate` Pydantic model.
* **SQLite Response Caching**: Responses are automatically saved to `data/common_ground.db` under the `qloo_cache` table. Duplicate calls are returned immediately from cache.
* **Automatic Retries & Backoff**: Handles rate limits (HTTP 429) and server glitches (HTTP 5xx) with 3 retries and exponential backoff.
* **Audit Logging**: Every raw request, response status, and payload is appended to `data/qloo_log.jsonl` for complete transparency.
* **Programmatic Self-Critique & Validation**: `backend/validation.py` inspects the candidate pool before any plan is committed to guarantee compliance.
