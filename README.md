# ScriptSim — AI QA Testing Agent

ScriptSim deploys adversarial AI personas to test web products in parallel. Each persona browses the product in a real browser, finds bugs the owner never thought to test for, and produces a ranked severity report with screenshots.

---

## How It Works

Five AI personas (confused 8-year-old, 22-year-old power user, anxious parent, retiree, grandma) simultaneously explore a live web app. Each persona behaves differently — the kid clicks randomly, the power user tries XSS injection, the parent worries about privacy. After browsing, their findings are synthesized into a single ranked bug report.

### Pipeline (5 phases, fully automated)

```
SetupAgent → MapperAgent → ParallelAgent (4 personas) → ReportAgents → SynthesisAgent → EvalAgent
```

| Phase | Agent | What it does |
|-------|-------|-------------|
| 1 | SetupAgent | Logs in, saves session cookies |
| 2 | MapperAgent | Crawls the app, builds feature map |
| 3 | ParallelAgent | Runs 4 PersonaAgents simultaneously |
| 4 | ReportAgent ×4 | Converts action logs to structured bug reports |
| 5 | SynthesisAgent + EvalAgent | Deduplicates, cross-scores, ranks by severity |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | Google ADK (`google-adk`) |
| LLM (personas/mapper) | Gemini 2.5 Flash-Lite |
| LLM (synthesis/eval) | Gemini 2.5 Flash |
| Browser automation | Playwright + Chromium |
| Infrastructure | Google Cloud Run |
| State storage | Google Cloud Firestore |
| Screenshot storage | Google Cloud Storage |
| Frontend | Next.js on Firebase Hosting |
| API | FastAPI |

---

## Project Structure

```
scriptsim/
├── test_agent.py           # Smoke test — run single agent against any URL
├── tools/                  # Person 1 — Playwright browser tools
│   ├── browser.py          # Async browser singleton (start, stop, inject cookies)
│   ├── get_page_state.py   # Snapshot of current page (buttons, inputs, links)
│   ├── click_element.py    # Click by visible text or aria-label
│   ├── type_text.py        # Fill input by placeholder or aria-label
│   ├── hover_element.py    # Hover to reveal tooltips/dropdowns
│   ├── take_screenshot.py  # Screenshot → GCS bucket (returns gs:// URI)
│   ├── log_bug.py          # Write bug to Firestore
│   ├── login.py            # Fill login form, return session cookies
│   └── go_back.py          # Browser back navigation (page.go_back())
│
├── agents/                 # Person 2 — ADK agent definitions
│   ├── setup_agent.py      # Logs in to target app
│   ├── mapper_agent.py     # Crawls app, builds feature map
│   ├── persona_agent.py    # make_persona_agent(persona) factory
│   ├── report_agent.py     # make_report_agent(persona) factory
│   ├── synthesis_agent.py  # Dedup + cross-persona severity scoring
│   └── eval_agent.py       # Final ranking and report generation
│
├── schemas/                # Person 2 — Pydantic models
│   └── bug_report.py       # BugReport schema (9 fields, severity 1–5)
│
├── orchestrator.py         # Person 2 — Full pipeline runner
│
├── demo_app/               # Person 3 — Flask app with 5 planted bugs
├── dashboard/              # Person 3 — Next.js results dashboard
├── api/                    # Person 3 — FastAPI scan trigger endpoints
│
├── Dockerfile              # Playwright + Python image for Cloud Run
├── requirements.txt        # Python dependencies
├── CLAUDE.md               # Project spec and rules
└── STATUS.md               # Dev log, errors, and current status
```

---

## GCP Infrastructure

| Resource | Config | Status |
|----------|--------|--------|
| Project | `agentic-fp-scriptsim` | Active |
| GCS Bucket | `scriptsim-screenshots` — us-central1 | Created + Tested |
| Firestore | `(default)` — Native mode, us-central1 | Created + Tested |
| Cloud Run | `scriptsim-worker` — us-central1 | Pending |

---

## Local Setup

### Prerequisites
- Python 3.11+ (3.14 supported with playwright upgrade)
- `gcloud` CLI installed and authenticated

