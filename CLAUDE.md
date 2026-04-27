# ScriptSim — AI QA Testing Agent

## What this project is
ScriptSim deploys adversarial AI personas (confused 8yo kid, 22yo power user,
45yo anxious parent, 67yo retiree) to test web products in parallel.
Each persona explores the product in a real browser, finds bugs the owner never
thought to test for, and produces a ranked severity report with screenshots.

## Tech stack (locked — do not change)
- **Agent framework**: Google ADK (google-cloud-adk)
- **LLM**: Gemini 2.5 Flash-Lite for PersonaAgent/MapperAgent/SetupAgent,
           Gemini 2.5 Flash for ReportAgent/SynthesisAgent/EvalAgent
- **Browser**: Playwright + Chromium (async)
- **Infra**: Cloud Run (GCP), Firestore (state + live activity), Cloud Storage (screenshots)
- **Frontend**: Next.js dashboard (localhost:3000)
- **API**: FastAPI (localhost:8000)
- **Demo app**: Flask (localhost:5000)

## Architecture (5 phases, sequential)
1. SetupAgent — logs in, cookies stored globally for all persona contexts
2. MapperAgent — crawls product, builds feature map (skipped in smoke test mode)
3. ParallelAgent — runs persona agents simultaneously, each in isolated browser context
4. ReportAgent × N — converts action logs to BugReport Pydantic schema
5. SynthesisAgent + EvalAgent — dedup, cross-persona scoring, severity 1-5

## Run everything locally with one command
```
python start.py
```
Opens: Demo App (port 5000) + API (port 8000) + Dashboard (port 3000)
Then visit http://localhost:3000 → select Demo App → Run Parallel Scan

## Scan modes
- **Smoke Test Mode** (checkbox in dashboard): 1 persona, 5 actions, skip mapper — fast demo (~3 min)
- **Full Scan**: all selected personas, 15 actions each, with mapper — thorough (~15 min)

## Critical ADK constraint
output_schema and tools are MUTUALLY EXCLUSIVE in Gemini.
- PersonaAgent: has tools, NO output_schema
- ReportAgent: has output_schema=BugReport, NO tools
Never put both on the same agent.

## Agents communicate via output_key
Agents pass data through session state using output_key, NOT return values.
PersonaAgent writes to state["action_log_kid"]
ReportAgent reads via {action_log_kid} in its instruction template.

## Browser isolation (critical — how parallel personas work)
Each asyncio Task (persona) gets its own isolated BrowserContext via `_contexts` dict
keyed by `asyncio.current_task()` ID. login.py stores cookies globally in `_default_cookies`
after SetupAgent logs in — new persona contexts inject these cookies automatically so
every persona starts already logged in at the target URL.
Never use a single global `_page` — that was the old broken design.

## Person 1 owns (browser layer)
- tools/ directory — all Playwright tool functions
- Dockerfile — using official Playwright image
- Cloud Run deployment
- DO NOT touch agents/ or schemas/ — those belong to Person 2

## Person 2 owns (agent layer)
- agents/ directory — all ADK agent definitions
- schemas/ — Pydantic models
- orchestrator.py

## Person 3 owns (product + frontend)
- demo_app/ — Flask app with 5 planted bugs
- dashboard/ — Next.js frontend
- api/ — FastAPI scan trigger endpoints

## Folder structure
scriptsim/
├── CLAUDE.md              ← you are here
├── Dockerfile
├── requirements.txt
├── start.py               ← starts all 3 services with one command
├── test_agent.py          ← smoke test: run single agent against any URL
├── orchestrator.py        ← Person 2 owns this
├── tools/                 ← Person 1 owns this
│   ├── __init__.py
│   ├── browser.py         ← Per-task async browser contexts (isolated per persona)
│   ├── get_page_state.py
│   ├── click_element.py
│   ├── type_text.py
│   ├── hover_element.py
│   ├── take_screenshot.py ← uploads to gs://scriptsim-screenshots/
│   ├── log_bug.py         ← writes to Firestore scans/{scan_id}/bugs/
│   ├── login.py           ← fills login form + stores cookies globally
│   └── go_back.py         ← browser back navigation
├── agents/                ← Person 2 owns this
│   ├── setup_agent.py     ← model: gemini-2.5-flash-lite
│   ├── mapper_agent.py    ← model: gemini-2.5-flash-lite
│   ├── persona_agent.py   ← model: gemini-2.5-flash-lite, uses {max_persona_actions}
│   ├── report_agent.py    ← model: gemini-2.5-flash, output_schema=BugReport
│   ├── synthesis_agent.py ← model: gemini-2.5-flash
│   └── eval_agent.py      ← model: gemini-2.5-flash
├── schemas/               ← Person 2 owns this
│   └── bug_report.py
├── demo_app/              ← Person 3 owns this
│   ├── app.py             ← Flask shop with 5 planted bugs
│   └── requirements.txt   ← Flask==3.0.3, Werkzeug==3.0.3
├── dashboard/             ← Person 3 owns this
│   ├── app/page.js        ← main UI: URL input, persona picker, smoke test toggle
│   ├── app/api/activity/  ← live activity feed from Firestore
│   ├── app/api/bugs/      ← bug report display
│   └── package.json
└── api/                   ← Person 3 owns this
    └── main.py            ← FastAPI POST /scan, GET /health

