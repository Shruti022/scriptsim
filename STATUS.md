# ScriptSim — Dev Status & Error Log

**Last updated:** 2026-04-26
**GitHub:** https://github.com/Shruti022/scriptsim

---

## Project Completion Overview

| Area | Owner | Status |
|------|-------|--------|
| `tools/` — 10 async Playwright tools | Person 1 | DONE + Tested |
| Browser isolation (per-task contexts) | Person 1 | DONE + Tested |
| GCS bucket `scriptsim-screenshots` | Person 1 | Created + Tested |
| Firestore database | Person 1 | Created + Tested |
| GCP IAM access for teammates | Person 1 | Configured |
| Cloud Run deployment | Person 1 | Not started |
| `agents/` — 6 ADK agents | Person 2 | DONE |
| `schemas/bug_report.py` | Person 2 | DONE |
| `orchestrator.py` (smoke test + persona selection) | Person 2 | DONE |
| `demo_app/` — Flask shop with 5 planted bugs | Person 3 | DONE |
| `dashboard/` — Next.js with live activity console | Person 3 | DONE |
| `api/` — FastAPI POST /scan | Person 3 | DONE |
| `start.py` — one-command launcher | Person 3 | DONE |
| SetupAgent login reliability fix | Person 1 | DONE |
| Persona login fallback + action limit fix | Person 1 | DONE |
| `test_agent.py` pre-login + session state fix | Person 1 | DONE |
| Kid persona smoke test vs demo app | All | PASS — found Bug 2 (silent cart) |
| Full 4-persona parallel scan | All | Awaiting end-to-end test |

---

## Person 1 — Completed Work

### tools/ directory (all 10 files)

| File | What it does | Status |
|------|-------------|--------|
| `tools/__init__.py` | Exports all tool functions | Done |
| `tools/browser.py` | Per-task async browser contexts — each persona gets isolated BrowserContext | Done + Tested |
| `tools/get_page_state.py` | JSON snapshot: URL, title, buttons, inputs, links, errors | Done + Tested |
| `tools/click_element.py` | Click by visible text or aria-label | Done + Tested |
| `tools/type_text.py` | Fill input by placeholder or aria-label | Done + Tested |
| `tools/hover_element.py` | Hover to reveal tooltips | Done + Tested |
| `tools/take_screenshot.py` | Screenshot → GCS `gs://scriptsim-screenshots/` | Done + Tested |
| `tools/log_bug.py` | Write bug to Firestore `scans/{scan_id}/bugs/` | Done + Tested |
| `tools/login.py` | Login form + stores cookies globally for parallel personas | Done + Tested |
| `tools/go_back.py` | Browser back via `page.go_back()` | Done + Tested |

### agents/ — fixes applied (Person 1 fixed, Person 2 owns)

| File | Fix | Status |
|------|-----|--------|
| `agents/setup_agent.py` | Imperative instruction forces immediate login tool call | Fixed |
| `agents/persona_agent.py` | `_LOGIN_PREAMBLE` login fallback + max action limit enforcement | Fixed |

### test_agent.py — fixes applied

| Fix | Status |
|-----|--------|
| Pre-login step before running persona (mirrors SetupAgent in pipeline) | Fixed |
| `max_persona_actions=5` added to initial session state | Fixed |

### GCP Infrastructure

| Resource | Config | Status |
|----------|--------|--------|
| GCS bucket `scriptsim-screenshots` | us-central1, Standard | Created + Tested |
| Firestore database | Native mode, us-central1 | Created + Tested |
| IAM access | Vertex AI User + Storage Object Creator + Cloud Datastore User | Configured for teammates |
| Cloud Run service `scriptsim-worker` | us-central1 | Not created yet |

### Live Test Results

| Test | Result |
|------|--------|
| `get_page_state` on example.com | PASS |
| `click_element` on example.com | PASS |
| `type_text` on DuckDuckGo | PASS |
| `hover_element` on example.com | PASS |
| `take_screenshot` → GCS upload | PASS — `gs://scriptsim-screenshots/gcs-test_1777135923.png` |
| `log_bug` → Firestore write | PASS — doc `fZb0FWUYAiKawgWeAABP` |
| MapperAgent full scan vs example.com | PASS — clean JSON output, go_back working |
| PersonaAgent [kid] vs example.com | PASS — all 7 tools fired, 3 GCS screenshots |
| SetupAgent login vs demo app (localhost:5000) | PASS — cookies saved |
| Kid persona vs demo app (localhost:5000) | PASS — landed on home page, found Bug 2 (silent cart), screenshots to GCS |
| Full 4-persona parallel scan | Awaiting end-to-end test |