### Install

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

> **Note:** `requirements.txt` pins `playwright==1.44.0` for Docker compatibility. If you're on Python 3.14 locally and get a `greenlet` build error, run `pip install "playwright>=1.50.0"` to override it. Always use `python -m playwright install chromium` (not just `playwright install chromium`) to install the browser for the correct version.

## Quick Start (Local Run)

The easiest way to run ScriptSim locally is using the automated startup script:

```powershell
python start.py
```

This single command starts the **Demo App**, **FastAPI Backend**, and **Next.js Dashboard** simultaneously.

### Access the Dashboard
Once the script is running, visit: **[http://localhost:3000](http://localhost:3000)**

- Select **"Demo App"** for a local test.
- Pick your **AI Personas**.
- Enable **"Smoke Test Mode"** for a fast (3-minute) demo.
- Click **"Run Parallel Scan"** and watch the **Live Activity Console**!

---

### Create `.env` file

```
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=agentic-fp-scriptsim
GOOGLE_CLOUD_LOCATION=us-central1
```

### Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project agentic-fp-scriptsim
gcloud auth application-default set-quota-project agentic-fp-scriptsim
```

> **GCP access:** All teammates use the shared project `agentic-fp-scriptsim`. Your Gmail must be added to the project IAM by Shruti before this works. Three roles are required:
> - `Vertex AI User` — to call the Gemini API (every agent call needs this)
> - `Storage Object Creator` — to upload screenshots to GCS (`take_screenshot.py`)
> - `Cloud Datastore User` — to write bug reports to Firestore (`log_bug.py`)

### Verify setup with smoke tests

```bash
python test_agent.py mapper https://example.com       # MapperAgent — should print feature_map JSON
python test_agent.py persona kid https://example.com  # kid PersonaAgent — should print action_log_kid
```

Both tests confirmed working as of 2026-04-25.

### Run a full scan (once demo app is deployed)

```bash
python orchestrator.py https://<demo-app-url>
```

---

## Demo App

- **URL:** Local (run `python demo_app/app.py` on port 5000) or TBD (deploying to Railway)
- **Test credentials:** `test@scriptsim.com` / `TestPass123!`
- **Planted bugs:** XSS in search, silent cart failure, crash at 10+ items, confusing error message, frozen checkout button

---

## Key Design Decisions

**Async Playwright (not sync)** — ADK's runner is async, so all browser tools must be `async def` using `playwright.async_api`. Sync Playwright raises an error inside an asyncio event loop. Every `page.*` call must be `await`-ed.

**`gs://` URIs for screenshots** — GCS Public Access Prevention is on by default in GCP. Tools store `gs://scriptsim-screenshots/filename.png` URIs instead of public HTTPS URLs. Cloud Run service accounts access GCS directly via IAM. The dashboard handles signed URLs for display.

**`go_back()` tool for navigation** — Agents cannot control browser chrome (the back button). `tools/go_back.py` wraps `page.go_back()` and must be given to any agent that needs to navigate back between pages.

**ADK constraint: tools XOR output_schema** — Gemini does not support both on the same agent. PersonaAgents have tools and no schema. ReportAgents have `output_schema=BugReport` and no tools.

**State passing via `output_key`** — Agents do not return values directly. Each agent writes to session state via `output_key`. Downstream agents read via `{variable_name}` in their instruction templates.
---

## Class Concepts Used

This project implements the following concepts covered in class:

1. **Multi-Agent Orchestration**: Uses a `SequentialAgent` to coordinate a complex 5-phase pipeline.

2. **Parallel Agentic Loops**: Uses a `ParallelAgent` to run multiple adversarial personas simultaneously, each with their own autonomous reasoning and tool-calling loop.

3. **Tool Calling & Browser Automation**: Agents use a suite of custom-built Playwright tools to interact with the DOM, handle navigation, and capture visual evidence.

4. **Structured Synthesis**: Uses a high-capability model (Gemini 2.5 Flash) to deduplicate and rank raw findings from multiple lower-capability agents (Flash-Lite).
