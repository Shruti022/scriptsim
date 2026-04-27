# ScriptSim — Dev Status & Error Log

**Last updated:** 2026-04-27
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
| Orchestrator logging + token counter | Person 2 | DONE |
| `demo_app/` — Flask shop with 5 planted bugs | Person 3 | DONE |
| `dashboard/` — Next.js with live activity console | Person 3 | DONE |
| `api/` — FastAPI POST /scan | Person 3 | DONE |
| `start.py` — one-command launcher | Person 3 | DONE |
| SetupAgent login reliability fix | Person 1 | DONE |
| Persona login fallback + action limit fix | Person 1 | DONE |
| `test_agent.py` pre-login + session state fix | Person 1 | DONE |
| Orchestrator user message, report sequencing, encoding fixes | Person 1 | DONE |
| Kid persona smoke test vs demo app | All | PASS (2026-04-26) |
| Full 4-persona parallel scan end-to-end | All | PASS (2026-04-27) — 3 bugs found, $0.023, 631s |

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

### agents/ and orchestrator.py — fixes applied

| File | Fix | Status |
|------|-----|--------|
| `agents/setup_agent.py` | Imperative instruction forces immediate login tool call | Fixed |
| `agents/persona_agent.py` | `_LOGIN_PREAMBLE` login fallback + max action limit enforcement | Fixed |
| `orchestrator.py` | User message changed to "Begin." — removes agent confusion | Fixed |
| `orchestrator.py` | Report agents changed from ParallelAgent to SequentialAgent | Fixed |
| `orchestrator.py` | `→` replaced with `->` in print statements (Windows encoding) | Fixed |
| `orchestrator.py` | `max_persona_actions` reduced 15→7 for full scan | Fixed |
| `orchestrator.py` | `skip_mapper=True` for full scan (mapper loops on this app) | Fixed |
| `test_agent.py` | Pre-login step + `max_persona_actions` in session state | Fixed |

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
| MapperAgent vs example.com | PASS — clean JSON output |
| PersonaAgent [kid] vs example.com | PASS — all 7 tools fired, 3 GCS screenshots |
| SetupAgent login vs demo app | PASS — cookies saved, LOGIN_SUCCESS |
| Kid persona vs demo app (localhost:5000) | PASS (2026-04-26) — landed on home page, found Bug 2 |
| Full 4-persona scan vs demo app | PASS (2026-04-27) — all 11 agents ran, 3 bugs found, $0.023 |

---

## Person 2 — Completed Work (teammate additions 2026-04-27)

### orchestrator.py — logging and token counter
- Per-scan log files written to `logs/agent_log_{scan_id}.txt` on completion or Ctrl+C
- Per-scan token usage report written to `logs/token_report_{scan_id}.txt`
- Signal handlers (SIGINT, SIGTERM) save logs before exit
- `set_zoom(150)` called for retiree persona browser context

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

## First Successful Full Scan Results (2026-04-27)

Scan ID: `9e4aec31-6f8f-4051-acb3-d11b7ef28495`
URL: `http://localhost:5000`
Elapsed: 631 seconds (~10.5 min) | Cost: $0.023 | API calls: 71

| Agent | API Calls | Tokens |
|-------|-----------|--------|
| setup_agent | 2 | 583 |
| persona_kid | 12 | 20,477 |
| persona_power_user | 40 | 101,281 |
| persona_parent | 9 | 14,938 |
| persona_retiree | 2 | 2,376 |
| report_kid | 1 | 9,650 |
| report_power_user | 1 | 10,037 |
| report_parent | 1 | 10,347 |
| report_retiree | 1 | 10,755 |
| synthesis_agent | 1 | 13,322 |
| eval_agent | 1 | 14,903 |

### Bugs found by the scan

| Rank | Title | Severity | Personas |
|------|-------|----------|---------|
| 1 | Add to Cart not working — cart stays at 0 after adding items | CRITICAL (5) | kid, parent |
| 2 | Cart displays incorrect item quantities | MAJOR (4) | power_user |
| 3 | Search UX unclear for novice users | MINOR (2) | retiree |

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
over one tab — each agent's clicks affected what others saw.
**Fix:** Rewrote `browser.py` to use per-task `BrowserContext` via `asyncio.current_task()` ID.
`get_page()` auto-creates an isolated context for each new task. `login.py` stores cookies
globally in `_default_cookies` so new contexts start logged in. **Resolved.**

### Error 15 — SetupAgent not calling the login tool
**Problem:** LLM responded "I can't perform a full QA scan" instead of calling the `login` tool.
Personas started on `/login` page with empty `_default_cookies`.
**Fix:** Rewrote `setup_agent.py` instruction to be fully imperative: "You MUST immediately
call the login tool. Do not say anything first." **Resolved.**

### Error 16 — Action limit not respected in smoke test mode
**Problem:** "at least {max_persona_actions} actions" was treated as a minimum by the LLM.
**Fix:** Changed to "maximum of {max_persona_actions} tool calls total. STOP when you hit that
limit." Action limit remains soft (LLM approximates it, doesn't enforce it exactly). **Resolved.**

### Error 17 — Personas landing on /login despite SetupAgent running
**Problem:** If SetupAgent failed silently, `_default_cookies` stayed empty and personas
got redirected to `/login`.
**Fix:** Added `_LOGIN_PREAMBLE` to all 4 persona instructions — detects `/login` URL and
completes login steps before starting persona behaviour. Reliable fallback. **Resolved.**

### Error 18 — `test_agent.py` KeyError: `max_persona_actions` not in session state
**Problem:** `{max_persona_actions}` template in persona instruction had no value in the
test script's session state → ADK raised `KeyError` on first turn.
**Fix:** Added `"max_persona_actions": 5` to the initial state dict in `test_agent.py`. **Resolved.**

