# ScriptSim — Project Overview

---

## The Idea

When you build a website, you test it as yourself — a developer who knows exactly what everything does. But your actual users are not you.

One is a confused 8-year-old clicking random buttons. One is a paranoid parent reading every word before touching anything. One is a power user actively trying to break your site. One is an elderly person who gets lost without clear labels.

**ScriptSim pretends to be all four of them at the same time** and tells you what they found broken — without you writing a single test.

### Why this is different from normal testing

Traditional automated testing (Selenium, Cypress, unit tests) checks *specific things* you already thought to check — "does clicking this button change that value?" You have to write those tests yourself, which means you only find bugs you already knew to look for.

ScriptSim agents are not checking specific things. They are *behaving like people* and finding bugs through that behaviour — the same way a real user would discover them. You give it a URL. It gives you a ranked bug report.

---

## The Pipeline — 5 Phases in Order

```
SetupAgent
    ↓
[MapperAgent]   ← currently skipped
    ↓
PersonaAgent (kid)  ─┐
PersonaAgent (power) ─┤  ← run in parallel, isolated browsers
PersonaAgent (parent)─┤
PersonaAgent (retiree)┘
    ↓
ReportAgent (kid)
ReportAgent (power)   ← run sequentially
ReportAgent (parent)
ReportAgent (retiree)
    ↓
SynthesisAgent
    ↓
EvalAgent
    ↓
Final ranked bug report
```

---

### Phase 1 — SetupAgent

One agent opens a real Chromium browser and logs into the target app using provided credentials. It saves the session cookies globally so every persona that follows starts already authenticated. Without this step, all four personas would land on the login page and waste their entire budget trying to log in.

---

### Phase 2 — MapperAgent *(designed, currently skipped)*

Was designed to crawl the app before the personas run — visiting every link, recording every page and feature — and produce a feature map the personas could use to guide their exploration. Currently disabled because it gets stuck in a loop on apps with non-navigating buttons (like "Add to Cart"). Personas find bugs effectively without it.

---

### Phase 3 — 4 PersonaAgents running simultaneously

This is the heart of the system. Four AI agents run at the same time, each in their own completely isolated browser window, each with a distinct personality embedded in their instructions.

**Kid (8-year-old)**
Clicks things randomly out of curiosity. Types silly things like "cat" or "12345" in every text field. Tries to add 50+ items to the cart to see what happens. Gets confused by jargon. Does not read warnings. Finds bugs by stumbling into them.

**Power User (22-year-old developer)**
Tries XSS payloads (`<script>alert(1)</script>`) in every input field. Tests boundary values: 0, -1, empty string, 500-character strings. Clicks every button multiple times rapidly. Reads error messages looking for stack traces or internal information leaks. Tries SQL injection. Systematically probes edge cases.

**Anxious Parent (45-year-old)**
Reads every page carefully before clicking anything. Looks for privacy policy and terms of service. Hovers over buttons before clicking to see what they do. Worries about giving credit card details — looks for trust signals. Tries to complete a full purchase but abandons checkout if anything seems unclear or alarming.

**Retiree (67-year-old)**
Looks for phone numbers and a help or FAQ section. Gets confused by icons with no text labels. Prefers to hover over things to understand them before clicking. Uses the search bar for everything. Makes typos. Finds bugs that only appear when users are slow, careful, and unfamiliar with modern UI patterns.

Each persona uses 7 tools to interact with the browser:

| Tool | What it does |
|------|-------------|
| `get_page_state` | Reads the current page — URL, title, all buttons, inputs, links, and visible errors |
| `click_element` | Clicks a button or link by its visible text or aria-label |
| `type_text` | Types into an input field found by placeholder or aria-label |
| `hover_element` | Hovers over an element to reveal tooltips or dropdown menus |
| `go_back` | Navigates back in browser history |
| `take_screenshot` | Captures the current page and uploads it to Google Cloud Storage |
| `log_bug` | Writes a structured bug entry to Firestore with description, severity, and screenshot URL |

When a persona finishes, it writes a plain-English action log: every page visited, every bug noticed, every action taken.

---

### Phase 4 — 4 ReportAgents (one per persona)

Each persona's action log is messy free text — stream of consciousness narration of what the persona did and noticed. A ReportAgent reads that log and converts it into one structured bug report with defined fields:

- Title
- Description
- Severity (1–5)
- Steps to reproduce
- Expected behaviour
- Actual behaviour
- Screenshot URL
- URL where the bug occurred
- Which persona found it

These run one at a time (not in parallel) to avoid exceeding Vertex AI API rate limits.

---

### Phase 5 — SynthesisAgent + EvalAgent

**SynthesisAgent** reads all four structured reports and merges them. If the kid and the parent both independently found the same broken cart, they become one bug with both personas listed as affected. Duplicates are removed. The combined list is produced.

**EvalAgent** reads the merged list and produces the final ranked report — bugs ordered by severity, with a scan summary, critical/major/minor counts, and full reproduction steps. This is what gets displayed in the dashboard.

---

## How the Technology Fits Together

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent framework | Google ADK | Manages pipeline, runs agents in sequence or parallel, passes data between them |
| LLM (personas, setup) | Gemini 2.5 Flash-Lite via Vertex AI | Fast and cheap — ~$0.023 per full 4-persona scan |
| LLM (reports, synthesis, eval) | Gemini 2.5 Flash via Vertex AI | Higher reasoning quality for structured output |
| Browser automation | Playwright + Chromium (async) | Real browser — agents control an actual browser, not a fake HTTP client |
| Bug storage | Google Cloud Firestore | Stores bug reports and live activity feed for the dashboard |
| Screenshot storage | Google Cloud Storage | Stores screenshots; private bucket, accessed via `gs://` URIs |
| API | FastAPI | Accepts `POST /scan` from dashboard, runs pipeline as a background task |
| Frontend | Next.js dashboard | Persona picker, URL input, live activity console, bug report display |
| Demo target | Flask app | Fake online shop with 5 bugs deliberately planted to test the system |

