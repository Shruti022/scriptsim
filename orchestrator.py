"""
ScriptSim orchestrator — runs the full 5-phase QA pipeline.

Phase 1: SetupAgent   — logs in, saves cookies to session state
Phase 2: MapperAgent  — crawls the app, builds feature map
Phase 3: ParallelAgent — 4 PersonaAgents browse simultaneously
Phase 4: ReportAgents — 4 ReportAgents produce structured BugReports (parallel)
Phase 5: SynthesisAgent + EvalAgent — dedup, score, rank

Logs written per scan (on completion OR on Ctrl+C / any crash):
  logs/agent_log_{scan_id}.txt    — every agent event, timestamped
  logs/token_report_{scan_id}.txt — token usage breakdown per agent
"""
import asyncio
import json
import uuid
import time
import os
import signal
import atexit
from google.cloud import firestore
from dotenv import load_dotenv

# Load environment variables to ensure Vertex AI auth is picked up
load_dotenv()

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.setup_agent import setup_agent
from agents.mapper_agent import mapper_agent
from agents.persona_agent import make_persona_agent
from agents.report_agent import make_report_agent
from agents.synthesis_agent import synthesis_agent
from agents.eval_agent import eval_agent
from tools.browser import start_browser, close_browser, inject_cookies, set_zoom

PERSONAS = ["kid", "power_user", "parent", "retiree"]

# ── Logs directory ───────────────────────────────────────────────────────────
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# ── Per-scan state ───────────────────────────────────────────────────────────
_TOKEN_LOG: dict = {}
_AGENT_RUNS: list = []
_current_agent: str = None
_agent_start_time: float = None
_scan_start_time: float = None
_current_scan_id: str = None
_agent_log_lines: list = []   # in-memory buffer, flushed on save


def _log(line: str):
    """Print to terminal and buffer for file."""
    print(line)
    _agent_log_lines.append(line)


def _save_logs():
    """Write agent log and token report to files. Safe to call at any time."""
    if not _current_scan_id:
        return

    # ── Agent log ────────────────────────────────────────────────────────────
    agent_log_path = os.path.join(LOGS_DIR, f"agent_log_{_current_scan_id}.txt")
    try:
        with open(agent_log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(_agent_log_lines) + "\n")
        print(f"\n[logs] Agent log saved -> {agent_log_path}")
    except Exception as e:
        print(f"[logs] Could not save agent log: {e}")

    # ── Token report ─────────────────────────────────────────────────────────
    token_path = os.path.join(LOGS_DIR, f"token_report_{_current_scan_id}.txt")
    try:
        total_in = total_out = total_calls = 0
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"TOKEN USAGE REPORT  —  scan: {_current_scan_id}")
        lines.append(f"Generated : {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'='*60}")

        for agent, d in sorted(_TOKEN_LOG.items()):
            total_in    += d["input"]
            total_out   += d["output"]
            total_calls += d["calls"]
            lines.append(f"\n  {agent}")
            lines.append(f"    API calls : {d['calls']}")
            lines.append(f"    Input     : {d['input']:,} tokens")
            lines.append(f"    Output    : {d['output']:,} tokens")
            lines.append(f"    Total     : {d['input'] + d['output']:,} tokens")

        elapsed = time.time() - _scan_start_time if _scan_start_time else 0
        cost = (total_in / 1_000_000) * 0.10 + (total_out / 1_000_000) * 0.40
        lines.append(f"\n{'-'*60}")
        lines.append(f"  GRAND TOTAL")
        lines.append(f"    API calls  : {total_calls}")
        lines.append(f"    Input      : {total_in:,} tokens")
        lines.append(f"    Output     : {total_out:,} tokens")
        lines.append(f"    Total      : {total_in + total_out:,} tokens")
        lines.append(f"    Est. cost  : ${cost:.4f}  (Flash-Lite: $0.10/M in, $0.40/M out)")
        lines.append(f"    Elapsed    : {elapsed:.1f}s")
        lines.append(f"{'='*60}")

        report_text = "\n".join(lines)
        print(report_text)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(report_text + "\n")
        print(f"[logs] Token report saved -> {token_path}")
    except Exception as e:
        print(f"[logs] Could not save token report: {e}")


