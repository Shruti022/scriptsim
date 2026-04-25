# ScriptSim — Dev Status & Error Log

**Last updated:** 2026-04-25  
**Person 1 session:** person1-playwright-tools  
**GitHub:** https://github.com/Shruti022/scriptsim

---

## Project Completion Overview

| Area | Owner | Status |
|------|-------|--------|
| `tools/` — Playwright tool functions | Person 1 | DONE + Tested |
| `Dockerfile` | Person 1 | Done (initial) |
| `requirements.txt` | Person 1 | Done (initial) |
| GCS bucket `scriptsim-screenshots` | Person 1 | Created in GCP |
| Firestore database | Person 1 | Not started |
| Cloud Run deployment | Person 1 | Not started |
| `agents/` — ADK agent definitions | Person 2 | DONE |
| `schemas/bug_report.py` | Person 2 | DONE |
| `orchestrator.py` | Person 2 | DONE |
| `demo_app/` — Flask app with planted bugs | Person 3 | Not started |
| `dashboard/` — Next.js frontend | Person 3 | Not started |
| `api/` — FastAPI scan trigger | Person 3 | Not started |
| `README.md` | Person 1 | Done |

---

## Person 1 — Completed Work

### tools/ directory (all 9 files)

| File | What it does | Status |
|------|-------------|--------|
| `tools/__init__.py` | Exports all tool functions for ADK import | Done |
| `tools/browser.py` | Browser singleton — `start_browser`, `get_page`, `inject_cookies`, `set_zoom`, `close_browser` | Done |
| `tools/get_page_state.py` | Returns JSON snapshot of page: URL, title, buttons, inputs, links, text, modals, errors | Done + Tested |
| `tools/click_element.py` | Clicks element by visible text, falls back to aria-label | Done + Tested |
| `tools/type_text.py` | Fills input by placeholder or aria-label, with optional clear-first | Done + Tested |
| `tools/hover_element.py` | Hovers over element, captures any tooltip text that appears | Done + Tested |
| `tools/take_screenshot.py` | Screenshot → system temp dir → uploads to GCS → returns `gs://` URI | Done + Tested (local) |
| `tools/log_bug.py` | Writes bug to Firestore `scans/{scan_id}/bugs/` with severity 1–5 | Done, untested (needs Firestore) |
| `tools/login.py` | Navigates login page, fills email+password, submits, returns cookies for SetupAgent | Done, untested (needs demo app) |

### GCP Infrastructure

| Resource | Config | Status |
|----------|--------|--------|
| GCS bucket `scriptsim-screenshots` | Region: us-central1, Standard class | Created + Tested |
| Firestore database | Native mode, us-central1, Standard edition | Created + Tested |
| Cloud Run service `scriptsim-worker` | us-central1 | Not created yet |

### Live Test Results

| Tool | Test | Result |
|------|------|--------|
| `get_page_state` | `https://example.com` | PASS |
| `click_element` | click "Learn more" on example.com | PASS — navigated to iana.org |
| `type_text` | type into DuckDuckGo search box | PASS |
| `hover_element` | hover on example.com | PASS |
| `take_screenshot` | screenshot example.com | PASS — uploaded to `gs://scriptsim-screenshots/gcs-test_1777135923.png` |
| `log_bug` | write bug to Firestore scan `test-scan-001` | PASS — doc ID `fZb0FWUYAiKawgWeAABP` written |
| `login` | — | Untested — needs Person 3 demo app URL |

---

## Errors Encountered & How They Were Fixed

### Error 1 — `tools/` directory didn't exist

**Problem:** `browser.py` and `get_page_state.py` were sitting in the project root. The `Dockerfile` copies `tools/` and imports reference `tools.browser`, so the files were in the wrong place.

**Fix:** Created the full `tools/` directory with all 9 required files. Deleted the orphaned root-level copies.

**Status:** Resolved.

---

### Error 2 — `greenlet==3.0.3` fails to build on Python 3.14

**Problem:**
```
error: failed-wheel-build-for-install
greenlet
fatal error C1189: #error: "this header requires Py_BUILD_CORE define"
```
`playwright==1.44.0` hard-pins `greenlet==3.0.3`, which was released before Python 3.14 and has no pre-built wheel for it.

**Fix:** Upgraded playwright to `1.58.0` locally (`pip install "playwright>=1.50.0"`), which works with `greenlet==3.4.0`.

**Impact on Docker:** None — the Dockerfile uses `mcr.microsoft.com/playwright/python:v1.44.0-jammy` with its own Python 3.11. Version mismatch is local-only.

**Status:** Resolved. Local = playwright 1.58.0 / Docker = playwright 1.44.0.

---

### Error 3 — `ModuleNotFoundError: No module named 'tools'` when running tools as scripts

**Problem:** Running `python tools/get_page_state.py` adds `tools/` to `sys.path[0]`, so `from tools.browser import get_page` fails — Python looks for a `tools` package *inside* `tools/`.

**Fix:** All tool files use a try/except import fallback:
```python
try:
    from tools.browser import get_page   # works when imported as package
except ImportError:
    from browser import get_page         # works when run as script directly
```
Applied to all 7 tool files and all `__main__` blocks.

**Status:** Resolved.

---

### Error 4 — `playwright install chromium` downloaded wrong version

**Problem:** After upgrading playwright 1.44 → 1.58, the shell `playwright install chromium` downloaded for the old version. Browser binary not found:
```
BrowserType.launch: Executable doesn't exist at
C:\...\ms-playwright\chromium_headless_shell-1208\...
```