---

## Key Engineering Decisions

### Browser isolation per persona
Each of the 4 parallel personas gets its own completely separate `BrowserContext` — isolated cookies, local storage, and browser tab. They cannot see or interfere with each other's sessions. This was the hardest part to get right because all four run inside the same Python asyncio event loop. The solution maps each asyncio Task to its own context using `asyncio.current_task()` as a key.

### Cookie injection from SetupAgent
SetupAgent logs in once and stores the cookies globally in memory. When each persona's browser context is created, those cookies are injected automatically. Every persona starts already logged in, at the target URL, ready to explore. Personas also have a fallback: if they land on a login page, they log in themselves before starting their persona behaviour.

### Agent communication via session state
Agents do not call each other and do not share Python objects. They communicate through a shared session state dictionary managed by ADK. PersonaAgent writes its action log to `state["action_log_kid"]`. ReportAgent reads it via `{action_log_kid}` in its instruction template. This is how the full pipeline passes data from phase to phase.

### Neutral pipeline trigger message
ADK's SequentialAgent passes the same user message to every sub-agent in the pipeline. The message must be neutral — `"Begin."` — because a descriptive message like "Run a full QA scan" confuses agents that have narrow tools. SetupAgent only has a login tool; if it sees "run a QA scan" it refuses.

### Sequential report agents
Running all 4 report agents in parallel after 4 parallel personas caused Vertex AI to return 429 rate limit errors — too many API calls at once. Report agents now run sequentially, spacing out the calls by about 30 seconds total at the cost of a slightly longer scan.

---

## Confirmed Scan Results (2026-04-27)

Four full scans completed. Two on the demo app, two on real public websites.

### Demo App Scans

| Metric | Scan 1 | Scan 2 (latest) |
|--------|--------|-----------------|
| Total time | 631s (~10.5 min) | 708s (~12 min) |
| Total cost | $0.023 | $0.021 |
| API calls | 71 | 62 |
| Agents that ran | 11 | 11 |
| Bugs found (parsed) | 3 | 2 |
| Dashboard output | "? bugs found" (fence bug) | "2 bugs found" (correct) |

Bugs found in latest demo scan:

| Rank | Bug | Severity | Found by |
|------|-----|----------|---------|
| 1 | Add to Cart broken — cart stays empty, View Cart link fails | Critical (5) | Kid, Parent, Power User |
| 2 | Missing help or contact section | Major (4) | Retiree |

### Real Website Scans — Generalization Confirmed

**Saucedemo.com** (https://www.saucedemo.com) — 618s, $0.016, 3 bugs found.
A public Selenium/Playwright practice site. Pipeline ran end-to-end successfully. However, saucedemo
uses React component memory for auth state (no cookies/localStorage) — our session injection
couldn't pre-authenticate personas, so bugs reported were mostly login-related. Identified as a
known limitation of React SPA auth.

**automationexercise.com** (https://automationexercise.com) — 682s, $0.028, 4 bugs found.
A public e-commerce practice site with standard cookie-based sessions. Cookie injection confirmed
working — all 4 personas started already logged in. System found real UX issues through persona
behaviour on a site it had never seen before.

| Rank | Bug | Severity | Found by |
|------|-----|----------|---------|
| 1 | Products button unresponsive | Critical (5) | Kid, Power User, Retiree |
| 2 | Login redirects to homepage (was already logged in) | Critical (5) | Power User |
| 3 | Password field unresponsive | Critical (5) | Parent |
| 4 | No phone number on Contact Us page | Major (4) | Retiree |

The system found these issues through persona behaviour alone on a site it had never been told about.

---

## Demo App — 5 Planted Bugs

The demo target is a simple Flask online shop built specifically to test ScriptSim. Five bugs were deliberately planted:

| # | Bug | How to trigger |
|---|-----|---------------|
| 1 | XSS in search | Search for `<script>alert(1)</script>` — executes in the browser |
| 2 | Silent cart failure | Add "Super Gadget" — success message shown but item never appears in cart |
| 3 | Crash at 10+ items | Add "Awesome Widget" 10+ times — server throws 500 error |
| 4 | Confusing error message | Trigger the 500 — error page says "chickens have come home to roost" |
| 5 | Frozen checkout | Go to cart — Checkout button is permanently disabled with no explanation |

Test credentials: `test@scriptsim.com` / `TestPass123!`

---

## How to Run It

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install flask werkzeug
python -m playwright install chromium

# 2. Create .env (copy from .env.example, fill in GCP details)

# 3. Authenticate with GCP
gcloud auth application-default login

# 4. Start everything
python start.py
# Opens: demo app (port 5000), API (port 8000), dashboard (port 3000)

# 5. Open the dashboard
# http://localhost:3000
# Select Demo App, pick personas, click Run Parallel Scan
```

Smoke test (single persona, no dashboard):
```bash
python test_agent.py persona kid http://localhost:5000
```

---

## Team

| Person | Owns |
|--------|------|
| Person 1 (Shruti) | `tools/` — all browser automation, GCP infrastructure, Dockerfile, Cloud Run |
| Person 2 | `agents/`, `schemas/`, `orchestrator.py` — full ADK pipeline |
| Person 3 | `demo_app/`, `dashboard/`, `api/`, `start.py` — product and frontend |