---

## Person 3 — Completed Work

### demo_app/app.py — 5 planted bugs

| Bug | Description |
|-----|-------------|
| Bug 1 — XSS | Search query rendered with `\|safe` — `<script>alert(1)</script>` executes |
| Bug 2 — Silent failure | "Super Gadget" add-to-cart returns success but item never added |
| Bug 3 — Crash | Adding 10+ "Awesome Widget" raises ValueError → 500 error page |
| Bug 4 — Confusing error | 500 page says "chickens have come home to roost" |
| Bug 5 — Frozen checkout | Checkout button permanently disabled, says "unavailable" |

### api/main.py
- `POST /scan` — accepts URL, personas, smoke_test flag; runs scan in background; returns scan_id immediately
- `GET /health` — health check
- CORS enabled for dashboard

### dashboard/
- Persona picker (8-Year-Old, Power User, Anxious Parent, Retiree)
- Demo App / Live Website toggle
- Smoke Test Mode checkbox
- Live activity console (polls Firestore every few seconds)
- Bug report display

### start.py
- Launches demo_app (port 5000), API (port 8000), dashboard (port 3000) simultaneously
- Auto-installs npm dependencies if node_modules missing

---

## Errors Encountered & How They Were Fixed

### Error 1 — `tools/` directory didn't exist
**Fix:** Created full `tools/` package. **Resolved.**

### Error 2 — `greenlet==3.0.3` build failure on Python 3.14
**Fix:** `pip install "playwright>=1.50.0"` locally. Docker still uses 1.44.0. **Resolved.**

### Error 3 — `ModuleNotFoundError: No module named 'tools'`
**Fix:** try/except import fallback in all tool files. **Resolved.**

### Error 4 — Wrong Chromium binary after playwright upgrade
**Fix:** Use `python -m playwright install chromium`. **Resolved.**

### Error 5 — GCS public access prevention
**Fix:** Return `gs://` URIs instead of public HTTPS URLs. **Resolved.**

### Error 6 — Sync Playwright crashes inside asyncio
**Fix:** Rewrote all tools to `async def` using `async_playwright`. **Resolved.**

### Error 7 — Gemini model 404 from Vertex AI
**Fix:** Changed all model names to `gemini-2.5-flash-lite` / `gemini-2.5-flash`. **Resolved.**

### Error 8 — MapperAgent stuck on sub-pages
**Fix:** Added `tools/go_back.py`, gave it to MapperAgent and all PersonaAgents. **Resolved.**

### Error 9 — Agent output wrapped in markdown fences
**Fix:** Strengthened instructions: "Do not wrap in ```json or markdown fences". **Resolved.**

### Error 10 — SetupAgent had wrong model name (missed in Error 7 batch fix)
**Fix:** Updated `setup_agent.py` to `gemini-2.5-flash-lite`. **Resolved.**

### Error 11 — `nest_asyncio` left in requirements.txt after being abandoned
**Fix:** Removed from `requirements.txt`. **Resolved.**

### Error 12 — SynthesisAgent and EvalAgent missing anti-fence instruction
**Fix:** Added "Do not wrap in markdown fences" to both. **Resolved.**

### Error 13 — Flask not installed, demo app fails to start
**Problem:** `start.py` launches demo app but Flask wasn't in main `requirements.txt`.
**Fix:** `pip install flask werkzeug` separately (demo_app has its own requirements.txt). **Resolved.**

### Error 14 — Parallel personas share one browser tab (chaos)
**Problem:** All 4 PersonaAgents shared the same global `_page`. Running in parallel they fought
over one tab — each agent's clicks affected what others saw. Second scan picked up stale state.
**Fix:** Rewrote `browser.py` to use per-task `BrowserContext` via `asyncio.current_task()` ID.
`get_page()` auto-creates an isolated context for each new task. `login.py` stores cookies
globally in `_default_cookies` so new contexts start logged in. `start_browser()` clears
all stale contexts before launching. **Resolved.**