def _emergency_save(signum=None, frame=None):
    """Called on Ctrl+C or SIGTERM — saves whatever we have so far."""
    print("\n[logs] Interrupted — saving logs before exit...")
    _save_logs()
    os._exit(0)


# Register signal handlers and atexit so files are always written
signal.signal(signal.SIGINT,  _emergency_save)
signal.signal(signal.SIGTERM, _emergency_save)
atexit.register(_save_logs)
# ─────────────────────────────────────────────────────────────────────────────


def _on_agent_start(author: str):
    global _current_agent, _agent_start_time
    _current_agent = author
    _agent_start_time = time.time()
    _AGENT_RUNS.append({"agent": author, "started_at": time.strftime("%H:%M:%S")})
    _log(f"\n{'='*60}")
    _log(f"[AGENT START] {author}  ({time.strftime('%H:%M:%S')})")
    _log(f"{'='*60}")


def _on_tokens(author: str, input_tokens: int, output_tokens: int):
    if author not in _TOKEN_LOG:
        _TOKEN_LOG[author] = {"input": 0, "output": 0, "calls": 0}
    _TOKEN_LOG[author]["input"]  += input_tokens
    _TOKEN_LOG[author]["output"] += output_tokens
    _TOKEN_LOG[author]["calls"]  += 1
    _log(f"  [tokens] {author}: +{input_tokens} in / +{output_tokens} out "
         f"(running total: {_TOKEN_LOG[author]['input']} in / {_TOKEN_LOG[author]['output']} out)")


def _build_pipeline(personas: list[str], skip_mapper: bool = False) -> SequentialAgent:
    persona_agents = [make_persona_agent(p) for p in personas]
    report_agents = [make_report_agent(p) for p in personas]

    sub_agents = [setup_agent]
    if not skip_mapper:
        sub_agents.append(mapper_agent)

    sub_agents.extend([
        ParallelAgent(
            name="persona_parallel",
            description="Selected personas explore the app simultaneously.",
            sub_agents=persona_agents,
        ),
        SequentialAgent(
            name="report_sequential",
            description="ReportAgents convert action logs to structured BugReports (sequential to avoid rate limits).",
            sub_agents=report_agents,
        ),
        synthesis_agent,
        eval_agent,
    ])

    return SequentialAgent(
        name="scriptsim_pipeline",
        description="Full ScriptSim QA scan pipeline.",
        sub_agents=sub_agents,
    )