**Fix:** Used `python -m playwright install chromium` — this ensures the install command uses the same playwright Python package that gets imported.

**Status:** Resolved. Chromium 145.0.7632.6 installed.

---

### Error 5 — Cannot enable public access on GCS bucket

**Problem:** GCS bucket had "Public access prevention" enforced at the bucket level. No edit button appeared in the Configuration tab to disable it. `blob.make_public()` would have failed at runtime.

**Fix:** Dropped public access entirely — switched `take_screenshot.py` to use `gs://` URIs instead of public HTTPS URLs. Removed `blob.make_public()` call. This is correct because:
- Agents run in Cloud Run and access GCS via service account — no public URL needed
- `gs://` URIs are stored in Firestore bug reports and used internally by agents
- Dashboard display (Person 3) will handle signed URLs separately if needed

**Status:** Resolved. `take_screenshot` now returns `gs://scriptsim-screenshots/{filename}`.

---

## Design Decisions

### Sync vs Async Playwright

**Conflict:** `CLAUDE.md` says "Always use async Playwright". `playwright-tools.md` says tools must be sync functions because ADK tool functions cannot be `async def`.

**Decision:** All tools use sync Playwright. ADK wraps tool calls synchronously — async tools break the agent loop. The CLAUDE.md async note predates the ADK constraint.

### GCS — `gs://` URI vs Public HTTPS URL

**Decision:** Tools return `gs://scriptsim-screenshots/{filename}` URIs, not public HTTPS URLs. Cloud Run service accounts have Storage Object Viewer/Creator permissions and can access GCS directly. Public access is unnecessary and a security risk.

---

## What Is and Isn't in CLAUDE.md

### In CLAUDE.md
- Project description, 5 persona types
- Locked tech stack
- Architecture phases (Setup → Mapper → Parallel → Report → Synthesis/Eval)
- Critical ADK constraint: `output_schema` and `tools` are mutually exclusive
- Agent state via `output_key`
- Ownership boundaries (Person 1 / 2 / 3)
- Full folder structure
- Playwright rules
- GCP config (project, region, Firestore collection, GCS bucket, Cloud Run service)
- Demo app URL + credentials + 5 planted bugs
- How to run tools locally + session naming

### NOT in CLAUDE.md (important things to know)
- `playwright==1.44.0` incompatible with Python 3.14 — use `>=1.50.0` locally
- Use `python -m playwright install` not `playwright install`
- `tools/__init__.py` exports all functions for ADK agent import
- `take_screenshot` returns `gs://` URI, not a public URL (GCP Public Access Prevention blocks public access)
- `log_bug` clamps severity: `max(1, min(5, severity))`
- `login.py` returns raw cookies as a list — SetupAgent persists them to Firestore
- GCS bucket created but Cloud Run service account permissions still need to be set when Cloud Run is deployed

---

## Next Steps for Person 1

- [x] Create all 9 tool files in `tools/`
- [x] Delete orphaned root-level `browser.py` and `get_page_state.py`
- [x] Test `get_page_state`, `click_element`, `type_text`, `hover_element`, `take_screenshot` locally
- [x] Create GCS bucket `scriptsim-screenshots` in us-central1
- [x] Install `gcloud` CLI + run `gcloud auth application-default login`
- [x] Create Firestore database (Native mode, us-central1) in GCP console
- [x] GCS upload test — `take_screenshot` confirmed writing to `gs://scriptsim-screenshots/`
- [x] Firestore test — `log_bug` confirmed writing to `scans/test-scan-001/bugs/`
- [ ] Test `login.py` + `click_element` against demo app (needs Person 3 deploy URL)
- [ ] Set up Cloud Run deployment (session: `person1-cloudrun`)
- [ ] Grant Cloud Run service account `Storage Object Creator` + `Cloud Datastore User` roles in GCP IAM

## Person 2 — Completed Work

| File | What it does |
|------|-------------|
| `schemas/bug_report.py` | Pydantic `BugReport` model with 9 fields, severity 1–5 |
| `agents/setup_agent.py` | LlmAgent — calls `login` tool, outputs `auth_cookies` to session state |
| `agents/mapper_agent.py` | LlmAgent — crawls app with `get_page_state` + `click_element`, outputs `feature_map` |
| `agents/persona_agent.py` | `make_persona_agent(persona)` — creates persona-specific LlmAgent with 6 tools, no schema |
| `agents/report_agent.py` | `make_report_agent(persona)` — LlmAgent with `output_schema=BugReport`, no tools |
| `agents/synthesis_agent.py` | LlmAgent — deduplicates bugs, cross-persona severity boost, outputs `deduplicated_bugs` |
| `agents/eval_agent.py` | LlmAgent — final scoring + ranking, outputs `final_report` JSON |
| `orchestrator.py` | `run_scan(url)` — SequentialAgent pipeline with ParallelAgent for personas + reports |

**ADK constraint verified:** `PersonaAgent` has 6 tools + no `output_schema`. `ReportAgent` has `output_schema=BugReport` + zero tools.

**Personas implemented:** kid (8yo), power_user (22yo), parent (45yo), retiree (67yo)

**Pipeline:** SetupAgent → MapperAgent → ParallelAgent(4 personas) → ParallelAgent(4 reports) → SynthesisAgent → EvalAgent

**Untested:** needs Person 3's demo app URL to run end-to-end
