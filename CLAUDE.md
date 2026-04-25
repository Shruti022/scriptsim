# ScriptSim — AI QA Testing Agent

## What this project is
ScriptSim deploys adversarial AI personas (confused 8yo kid, 22yo power user,
45yo anxious parent, 67yo retiree, 82yo grandma) to test web products in parallel.
Each persona explores the product in a real browser, finds bugs the owner never
thought to test for, and produces a ranked severity report with screenshots.

## Tech stack (locked — do not change)
- **Agent framework**: Google ADK (google-cloud-adk)
- **LLM**: Gemini 2.5 Flash-Lite for PersonaAgent/MapperAgent,
           Gemini 2.5 Flash for SynthesisAgent/EvalAgent
- **Browser**: Playwright + Chromium inside Docker
- **Infra**: Cloud Run (GCP), Firestore (state), Cloud Storage (screenshots)
- **Frontend**: Next.js on Firebase Hosting
- **API**: FastAPI

## Architecture (5 phases, sequential)
1. SetupAgent — logs in, saves cookies to Firestore
2. MapperAgent — crawls product, builds feature map
3. ParallelAgent — runs 4 PersonaAgents simultaneously, zero shared state
4. ReportAgent × 4 — converts action logs to BugReport Pydantic schema
5. SynthesisAgent + EvalAgent — dedup, cross-persona scoring, severity 1-5

## Critical ADK constraint
output_schema and tools are MUTUALLY EXCLUSIVE in Gemini.
- PersonaAgent: has tools, NO output_schema
- ReportAgent: has output_schema=BugReport, NO tools
Never put both on the same agent.

## Agents communicate via output_key
Agents pass data through session state using output_key, NOT return values.
PersonaAgent writes to state["action_log_kid"]
ReportAgent reads via {action_log_kid} in its instruction template.

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
- business_doc/

## Folder structure
scriptsim/
├── CLAUDE.md              ← you are here
├── Dockerfile
├── requirements.txt
├── tools/                 ← Person 1 owns this
│   ├── __init__.py
│   ├── browser.py         ← Playwright browser singleton
│   ├── get_page_state.py
│   ├── click_element.py
│   ├── type_text.py
│   ├── hover_element.py
│   ├── take_screenshot.py
│   ├── log_bug.py
│   └── login.py
├── agents/                ← Person 2 owns this
│   ├── setup_agent.py
│   ├── mapper_agent.py
│   ├── persona_agent.py
│   ├── report_agent.py
│   ├── synthesis_agent.py
│   └── eval_agent.py
├── schemas/               ← Person 2 owns this
│   └── bug_report.py
├── orchestrator.py        ← Person 2 owns this
├── demo_app/              ← Person 3 owns this
├── dashboard/             ← Person 3 owns this
└── api/                   ← Person 3 owns this

## Playwright rules (always follow these)
- Use sync Playwright (playwright.sync_api) — ADK tools must be sync def, not async def
- Always launch with: args=["--no-sandbox", "--disable-dev-shm-usage"]
- Always wait_for_load_state("networkidle") after navigation
- Always wrap tool calls in try/except — never let a tool crash the agent
- get_page_state() must return valid JSON string, never raise exceptions
- Selectors: prefer text-based ("button:has-text('Like')") over CSS selectors
- Screenshots: save to /tmp/ first, then upload to GCS, return URL

## GCP config
- Project: agentic-fp-scriptsim
- Region: us-central1
- Firestore: (default) database, Native mode, collection scans/{scan_id}/bugs/
- GCS bucket: scriptsim-screenshots (us-central1, no public access — use gs:// URIs)
- Cloud Run service: scriptsim-worker (not yet deployed)

## Demo app URL (Person 3 deploys this)
- URL: TBD (Railway deployment, update this when available)
- Test credentials: email=test@scriptsim.com, password=TestPass123!
- 5 planted bugs: XSS in search, silent cart, crash at 10+ items,
                  idiom error message, frozen checkout button

## How to run tools locally for testing
cd tools/
python get_page_state.py  # should print JSON of current page
python click_element.py "Like"  # should click and confirm

## What is done
- tools/ — all 9 Playwright tools, tested against live GCP (Person 1)
- agents/ + schemas/ + orchestrator.py — full ADK pipeline (Person 2)
- GCS bucket scriptsim-screenshots — created, tested
- Firestore (default) database — created, tested
- GitHub: https://github.com/Shruti022/scriptsim

## What is pending
- demo_app/ + dashboard/ + api/ — Person 3
- Cloud Run deployment — Person 1 (session: person1-cloudrun)
- Update demo app URL below once Person 3 deploys

## Session naming convention for Claude Code
claude --resume "person1-playwright-tools"
claude --resume "person1-docker"
claude --resume "person1-cloudrun"
