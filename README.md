# ScriptSim — AI-Powered Parallel QA Testing

ScriptSim deploys adversarial AI personas to test web products in parallel. Each persona browses the product in a real browser, finds bugs the owner never thought to test for, and produces a ranked severity report with screenshots.

---

## How It Works

Four AI personas simultaneously explore a live web app. Each behaves differently — the kid clicks randomly, the power user tries XSS injection, the parent worries about privacy, the retiree gets confused by icons. After browsing, findings are synthesised into a single ranked bug report.

### Pipeline (5 phases, fully automated)

```
SetupAgent → MapperAgent → ParallelAgent (N personas) → ReportAgents → SynthesisAgent → EvalAgent
```

| Phase | Agent | What it does |
|-------|-------|-------------|
| 1 | SetupAgent | Logs in, stores session cookies for all persona contexts |
| 2 | MapperAgent | Crawls the app, builds feature map (skipped in smoke test mode) |
| 3 | ParallelAgent | Runs persona agents simultaneously in isolated browser contexts |
| 4 | ReportAgent ×N | Converts action logs to structured BugReport objects |
| 5 | SynthesisAgent + EvalAgent | Deduplicates, cross-scores, ranks by severity 1–5 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | Google ADK (`google-adk`) |
| LLM (setup/mapper/personas) | Gemini 2.5 Flash-Lite via Vertex AI |
| LLM (report/synthesis/eval) | Gemini 2.5 Flash via Vertex AI |
| Browser automation | Playwright + Chromium (async, per-task isolated) |
| Infrastructure | Google Cloud Run |
| State + live activity | Google Cloud Firestore |
| Screenshot storage | Google Cloud Storage (`gs://scriptsim-screenshots/`) |
| Frontend | Next.js dashboard |
| API | FastAPI |
| Demo target | Flask app with 5 planted bugs |

---

## Project Structure

```
scriptsim/
├── start.py                # One command starts all 3 services
├── test_agent.py           # Smoke test — run single agent against any URL
├── orchestrator.py         # Full pipeline runner (persona selection, smoke test mode)
├── tools/                  # Person 1 — Playwright browser tools
│   ├── browser.py          # Per-task isolated BrowserContext (parallel-safe)
│   ├── get_page_state.py   # Snapshot: URL, buttons, inputs, links, errors
│   ├── click_element.py    # Click by visible text or aria-label
│   ├── type_text.py        # Fill input by placeholder or aria-label
│   ├── hover_element.py    # Hover to reveal tooltips/dropdowns
│   ├── take_screenshot.py  # Screenshot → GCS (returns gs:// URI)
│   ├── log_bug.py          # Write bug to Firestore
│   ├── login.py            # Login form + store cookies for all persona contexts
│   └── go_back.py          # Browser back navigation
├── agents/                 # Person 2 — ADK agent definitions
│   ├── setup_agent.py
│   ├── mapper_agent.py
│   ├── persona_agent.py    # make_persona_agent(persona) factory
│   ├── report_agent.py     # make_report_agent(persona) factory
│   ├── synthesis_agent.py
│   └── eval_agent.py
├── schemas/
│   └── bug_report.py       # Pydantic BugReport (9 fields, severity 1–5)
├── demo_app/               # Person 3 — Flask shop with 5 planted bugs
│   └── app.py
├── dashboard/              # Person 3 — Next.js UI
│   └── app/page.js         # Persona picker, scan trigger, live activity console
├── api/                    # Person 3 — FastAPI backend
│   └── main.py             # POST /scan, GET /health
├── Dockerfile
├── requirements.txt
├── CLAUDE.md               # Full project spec and rules (read by Claude Code automatically)
└── STATUS.md               # Error log, test results, next steps
```

---

## Quick Start

### Prerequisites
- Python 3.11+ (3.14 supported — see note below)
- Node.js (for Next.js dashboard)
- `gcloud` CLI

### 1. Install dependencies

```bash
pip install -r requirements.txt
pip install flask werkzeug          # for demo app
python -m playwright install chromium
```

> **Python 3.14 note:** `requirements.txt` pins `playwright==1.44.0` for Docker. On Python 3.14 locally, run `pip install "playwright>=1.50.0"` to override. Always use `python -m playwright install chromium` (not the shell command).

### 2. Create `.env` file (get from Shruti — never commit this)

```
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=agentic-fp-scriptsim
GOOGLE_CLOUD_LOCATION=us-central1
```

