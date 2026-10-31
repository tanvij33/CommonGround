# Common Ground 🌍✨
> **A taste-fair group trip planner powered by Qloo's Cultural AI.**

Common Ground helps groups of friends plan unforgettable trips by analyzing everyone's unique cultural tastes (music, dining, fashion, art, architecture) and finding shared affinities, zero-hallucination venues, and balanced compromises for accommodations, dining, and daily activities.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Next.js 14 Frontend                             │
│  • Landing & Taste Graph Showcase    • Cultural Onboarding & QR Invite │
│  • Real-Time SSE Generation Stream   • Interactive Itinerary & Sliders │
│  • Common Ground vs Plain LLM        • Shareable Social Trip Cards     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / Server-Sent Events (SSE)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI REST Engine                            │
│  • Trip & Traveler Session State     • Taste-Fairness Optimizer        │
│  • Autocomplete & Search Proxy       • Grounding & Guardrail Validator │
└───────────────────┬───────────────────────────────────┬────────────────┘
                    │                                   │
                    ▼                                   ▼
┌───────────────────────────────────────┐ ┌──────────────────────────────┐
│          Qloo Cultural AI             │ │    SQLite & Cache Layer      │
│ • Entity Resolution & Insights Engine │ │ • Query Response Cache       │
│ • Offline Catalogs & Mock Fallbacks   │ │ • JSONL Audit Logs           │
└───────────────────────────────────────┘ └──────────────────────────────┘
```

---

## 📁 Repository Structure

```text
CommonGround/
├── backend/                        # Python FastAPI & Qloo intelligence backend
│   ├── main.py                     # FastAPI REST endpoints with SSE streaming & CORS
│   ├── qloo_client.py              # Unified Qloo API client (caching, retries, audit logs)
│   ├── pipeline.py                 # Modular trip generator for any group, city, or duration
│   ├── scoring.py                  # Taste-fairness algorithms (group score, taste debt, bridges)
│   ├── mock_data.py                # Realistic offline cultural catalogs & synthesis fallbacks
│   ├── models.py                   # Pydantic schemas (Trip, Profile, Candidate, Plan, PlanStop)
│   ├── db.py                       # SQLite database & session management
│   ├── validation.py               # Grounding validation (rejects hallucinations, enforces constraints)
│   ├── agent.py                    # Autonomous planner with streaming progress & self-critique
│   ├── llm.py                      # Swappable LLM wrapper (OpenAI, Gemini, mock)
│   ├── run_group_demo.py           # 4-friend live Lisbon demo script with real Qloo data
│   ├── run_cli.py                  # CLI runner for agent pipeline and queries
│   ├── tests/                      # Unit & integration tests
│   │   ├── test_api.py             # Complete REST API lifecycle & endpoint tests
│   │   ├── test_scoring.py         # Fairness scoring & mathematical spread tests
│   │   ├── test_agent_and_validation.py # Grounding & constraint validation tests
│   │   └── test_qloo_integration.py # Qloo client & cache tests
│   └── requirements.txt            # Python package dependencies
├── frontend/                       # Modern Next.js 14 web application
│   ├── app/                        # App Router pages and layouts
│   │   ├── page.tsx                # High-conversion Landing page & demo showcase
│   │   ├── create/page.tsx         # Trip creation wizard
│   │   ├── join/[tripId]/page.tsx  # Friend onboarding flow with QR code & taste inputs
│   │   ├── trip/[tripId]/          # Trip management & status
│   │   │   ├── generating/page.tsx # Real-time SSE progress tracker
│   │   │   ├── plan/page.tsx       # Interactive itinerary, fairness breakdown & sliders
│   │   │   ├── compare/page.tsx    # Common Ground vs. Vanilla LLM comparison
│   │   │   └── card/page.tsx       # Exportable visual trip card
│   │   ├── layout.tsx              # Root HTML shell & navigation
│   │   └── globals.css             # Tailwind CSS & design tokens
│   ├── components/                 # Reusable UI component library
│   │   ├── landing/                # Hero, TasteGraphStrip, FairnessShowcase, Modals
│   │   └── ui/                     # Cards, Chips, ScoreBars, Buttons, Modals, Steppers
│   ├── lib/                        # Client libraries & utilities
│   │   ├── api.ts                  # Typed backend API client & mock fallbacks
│   │   ├── autocompleteData.ts     # Pre-curated cultural entities catalog
│   │   └── utils.ts                # Tailwind class mergers and formatting helpers
│   ├── package.json                # Frontend dependencies and scripts
│   ├── tailwind.config.ts          # Tailwind styling configuration
│   └── tsconfig.json               # TypeScript configuration
├── data/                           # Local SQLite database, audit logs & demo plan
│   ├── common_ground.db            # SQLite database (trips, profiles, plans, qloo_cache)
│   ├── demo_plan.json              # Reference plan JSON output
│   └── qloo_log.jsonl              # Raw Qloo request/response audit log
├── pytest.ini                      # Pytest configuration
├── .env.example                    # Template for environment variables
└── README.md                       # This guide
```

---

## 🚀 Quickstart Guide: Running the Full Stack

To run Common Ground properly, launch both the **FastAPI backend** (Terminal 1) and the **Next.js frontend** (Terminal 2).

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm 9+**

---

### Step 1: Configure Environment Variables

From the project root (`CommonGround/`), copy the environment template:

```bash
cp .env.example .env
```

Open `.env` and configure your credentials:

```ini
# Qloo Hackathon API Key
QLOO_API_KEY=your_actual_qloo_api_key_here