## Playwright rules (always follow these)
- Use ASYNC Playwright (playwright.async_api) — ADK runner is async, sync Playwright crashes
- All tool functions must be `async def`, all page calls must be `await`-ed
- Always launch with: args=["--no-sandbox", "--disable-dev-shm-usage"]
- Always wait_for_load_state("networkidle") after navigation
- Always wrap tool calls in try/except — never let a tool crash the agent
- get_page_state() must return valid JSON string, never raise exceptions
- Selectors: prefer text-based ("button:has-text('Like')") over CSS selectors
- Screenshots: save to /tmp/ first, then upload to GCS, return gs:// URI (NOT public URL)
- Use go_back() tool for browser back navigation — never try to click a "Back" button
- NEVER use a single global _page — use get_page() which returns per-task context

## GCP config
- Project: agentic-fp-scriptsim
- Region: us-central1
- Firestore: (default) database, Native mode
  - scans/{scan_id}/bugs/ — bug reports
  - scans/{scan_id}/activity/ — live agent activity for dashboard
- GCS bucket: scriptsim-screenshots (us-central1, no public access — use gs:// URIs)
- Cloud Run service: scriptsim-worker (not yet deployed)

## Demo app (runs locally on port 5000)
- Test credentials: email=test@scriptsim.com, password=TestPass123!
- 5 planted bugs:
  1. XSS in search — query rendered with |safe filter
  2. Silent cart failure — Super Gadget returns success but isn't added
  3. Crash at 10+ items — ValueError → 500 error
  4. Confusing error message — "chickens have come home to roost"
  5. Frozen checkout button — permanently disabled

## Local setup (required before running anything)
1. Install Python deps: `pip install -r requirements.txt`
2. Install Flask for demo app: `pip install flask werkzeug`
3. Install Chromium: `python -m playwright install chromium`
4. Install Node.js (for dashboard): https://nodejs.org
5. Create `.env` in project root (get from Shruti — never commit):
   ```
   GOOGLE_GENAI_USE_VERTEXAI=1
   GOOGLE_CLOUD_PROJECT=agentic-fp-scriptsim
   GOOGLE_CLOUD_LOCATION=us-central1
   ```
6. Authenticate with GCP: `gcloud auth application-default login`

## GCP access (who needs it and how to get it)
All teammates use the shared GCP project: `agentic-fp-scriptsim`

**Who needs GCP access:**
- Person 1 (Shruti) — already owner
- Person 2 — only if running scans locally
- Person 3 — NOT needed for Flask app; only needed for end-to-end scan testing

**How Shruti adds a teammate (GCP Console → IAM & Admin → IAM → Grant Access):**
1. New principals: enter their Gmail
2. Add role: `Vertex AI User` — agents call Gemini API; without this, permission denied
3. Add role: `Storage Object Creator` — take_screenshot.py uploads to GCS
4. Add role: `Cloud Datastore User` — log_bug.py writes to Firestore
5. Save — no IAM conditions needed

**Teammate then runs:** `gcloud auth application-default login` with that Gmail

## Smoke tests (verify tools + agents work)
```
python test_agent.py mapper https://example.com
python test_agent.py persona kid https://example.com
```
Both confirmed PASSING as of 2026-04-25.

## What is done
- tools/ — all 10 async Playwright tools, per-task browser isolation implemented
- login.py — stores cookies globally so all parallel persona contexts start logged in
- agents/ + schemas/ + orchestrator.py — full ADK pipeline with smoke test + persona selection
- GCS bucket + Firestore — created and tested
- demo_app/ — Flask shop with 5 planted bugs (Person 3)
- dashboard/ — Next.js UI with live activity console (Person 3)
- api/ — FastAPI POST /scan endpoint with background task runner (Person 3)
- start.py — one-command launcher for all 3 services
- First scan run against demo app — SetupAgent + kid persona confirmed working

## What is pending
- Full 4-persona parallel scan end-to-end test (browser isolation fix just deployed)
- Cloud Run deployment — Person 1 (session: person1-cloudrun)
- Deploy demo app to Railway/Cloud Run for public URL

## Session naming convention for Claude Code
claude --resume "person1-playwright-tools"
claude --resume "person1-cloudrun"