### 3. Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project agentic-fp-scriptsim
gcloud auth application-default set-quota-project agentic-fp-scriptsim
```

> **GCP access:** Your Gmail must be added to the project IAM by Shruti. Required roles:
> - `Vertex AI User` — to call Gemini API (every agent needs this)
> - `Storage Object Creator` — to upload screenshots (`take_screenshot.py`)
> - `Cloud Datastore User` — to write bug reports (`log_bug.py`)
>
> Person 3 does NOT need GCP access to run the Flask demo app.

### 4. Start everything

```bash
python start.py
```

Opens:
- Demo App → http://localhost:5000
- Dashboard → http://localhost:3000
- API → http://localhost:8000

### 5. Run a scan

1. Open http://localhost:3000
2. Select **Demo App** (pre-filled, port 5000)
3. Pick personas (or keep all 4)
4. Check **Smoke Test Mode** for a fast 3-minute demo
5. Click **Run Parallel Scan**

---

## Demo App — 5 Planted Bugs

| # | Bug | How to trigger |
|---|-----|---------------|
| 1 | XSS in search | Search for `<script>alert(1)</script>` |
| 2 | Silent cart failure | Add "Super Gadget" — success alert but item never appears in cart |
| 3 | Crash at 10+ items | Add "Awesome Widget" 10 times — server 500 error |
| 4 | Confusing error message | Trigger the 500 — says "chickens have come home to roost" |
| 5 | Frozen checkout | Go to cart — Checkout button is permanently disabled |

Test credentials: `test@scriptsim.com` / `TestPass123!`

---

## Smoke Tests (verify agents work)

```bash
python test_agent.py mapper https://example.com
python test_agent.py persona kid http://localhost:5000
```

| Test | Result | Date |
|------|--------|------|
| MapperAgent vs example.com | PASS | 2026-04-25 |
| Kid persona vs demo app (localhost:5000) | PASS — found Bug 2, screenshots to GCS | 2026-04-26 |
| Full 4-persona scan vs demo app (scan 1) | PASS — all 11 agents, 3 bugs, $0.023, 631s | 2026-04-27 |
| Full 4-persona scan vs demo app (scan 2) | PASS — fence fix confirmed, "2 bugs found" correct, $0.021 | 2026-04-27 |

Note: persona smoke test requires demo app running (`python start.py` or `python demo_app/app.py`). The test pre-logs in automatically before the persona starts.

---

## GCP Infrastructure

| Resource | Config | Status |
|----------|--------|--------|
| Project | `agentic-fp-scriptsim` | Active |
| GCS Bucket | `scriptsim-screenshots` — us-central1 | Created + Tested |
| Firestore | `(default)` — Native mode, us-central1 | Created + Tested |
| Cloud Run | `scriptsim-worker` — us-central1 | Pending |

---

## Key Design Decisions

**Per-task browser isolation** — Each asyncio Task (persona) gets its own `BrowserContext` keyed by `asyncio.current_task()` ID. Personas cannot interfere with each other. `login.py` stores cookies globally so every new context starts logged in automatically.

**Async Playwright** — ADK's runner is async. Sync Playwright raises an error inside asyncio. All tools are `async def`, all page calls are `await`-ed.

**`gs://` URIs for screenshots** — GCS Public Access Prevention blocks public URLs. Tools return `gs://scriptsim-screenshots/...` URIs; Cloud Run reads via IAM.

**`go_back()` tool** — Agents cannot click browser chrome. `go_back()` wraps `page.go_back()`.

**ADK constraint: tools XOR output_schema** — PersonaAgents have 7 tools, no schema. ReportAgents have `output_schema=BugReport`, no tools. Never combine both on one agent.

**Smoke test mode** — `is_smoke_test=True` runs 1 persona, 5 actions, skips mapper. Enables fast 3-minute demos without burning Gemini quota.

**Sequential report agents** — ReportAgents run sequentially (not in parallel) to avoid 429 RESOURCE_EXHAUSTED rate limit errors on Vertex AI when all 4 agents call the API simultaneously.

**Neutral orchestrator trigger message** — ADK's SequentialAgent passes the same user message to every sub-agent. The message must be `"Begin."` — a descriptive message like "Run QA scan" causes SetupAgent (which only has a login tool) to refuse with "I can't run a full QA scan".

---

## Team

| Person | Owns | Status |
|--------|------|--------|
| Person 1 (Shruti) | `tools/`, `Dockerfile`, Cloud Run | Done — browser isolation + agent reliability fixes shipped |
| Person 2 | `agents/`, `schemas/`, `orchestrator.py` | Done |
| Person 3 | `demo_app/`, `dashboard/`, `api/`, `start.py` | Done |

## Known Limitations

- **Action limit is a soft limit** — `max_persona_actions` is a hint to the LLM, not a hard stop. Scans may run longer than expected but always complete.
- **Mapper disabled** — MapperAgent loops on non-navigating buttons (`go_back` from root → `about:blank`). Skipped until fixed; personas find bugs without it.
- **Cloud Run not yet deployed** — All services run locally. Public URL pending.