# Base URL for Qloo Hackathon API
QLOO_BASE_URL=https://hackathon.api.qloo.com

# Mode toggle:
# Set QLOO_MOCK=false to query live Qloo cultural endpoints
# Set QLOO_MOCK=true to run completely offline with mock catalogs
QLOO_MOCK=false

# LLM Configuration (supports openai, gemini, anthropic, or mock)
LLM_PROVIDER=mock
LLM_MODEL=gpt-4o

# SQLite Database path
DATABASE_URL=sqlite:///./data/common_ground.db
```

---

### Step 2: Start the Backend Server (Terminal 1)

From the project root:

```bash
# 1. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Start the FastAPI server with reload
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend is now running at:
- **REST API Base**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qloo Health Check**: [http://localhost:8000/health/qloo](http://localhost:8000/health/qloo)

---

### Step 3: Start the Next.js Frontend (Terminal 2)

In a new terminal window, navigate to the `frontend/` directory and run:

```bash
cd frontend
npm run dev
```

> **Note:** If running for the first time, make sure dependencies are installed:
> ```bash
> cd frontend
> npm install
> npm run dev
> ```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🌐 Application Experience & Walkthrough

| Screen | URL | Highlights |
| :--- | :--- | :--- |
| **Landing Page** | `http://localhost:3000/` | Interactive Taste Graph preview, fairness showcase, product screenshots, and one-click demo plan launcher. |
| **Create Trip** | `http://localhost:3000/create` | Set trip name, destination city (e.g. Lisbon, Tokyo, Berlin), and duration in days. Generates an instant share link and QR code. |
| **Join & Cultural Onboarding** | `http://localhost:3000/join/{tripId}` | Friends join via mobile/desktop. Onboards multi-domain cultural favorites (Music, Film, Fashion, Books, Dining) with live autocomplete, plus travel guardrails (budget, dietary, alcohol-free, pace). |
| **Plan Generation (SSE)** | `http://localhost:3000/trip/{tripId}/generating` | Displays real-time progress steps streamed via Server-Sent Events from the background planning agent. |
| **Taste-Fair Itinerary** | `http://localhost:3000/trip/{tripId}/plan` | Daily schedule featuring dedicated Friend Spotlights (★), cross-taste Bridges (🌉), guardrail status badges, and interactive Adventurous / Cultural rebalancing sliders. |
| **Common Ground vs. LLM** | `http://localhost:3000/trip/{tripId}/compare` | Head-to-head comparison demonstrating how standard LLMs produce 1-person-dominated plans vs. Common Ground's taste fairness. |
| **Shareable Trip Card** | `http://localhost:3000/trip/{tripId}/card` | Visual summary card ready for social sharing or group chats. |

---

## 📡 REST API Endpoints & `curl` Flow

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health/qloo` | Tests live Qloo connection and reports latency |
| `POST` | `/trips` | Creates a new trip `{name, destination, days}` |
| `GET` | `/trips/{id}` | Retrieves trip metadata, status, and joined travelers |
| `GET` | `/entities/search?q=&type=` | Qloo entity autocomplete for artists, films, brands, and venues |
| `POST` | `/trips/{id}/profiles` | Adds a traveler profile with cultural favorites & constraints |
| `POST` | `/dev/demo-trip` | Pre-populates a test trip with 4 contrasting demo friends |
| `POST` | `/trips/{id}/generate` | Launches background plan generation with grounding & critique |
| `GET` | `/trips/{id}/progress` | Real-time Server-Sent Events (`text/event-stream`) |
| `GET` | `/trips/{id}/plan` | Retrieves the finalized itinerary JSON |
| `POST` | `/trips/{id}/rebalance` | Re-ranks plan with adventurous/cultural sliders (0 extra Qloo calls) |
| `GET` | `/trips/{id}/compare` | Side-by-side comparison between Plain LLM and Common Ground plan |

### Sequential `curl` Testing Flow

```bash
# 1. Check Qloo health status
curl http://localhost:8000/health/qloo | jq .

# 2. Quick setup: create a 4-friend Lisbon demo trip
DEMO_ID=$(curl -X POST http://localhost:8000/dev/demo-trip | jq -r .trip_id)
echo "Demo Trip ID: $DEMO_ID"

# 3. Trigger plan generation in background
curl -X POST http://localhost:8000/trips/$DEMO_ID/generate | jq .

# 4. Stream real-time progress via SSE
curl -N http://localhost:8000/trips/$DEMO_ID/progress

# 5. Fetch finalized plan
curl http://localhost:8000/trips/$DEMO_ID/plan | jq .

# 6. Rebalance plan dynamically
curl -X POST http://localhost:8000/trips/$DEMO_ID/rebalance \
  -H "Content-Type: application/json" \
  -d '{"adventurous": 0.85, "cultural": 0.90}' | jq .under_the_hood

# 7. Compare vs Plain LLM
curl http://localhost:8000/trips/$DEMO_ID/compare | jq .comparison
```

---

## 🏃‍♂️ Running the 4-Friend Live Lisbon Demo CLI

To run the end-to-end 4-friend test group (Aisha, Rohan, Meera, Kabir) directly in your terminal:

```bash
.venv/bin/python3 backend/run_group_demo.py
```

### What This Demonstrates:
1. **Diverse Profiles**:
   - **Aisha**: Electronic & ambient music (Burial, Radiohead), contemporary art, vegetarian.
   - **Rohan**: Specialty third-wave coffee, architectural walks, high-intensity pace.
   - **Meera**: Indie bookstores, acoustic jazz, strictly alcohol-free.
   - **Kabir**: Vibrant street food, local markets, strict budget limit.
2. **Zero Hallucinations**: Every venue is grounded in Qloo's Cultural AI catalog.
3. **Hard Constraint Enforcement**: Respects dietary restrictions, budget bounds, and sobriety.
4. **Taste Fairness Guarantee**: Balances group happiness spread and prevents any single person from dominating.

---

## 🔬 Running Automated Tests

Run backend unit and integration test suites:

```bash
# Run all tests
.venv/bin/pytest -v

# Run API lifecycle tests specifically
.venv/bin/pytest backend/tests/test_api.py -v

# Run scoring and fairness tests
.venv/bin/pytest backend/tests/test_scoring.py -v
```

To test the frontend build:
```bash
cd frontend
npm run build
```

---

## 🧠 How It Works Under the Hood

### 1. Unified Cultural AI Client (`backend/qloo_client.py`)
- Communicates directly with Qloo Hackathon endpoints (`/v2/search`, `/v2/insights`).
- Maps raw entities to normalized candidate models with cultural tags and affinity scores.
- Implements transparent SQLite caching (`data/common_ground.db`) to ensure ultra-fast response times and prevent duplicate API usage.
- Automatically logs all interactions to `data/qloo_log.jsonl` with token and secret scrubbing.

### 2. Taste-Fairness Optimization (`backend/scoring.py`)
- Calculates personalized affinity vectors across travelers for each candidate venue.
- Tracks **Taste Debt**: If Friend A compromises during lunch, the algorithm prioritizes their cultural taste for dinner.
- Identifies **Taste Bridges** (venues that naturally satisfy overlapping interests between contrasting friends) and **Spotlights** (venues curated specifically for one traveler).

### 3. Programmatic Self-Critique & Grounding (`backend/validation.py`)
- Before saving an itinerary, the validation agent verifies:
  - 100% of stops correspond to verified entities.
  - Geographical coherence (e.g. venues are within the target metropolitan bounds).
  - Strict compliance with traveler guardrails (dietary, alcohol, mobility, budget).
