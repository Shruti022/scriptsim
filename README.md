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
├── tools/                  # Person 1 — Playwright browser tools
│   ├── browser.py          # Browser singleton (start, stop, inject cookies)
│   ├── get_page_state.py   # Snapshot of current page (buttons, inputs, links)
│   ├── click_element.py    # Click by visible text or aria-label
│   ├── type_text.py        # Fill input by placeholder or aria-label
│   ├── hover_element.py    # Hover to reveal tooltips/dropdowns
│   ├── take_screenshot.py  # Screenshot → GCS bucket
│   ├── log_bug.py          # Write bug to Firestore
│   └── login.py            # Fill login form, return session cookies
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

## Team

| Person | Owns | Status |
|--------|------|--------|
| Person 1 (Shruti) | `tools/`, Dockerfile, Cloud Run | Done |
| Person 2 | `agents/`, `schemas/`, `orchestrator.py` | Done |
| Person 3 | `demo_app/`, `dashboard/`, `api/` | In progress |

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
pip install "playwright>=1.50.0"
pip install google-adk google-cloud-firestore google-cloud-storage fastapi uvicorn
python -m playwright install chromium
```

> **Note:** `requirements.txt` pins `playwright==1.44.0` for Docker. Locally on Python 3.14, install `playwright>=1.50.0` instead.

### Authenticate with GCP

```bash
gcloud auth application-default login
gcloud config set project agentic-fp-scriptsim
gcloud auth application-default set-quota-project agentic-fp-scriptsim
```

### Test individual tools

```bash
python tools/get_page_state.py https://example.com
python tools/click_element.py https://example.com "Learn more"
python tools/take_screenshot.py https://example.com test-label
```

### Run a full scan (once demo app is deployed)

```bash
python orchestrator.py https://<demo-app-url>
```

---

## Demo App

- **URL:** TBD (Person 3 deploying to Railway)
- **Test credentials:** `test@scriptsim.com` / `TestPass123!`
- **Planted bugs:** XSS in search, silent cart failure, crash at 10+ items, confusing error message, frozen checkout button

---

## Key Design Decisions

**Sync Playwright over async** — Google ADK tool functions must be regular `def`, not `async def`. All browser tools use `playwright.sync_api`.

**`gs://` URIs for screenshots** — GCS Public Access Prevention is on by default in GCP. Tools store `gs://scriptsim-screenshots/filename.png` URIs instead of public HTTPS URLs. Cloud Run service accounts access GCS directly. The dashboard handles signed URLs for display.

**ADK constraint: tools XOR output_schema** — Gemini does not support both on the same agent. PersonaAgents have 6 tools and no schema. ReportAgents have `output_schema=BugReport` and no tools.

**State passing via `output_key`** — Agents do not return values directly. Each agent writes to session state via `output_key`. Downstream agents read via `{variable_name}` in their instruction templates.
