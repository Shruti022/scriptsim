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
| GCS bucket `scriptsim-screenshots` | Person 1 | Created + Tested |
| Firestore database | Person 1 | Created + Tested |
| Cloud Run deployment | Person 1 | Not started |
| `agents/` — ADK agent definitions | Person 2 | DONE |
| `schemas/bug_report.py` | Person 2 | DONE |
| `orchestrator.py` | Person 2 | DONE |
| First end-to-end Gemini scan | Person 1+2 | **DONE — MapperAgent ran successfully** |
| `demo_app/` — Flask app with planted bugs | Person 3 | Not started |
| `dashboard/` — Next.js frontend | Person 3 | Not started |
| `api/` — FastAPI scan trigger | Person 3 | Not started |
| `README.md` | All | Done |

---

## Person 1 — Completed Work

### tools/ directory (all 10 files)

| File | What it does | Status |
|------|-------------|--------|
| `tools/__init__.py` | Exports all tool functions for ADK import | Done |
| `tools/browser.py` | Async browser singleton — `start_browser`, `get_page`, `inject_cookies`, `set_zoom`, `close_browser` | Done + Tested |
| `tools/get_page_state.py` | Returns JSON snapshot of page: URL, title, buttons, inputs, links, text, modals, errors | Done + Tested |
| `tools/click_element.py` | Clicks element by visible text, falls back to aria-label | Done + Tested |
| `tools/type_text.py` | Fills input by placeholder or aria-label, with optional clear-first | Done + Tested |
| `tools/hover_element.py` | Hovers over element, captures any tooltip text that appears | Done + Tested |
| `tools/take_screenshot.py` | Screenshot → system temp dir → uploads to GCS → returns `gs://` URI | Done + Tested |
| `tools/log_bug.py` | Writes bug to Firestore `scans/{scan_id}/bugs/` with severity 1–5 | Done + Tested |
| `tools/login.py` | Navigates login page, fills email+password, submits, returns cookies for SetupAgent | Done, untested (needs demo app) |
| `tools/go_back.py` | Navigates browser back using `page.go_back()` — needed because agents can't click browser chrome | Done |

### GCP Infrastructure

| Resource | Config | Status |
|----------|--------|--------|
| GCS bucket `scriptsim-screenshots` | Region: us-central1, Standard class | Created + Tested |
| Firestore database | Native mode, us-central1, Standard edition | Created + Tested |
| IAM access for teammates | Vertex AI User + Storage Object Creator + Cloud Datastore User | Configured |
| Cloud Run service `scriptsim-worker` | us-central1 | Not created yet |

### Live Test Results

| Test | Result |
|------|--------|
| `get_page_state` on example.com | PASS |
| `click_element` — click "Learn more" on example.com | PASS — navigated to iana.org |
| `type_text` — DuckDuckGo search box | PASS |
| `hover_element` — example.com | PASS |
| `take_screenshot` — example.com | PASS — `gs://scriptsim-screenshots/gcs-test_1777135923.png` |
| `log_bug` — write to Firestore scan `test-scan-001` | PASS — doc ID `fZb0FWUYAiKawgWeAABP` |
| **Full MapperAgent scan vs example.com** | **PASS — first successful Gemini API call** |
| **PersonaAgent [kid] scan vs example.com** | **PASS — all 7 tools fired, screenshots uploaded to GCS** |
| `login` | Untested — needs Person 3 demo app URL |

---

## Errors Encountered & How They Were Fixed

### Error 1 — `tools/` directory didn't exist

**Problem:** `browser.py` and `get_page_state.py` were in the project root instead of inside `tools/`. ADK imports reference `tools.browser`.

**Fix:** Created the full `tools/` package with all required files, deleted orphaned root-level copies.

**Status:** Resolved.

---

### Error 2 — `greenlet==3.0.3` fails to build on Python 3.14

**Problem:**
```
error: failed-wheel-build-for-install greenlet
fatal error C1189: "this header requires Py_BUILD_CORE define"
```
`playwright==1.44.0` pins `greenlet==3.0.3` which has no wheel for Python 3.14.

**Fix:** Upgraded playwright locally to `>=1.50.0`. Docker still uses `playwright==1.44.0` with Python 3.11 — no conflict.

**Status:** Resolved. Local = playwright 1.58.0, Docker = playwright 1.44.0.

---

### Error 3 — `ModuleNotFoundError: No module named 'tools'` running tools as scripts

**Problem:** Running `python tools/get_page_state.py` adds `tools/` to `sys.path[0]`, so `from tools.browser import get_page` fails — it looks for `tools` *inside* `tools/`.

**Fix:** All tool files use a try/except import fallback:
```python
try:
    from tools.browser import get_page   # works when imported as package
except ImportError:
    from browser import get_page         # works when run as script directly
```

**Status:** Resolved.

---

### Error 4 — `playwright install chromium` installed wrong browser version