async def run_scan(
    target_url: str,
    login_email: str = "test@scriptsim.com",
    login_password: str = "TestPass123!",
    scan_id: str = None,
    personas: list[str] = None,
    is_smoke_test: bool = False,
) -> dict:
    """Run a ScriptSim scan. Returns the final ranked report."""
    global _current_agent, _agent_start_time, _scan_start_time, _current_scan_id
    _TOKEN_LOG.clear()
    _AGENT_RUNS.clear()
    _agent_log_lines.clear()
    _current_agent = None
    _scan_start_time = time.time()

    if personas is None:
        personas = PERSONAS

    if is_smoke_test:
        # Smoke test: 1 persona, 5 actions, skip mapper
        personas = [personas[0]] if personas else ["kid"]
        max_mapper_actions = 1
        max_persona_actions = 5
        skip_mapper = True
    else:
        max_mapper_actions = 20
        max_persona_actions = 7
        skip_mapper = True  # mapper loops on this app — skip until fixed

    if scan_id is None:
        scan_id = str(uuid.uuid4())

    _current_scan_id = scan_id

    # Write header to log buffer
    _log(f"ScriptSim Agent Log")
    _log(f"Scan ID  : {scan_id}")
    _log(f"URL      : {target_url}")
    _log(f"Started  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    _log(f"Personas : {personas}")
    _log(f"{'='*60}")

    # Create Firestore document for the scan so the dashboard can find it
    try:
        db = firestore.Client()
        db.collection("scans").document(scan_id).set({
            "target_url": target_url,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "running",
            "is_smoke_test": is_smoke_test,
            "personas": personas
        })
    except Exception as e:
        print(f"Warning: Failed to create Firestore scan document: {e}")

    session_service = InMemorySessionService()
    pipeline = _build_pipeline(personas, skip_mapper=skip_mapper)

    runner = Runner(
        agent=pipeline,
        app_name="scriptsim",
        session_service=session_service,
    )

    # Initial state — all agents read from here via {variable} in their instructions
    initial_state = {
        "scan_id": scan_id,
        "target_url": target_url,
        "login_email": login_email,
        "login_password": login_password,
        "personas": personas,
        "max_mapper_actions": max_mapper_actions,
        "max_persona_actions": max_persona_actions,
    }

    session = await session_service.create_session(
        app_name="scriptsim",
        user_id="scanner",
        state=initial_state,
        session_id=scan_id,
    )

    # Phase 1 + 2: SetupAgent and MapperAgent — single shared browser
    _log(f"[scan:{scan_id}] Starting browser for setup + mapping...")
    await start_browser(target_url)

    setup_events = []
    async for event in runner.run_async(
        user_id="scanner",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Begin.")]
        ),
    ):
        setup_events.append(event)

        author = getattr(event, "author", None)

        # ── Agent start detection ────────────────────────────────────────────
        if author and author != _current_agent:
            _on_agent_start(author)

        # ── Token tracking ───────────────────────────────────────────────────
        if hasattr(event, "usage_metadata") and event.usage_metadata:
            meta = event.usage_metadata
            in_tok  = getattr(meta, "prompt_token_count", 0) or 0
            out_tok = getattr(meta, "candidates_token_count", 0) or 0
            if in_tok or out_tok:
                _on_tokens(author or "unknown", in_tok, out_tok)

        # ── Existing event logging (unchanged) ───────────────────────────────
        if hasattr(event, "content") and event.content:
            text_parts = []
            if hasattr(event.content, "parts"):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text:
                        text_parts.append(p.text)
                    elif hasattr(p, "function_call") and p.function_call:
                        text_parts.append(f"Action: {p.function_call.name}")
                    elif hasattr(p, "function_response") and p.function_response:
                        pass

            text_part = " ".join(text_parts)
            if not text_part and author:
                text_part = f"Agent {author} is thinking..."

            _log(f"[{author}] {text_part[:120]}")

            # Log to Firestore for dashboard live activity
            try:
                db = firestore.Client()
                db.collection("scans").document(scan_id).collection("activity").add({
                    "author": author,
                    "message": text_part[:500],
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
            except:
                pass

    await close_browser()

    # Save logs on natural completion
    _save_logs()

    # Retrieve final report from session state
    updated_session = await session_service.get_session(
        app_name="scriptsim",
        user_id="scanner",
        session_id=session.id,
    )
    final_report_raw = updated_session.state.get("final_report", "{}")

    try:
        final_report = json.loads(final_report_raw)
    except (json.JSONDecodeError, TypeError):
        final_report = {"raw": final_report_raw}

    print(f"\n[scan:{scan_id}] Scan complete. {final_report.get('total_bugs', '?')} bugs found.")
    return {"scan_id": scan_id, "report": final_report}


async def _setup_persona_browser(target_url: str, cookies_json: str, persona: str):
    """Start a browser for a persona, inject auth cookies, set zoom if needed."""
    await start_browser(target_url)
    try:
        cookies = json.loads(cookies_json)
        if isinstance(cookies, list):
            await inject_cookies(cookies)
    except (json.JSONDecodeError, TypeError):
        pass
    if persona == "retiree":
        await set_zoom(150)


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    print(f"Running ScriptSim scan against: {url}")
    result = asyncio.run(run_scan(target_url=url))
    print(json.dumps(result["report"], indent=2))