### Error 19 — `test_agent.py` persona test started on /login
**Problem:** Smoke test ran persona without pre-login — no cookies, redirected to `/login`.
**Fix:** Added `await login(url, email, password)` call before running persona in `test_agent.py`.
Persona now starts on the home page, matching real pipeline behaviour. **Resolved.**

### Error 20 — Orchestrator user message confused all agents
**Problem:** User message "Run full QA scan on {url}. Scan ID: {scan_id}" was propagated to
every sub-agent by ADK's SequentialAgent. SetupAgent refused to call login ("I cannot run a
full QA scan — I only have a login tool"). All 3 non-kid personas also refused. Pipeline
effectively ran with only the kid persona.
**Fix:** Changed user message to `"Begin."` — agents now rely solely on their own instruction
text, which already contains all necessary context. **Resolved.**

### Error 21 — Windows charmap encoding crash in `_save_logs()`
**Problem:** `→` (Unicode U+2192) in print statements inside `_save_logs()` crashed on Windows
when stdout/file used cp1252 encoding. Error: `'charmap' codec can't encode character '→'`.
Despite adding `encoding="utf-8"` to file opens, the success-message `print()` line itself
also contained `→` and crashed inside the try/except, masking the fact that the file write
had actually succeeded.
**Fix:** Replaced all `→` with `->` (ASCII) in print statements in `orchestrator.py`. **Resolved.**

### Error 22 — MapperAgent stuck in an infinite loop
**Problem:** Mapper clicked "Add to Cart" (no navigation), then called `go_back` from the
homepage (no browser history) → `about:blank`. Then `get_page_state` on blank page, somehow
returned to homepage, repeated. Consumed 2M+ input tokens and triggered 429 rate limit.
Also: personas don't read `{feature_map}` in their instructions, so the mapper produced output
that was never used.
**Fix:** Set `skip_mapper = True` in full scan mode in `orchestrator.py`. Mapper skipped until
its looping behaviour is fixed. **Resolved (workaround).**

### Error 23 — 429 RESOURCE_EXHAUSTED — parallel report agents hit rate limit
**Problem:** 4 parallel report agents all made Vertex AI API calls simultaneously, immediately
after 4 parallel personas had also been running. The combined burst of API calls exceeded the
Vertex AI quota. The `ExceptionGroup` from ADK's TaskGroup propagated up and crashed the entire
pipeline before synthesis and eval ran.
**Fix:** Changed `ParallelAgent` for report agents to `SequentialAgent` in `orchestrator.py`.
Report agents now run one at a time, spacing out their 4 API calls. **Resolved.**

### Error 24 — Full scan `max_persona_actions` too high, personas ran 33–40 API calls
**Problem:** `max_persona_actions=15` in full scan mode. Kid ran 33 calls, power_user ran 40
calls. The soft action limit is not enforced precisely by the LLM. High per-persona call counts
amplified the rate limit problem and made scans very long (18+ minutes).
**Fix:** Reduced `max_persona_actions` from 15 to 7 in full scan mode. **Partially resolved —
power_user still ran 40 calls in confirmed working scan. Root cause is soft limit.**

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

### Orchestrator user message must be neutral ("Begin.")
ADK's SequentialAgent passes the same user message to every sub-agent. A descriptive message
like "Run full QA scan" conflicts with agents that have narrow tools (SetupAgent only has login).
Use "Begin." so each agent relies entirely on its own instruction text.

### Report agents run sequentially, not in parallel
Running 4 report agents in parallel immediately after 4 parallel personas caused 429 rate limit
errors on Vertex AI. Sequential execution spaces out the API calls at the cost of ~1 minute
of additional time per scan.

### Mapper skipped in all current scan modes
The mapper loops on apps with non-navigating buttons (like "Add to Cart"). It also uses `go_back`
on the root page which returns `about:blank`. Until fixed, mapper is skipped with
`skip_mapper=True`. Personas explore without a feature map — they find bugs anyway.

### Action limit is a soft limit
ADK has no built-in way to stop an agent after N tool calls. `max_persona_actions` in the
instruction is a hint — honoured approximately. The power_user persona in particular tends to
run many more calls than the limit due to its edge-case testing behaviour.

### Login fallback in persona instructions
All personas include `_LOGIN_PREAMBLE` which detects if the URL is `/login` and completes the
login flow before starting persona behaviour. Acts as a fallback if SetupAgent fails.

---

## Known Remaining Issues

| Issue | Impact | Workaround |
|-------|--------|-----------|
| Action limit is soft — power_user ran 40 calls vs limit of 7 | Longer scans, more quota used | Reduce limit further; accept as demo limitation |
| Retiree gave up after 2 API calls | Weak bug coverage from retiree persona | Strengthen retiree instruction |
| EvalAgent output wrapped in `\`\`\`json\`\`\`` fences | Dashboard shows "? bugs found" — final report parsed as raw string | Add stronger anti-fence instruction to eval_agent |
| Mapper loops on non-navigating buttons | Mapper unusable on current demo app | Skipped; fix mapper go_back logic |
| Cloud Run not deployed | Services run locally only | Pending Person 1 deployment |

---

## Next Steps

### Person 1
- [ ] Fix eval_agent fence wrapping so final report is properly parsed (dashboard shows correct bug count)
- [ ] Strengthen retiree persona instruction so it explores more
- [ ] Cloud Run deployment (session: `person1-cloudrun`)

### Person 2
- [ ] No pending work — agents and orchestrator complete

### Person 3
- [ ] Deploy demo app to Railway/Cloud Run for public URL
- [ ] Update CLAUDE.md with public demo app URL when available

### All together
- [ ] Run full scan on deployed public demo app URL
- [ ] Verify all 5 bugs found across personas
- [ ] Write final project report