**Problem:** After upgrading playwright 1.44 → 1.58, `playwright install chromium` (shell command) downloaded for the old version. Browser binary not found.

**Fix:** Use `python -m playwright install chromium` — this uses the exact playwright version that Python imports.

**Status:** Resolved. Chromium 145.0.7632.6 installed.

---

### Error 5 — GCS bucket public access prevention

**Problem:** GCS bucket had Public Access Prevention enforced. `blob.make_public()` would fail at runtime. No way to disable it in the console.

**Fix:** Dropped public access entirely. `take_screenshot.py` now returns `gs://` URIs instead of public HTTPS URLs. Cloud Run service accounts access GCS directly via IAM — no public URL needed.

**Status:** Resolved. All screenshots stored as `gs://scriptsim-screenshots/{filename}`.

---

### Error 6 — Sync Playwright cannot run inside asyncio event loop

**Problem:** Original tools used sync Playwright (`playwright.sync_api`). ADK runner is async — calling a sync Playwright function inside an async event loop raises:
```
playwright._impl._errors.Error: It looks like you are using Playwright Sync API inside the asyncio loop.
```

Also tried `nest_asyncio` to patch the loop but it broke `aiohttp`'s `asyncio.timeout()`:
```
TypeError: object CancelledError can't be used in 'await' expression
```

**Fix:** Rewrote all 9 tool files to `async def` using `async_playwright` from `playwright.async_api`. All `page.*` calls are now `await`-ed. The ADK runner handles async tools natively.

**Status:** Resolved. All tools are async.

---

### Error 7 — Gemini model 404 NOT_FOUND from Vertex AI

**Problem:** All agent files used preview model names (`gemini-2.5-flash-lite-preview-06-17`, `gemini-2.5-flash-preview-05-20`) that don't exist in Vertex AI:
```
404 NOT_FOUND: publishers/google/models/gemini-2.5-flash-lite-preview-06-17 not found
```

**Fix:** Listed available models via Vertex AI API. Confirmed available IDs:
- `gemini-2.5-flash-lite` — fast, cheap (PersonaAgent, MapperAgent, SetupAgent)
- `gemini-2.5-flash` — more capable (ReportAgent, SynthesisAgent, EvalAgent)

Updated all 5 agent files to use these IDs.

**Status:** Resolved. First successful Gemini API call confirmed.

---

### Error 8 — MapperAgent stuck on sub-pages (no browser back)

**Problem:** MapperAgent clicked "Learn more" and navigated to a sub-page, then tried to click a "Back" button (which doesn't exist in the page content). It looped trying different selectors and never returned to the original page.

**Fix:** Added `tools/go_back.py` which calls `page.go_back()` — the real browser back. Added it to MapperAgent and all PersonaAgents. Updated mapper instruction to use `go_back` after each link click.

**Status:** Resolved.

---

### Error 9 — MapperAgent output wrapped in markdown code fences

**Problem:** Despite "Output ONLY valid JSON" in the instruction, the agent returned:
```
```json
{ ... }
```
```
This breaks downstream agents that try to `json.loads()` the `feature_map` session state.

**Fix:** Strengthened the instruction: "Output ONLY the raw JSON object, nothing else. Do not wrap it in \`\`\`json or any markdown."

**Status:** Resolved (needs re-test to confirm).

---

## Design Decisions

### Async Playwright (not sync)

All tools are `async def` using `async_playwright`. The CLAUDE.md note about sync Playwright is outdated — ADK is async and sync Playwright cannot run inside an asyncio loop.

### GCS `gs://` URIs, not public HTTPS URLs

Tools return `gs://scriptsim-screenshots/{filename}` URIs. Cloud Run service accounts access GCS via IAM. Public access is blocked at the bucket level and is unnecessary.

### `go_back` as a dedicated tool

Agents cannot control browser chrome (back button). A `go_back()` tool wrapping `page.go_back()` is required for any navigation-heavy agent.

---

## Next Steps

### Person 1
- [x] Re-run `python test_agent.py mapper https://example.com` — `go_back` works, raw JSON confirmed
- [x] Test `python test_agent.py persona kid https://example.com` — all 7 tools fired, GCS screenshots confirmed
- [ ] Set up Cloud Run deployment (session: `person1-cloudrun`)
- [ ] Grant Cloud Run service account `Storage Object Creator` + `Cloud Datastore User` IAM roles
- [ ] Test `login.py` against demo app once Person 3 deploys

### Person 2 (done — no pending)

### Person 3 (pending)
- [ ] Build Flask demo app with 5 planted bugs
- [ ] Deploy to Railway (or Cloud Run)
- [ ] Build Next.js dashboard
- [ ] Build FastAPI `/scan` endpoint

### Full end-to-end test (all three)
- [ ] Run `python orchestrator.py <demo_app_url>` once Person 3 deploys
- [ ] Verify bugs appear in Firestore + screenshots in GCS
- [ ] Review final ranked report JSON