### Error 15 — SetupAgent not calling the login tool
**Problem:** LLM responded "I can't perform a full QA scan" or described the plan instead of
calling the `login` tool. Personas started on the `/login` page with no cookies.
**Fix:** Rewrote `setup_agent.py` instruction to be fully imperative: "You MUST immediately
call the login tool. Do not say anything first." Removed all explanatory language. **Resolved.**

### Error 16 — Action limit not respected in smoke test mode
**Problem:** Persona instructions said "at least {max_persona_actions} actions" — LLM treated
this as a minimum, not a maximum. Smoke test ran for 10+ minutes with 1 persona.
**Fix:** Changed to "You have a maximum of {max_persona_actions} tool calls total. Stop and
write your action log the moment you hit that limit." Added identical limit line to each
persona's closing instruction. **Resolved (soft limit — LLM honours it approximately).**

### Error 17 — Personas landing on /login despite SetupAgent running
**Problem:** If SetupAgent failed silently, `_default_cookies` stayed empty and every persona
context navigated to the app URL and got redirected to /login.
**Fix:** Added `_LOGIN_PREAMBLE` to all 4 persona instructions: on first `get_page_state`,
if URL contains "/login", perform the 4 login steps before starting persona behaviour.
Acts as a reliable fallback independent of SetupAgent. **Resolved.**

### Error 18 — `test_agent.py` KeyError: `max_persona_actions` not in session state
**Problem:** Persona instruction contains `{max_persona_actions}` template variable. The
smoke test script created a session without this key → ADK raised `KeyError` on first turn.
**Fix:** Added `"max_persona_actions": 5` to the initial state dict in `test_agent.py`. **Resolved.**

### Error 19 — `test_agent.py` persona test started on /login (no pre-login step)
**Problem:** The smoke test script ran the persona directly without calling SetupAgent or
`login()` first. Browser navigated to demo app and was redirected to /login.
**Fix:** Added a pre-login call (`await login(url, email, password)`) at the start of
`run_persona()` in `test_agent.py`. Persona now starts on the home page, matching the
real pipeline behaviour. **Resolved.**

---

## Design Decisions

### Per-task browser isolation
Each asyncio Task (persona) gets its own `BrowserContext` — isolated cookies, storage, and page.
`_contexts` dict maps `id(asyncio.current_task())` → `(BrowserContext, Page)`.
New contexts auto-inject `_default_cookies` (set by login) and navigate to `_default_url`.

### Async Playwright (not sync)
ADK is async. Sync Playwright raises error inside asyncio loop. All tools are `async def`.

### GCS `gs://` URIs, not public HTTPS URLs
Public Access Prevention blocks public URLs. Use `gs://` URIs; Cloud Run accesses via IAM.

### `go_back` as dedicated tool
Agents cannot click browser chrome. `go_back()` wraps `page.go_back()`.

### ADK tools XOR output_schema
PersonaAgents have 7 tools, no schema. ReportAgents have `output_schema=BugReport`, no tools.

### Orchestrator smoke test mode
`is_smoke_test=True` → 1 persona, max 5 actions, skip mapper. Enables fast 3-minute demos.

### Action limit is a soft limit
ADK has no built-in way to stop an agent after N tool calls. `max_persona_actions` in the
instruction text is a strong hint — LLMs honour it approximately but not precisely. This is
acceptable for demos; the pipeline does not hang because ADK's own turn limits apply.

### Login fallback in persona instructions
All personas include `_LOGIN_PREAMBLE` which detects if the URL is `/login` and completes the
login flow before starting persona behaviour. This makes personas resilient to SetupAgent
failures and makes the standalone `test_agent.py` smoke test reliable.

---

## Next Steps

### Person 1
- [ ] Run full 4-persona parallel scan via dashboard and verify all 5 bugs found
- [ ] Cloud Run deployment (session: `person1-cloudrun`)
- [ ] Grant Cloud Run service account IAM roles when deploying

### Person 2
- [ ] No pending work — agents complete

### Person 3
- [ ] Deploy demo app to Railway/Cloud Run for public URL
- [ ] Update CLAUDE.md with public demo app URL when available

### All together
- [ ] Run full scan on deployed public demo app URL
- [ ] Verify all 5 bugs found across personas
- [ ] Review final ranked report JSON
