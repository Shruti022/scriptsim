"""
ScriptSim orchestrator — runs the full 5-phase QA pipeline.

Phase 1: SetupAgent   — logs in, saves cookies to session state
Phase 2: MapperAgent  — crawls the app, builds feature map
Phase 3: ParallelAgent — PersonaAgents browse simultaneously
Phase 4: ReportAgents — produce structured BugReports
Phase 5: SynthesisAgent + EvalAgent — dedup, score, rank

Logs written per scan (on completion OR on Ctrl+C / any crash):
  logs/agent_log_{scan_id}.txt    — every agent event, timestamped
  logs/token_report_{scan_id}.txt — token usage breakdown per agent
"""
import asyncio
import json
import os
import signal
import atexit
import time
import uuid
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.setup_agent import make_setup_agent
from agents.mapper_agent import make_mapper_agent
from agents.persona_agent import make_persona_agent
from agents.report_agent import make_report_agent
from agents.synthesis_agent import make_synthesis_agent
from agents.eval_agent import make_eval_agent
from tools.browser import start_browser, close_browser, set_context_name

PERSONAS = ["kid", "power_user", "parent", "retiree"]

# ── Logs directory ────────────────────────────────────────────────────────────
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# ── Per-scan globals ──────────────────────────────────────────────────────────
_TOKEN_LOG: dict[str, dict] = {}   # agent_name → {in, out, calls}
_AGENT_RUNS: dict[str, float] = {} # agent_name → start_time
_agent_log_lines: list[str] = []
_current_agent: str | None = None
_agent_start_time: float | None = None
_scan_start_time: float = 0.0
_current_scan_id: str | None = None


def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    _agent_log_lines.append(line)
    print(line)


def _save_logs():
    if not _current_scan_id:
        return
    elapsed = time.time() - _scan_start_time
    generated = time.strftime("%Y-%m-%d %H:%M:%S")

    # Agent activity log
    log_path = os.path.join(LOGS_DIR, f"agent_log_{_current_scan_id}.txt")
    with open(log_path, "w") as f:
        f.write("\n".join(_agent_log_lines))
    print(f"[logs] Agent log saved → {log_path}")

    # Token report
    token_path = os.path.join(LOGS_DIR, f"token_report_{_current_scan_id}.txt")
    SEP  = "=" * 60
    DASH = "-" * 60
    RATE_IN  = 0.10   # per million tokens
    RATE_OUT = 0.40

    total_in = total_out = total_calls = 0
    for tok in _TOKEN_LOG.values():
        total_in    += tok.get("in", 0)
        total_out   += tok.get("out", 0)
        total_calls += tok.get("calls", 0)
    total_tokens = total_in + total_out
    est_cost = (total_in / 1_000_000 * RATE_IN) + (total_out / 1_000_000 * RATE_OUT)

    lines = [
        SEP,
        f"TOKEN USAGE REPORT  —  scan: {_current_scan_id}",
        f"Generated : {generated}",
        SEP,
    ]

    if _TOKEN_LOG:
        for agent, tok in sorted(_TOKEN_LOG.items()):
            in_t  = tok.get("in", 0)
            out_t = tok.get("out", 0)
            calls = tok.get("calls", 0)
            a_cost = (in_t / 1_000_000 * RATE_IN) + (out_t / 1_000_000 * RATE_OUT)
            lines += [
                DASH,
                f"  {agent}",
                f"    API calls  : {calls}",
                f"    Input      : {in_t} tokens",
                f"    Output     : {out_t} tokens",
                f"    Total      : {in_t + out_t} tokens",
                f"    Est. cost  : ${a_cost:.4f}",
            ]

    lines += [
        DASH,
        "  GRAND TOTAL",
        f"    API calls  : {total_calls}",
        f"    Input      : {total_in} tokens",
        f"    Output     : {total_out} tokens",
        f"    Total      : {total_tokens} tokens",
        f"    Est. cost  : ${est_cost:.4f}  (Flash-Lite: ${RATE_IN}/M in, ${RATE_OUT}/M out)",
        f"    Elapsed    : {elapsed:.1f}s",
        SEP,
    ]

    with open(token_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[logs] Token report saved → {token_path}")


def _emergency_save(signum=None, frame=None):
    print("\n[logs] Signal received — saving logs before exit...")
    _save_logs()
    os._exit(0)


signal.signal(signal.SIGINT, _emergency_save)
signal.signal(signal.SIGTERM, _emergency_save)
atexit.register(_save_logs)


def _on_agent_start(agent_name: str):
    global _current_agent, _agent_start_time
    if _current_agent and _agent_start_time:
        duration = time.time() - _agent_start_time
        _log(f"[{_current_agent}] finished in {duration:.1f}s")
    _current_agent = agent_name
    _agent_start_time = time.time()
    _AGENT_RUNS[agent_name] = _agent_start_time
    ts = time.strftime("%H:%M:%S")
    _log(f"")
    _log(f"{'='*60}")
    _log(f"[AGENT START] {agent_name}  ({ts})")
    _log(f"{'='*60}")


def _on_tokens(agent_name: str, in_tok: int, out_tok: int):
    if agent_name not in _TOKEN_LOG:
        _TOKEN_LOG[agent_name] = {"in": 0, "out": 0, "calls": 0}
    _TOKEN_LOG[agent_name]["in"] += in_tok
    _TOKEN_LOG[agent_name]["out"] += out_tok
    _TOKEN_LOG[agent_name]["calls"] += 1
    running_in  = _TOKEN_LOG[agent_name]["in"]
    running_out = _TOKEN_LOG[agent_name]["out"]
    _log(f"  [tokens] {agent_name}: +{in_tok} in / +{out_tok} out (running total: {running_in} in / {running_out} out)")


def _strip_fences(text: any) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers that LLMs sometimes add."""
    if not isinstance(text, str):
        return text
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:text.rfind("```")]
    return text.strip()


def _build_pipeline(personas: list[str], skip_mapper: bool = False) -> SequentialAgent:
    persona_agents = [make_persona_agent(p) for p in personas]
    report_agents = [make_report_agent(p) for p in personas]

    sub_agents = [make_setup_agent()]
    if not skip_mapper:
        sub_agents.append(make_mapper_agent())

    sub_agents.extend([
        ParallelAgent(
            name="persona_parallel",
            description="Selected personas explore the app simultaneously.",
            sub_agents=persona_agents,
        ),
        SequentialAgent(
            name="report_sequential",
            description="ReportAgents convert action logs to structured BugReports.",
            sub_agents=report_agents,
        ),
        make_synthesis_agent(personas),
        make_eval_agent(),
    ])

    return SequentialAgent(
        name="scriptsim_pipeline",
        description="Full ScriptSim QA scan pipeline.",
        sub_agents=sub_agents,
    )


async def run_scan(
    target_url: str,
    login_email: str = None,
    login_password: str = None,
    login_url: str = None,
    scan_id: str = None,
    personas: list[str] = None,
    scan_mode: str = "full",
) -> dict:
    """Run a ScriptSim scan. Returns the full ranked report."""
    global _current_scan_id, _scan_start_time

    if login_email is None:
        login_email = os.environ.get("LOGIN_EMAIL", "")
    if login_password is None:
        login_password = os.environ.get("LOGIN_PASSWORD", "")
    if login_url is None:
        login_url = f"{target_url}/login"

    if personas is None:
        personas = PERSONAS

    if scan_mode == "fast":
        personas = [personas[0]] if personas else ["kid"]
        max_mapper_actions = 1
        max_persona_actions = 7
        skip_mapper = True
    elif scan_mode == "smoke":
        personas = [personas[0]] if personas else ["kid"]
        max_mapper_actions = 1
        max_persona_actions = 10
        skip_mapper = True
    else:
        max_mapper_actions = 10
        max_persona_actions = 12
        skip_mapper = True  # mapper loops on this app — skip until fixed

    if scan_id is None:
        scan_id = str(uuid.uuid4())

    # Reset per-scan state
    _TOKEN_LOG.clear()
    _AGENT_RUNS.clear()
    _agent_log_lines.clear()
    _current_scan_id = scan_id
    _scan_start_time = time.time()

    _log(f"ScriptSim Agent Log")
    _log(f"Scan ID  : {scan_id}")
    _log(f"URL      : {target_url}")
    _log(f"Started  : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    _log(f"Personas : {personas}")
    _log(f"{'='*60}")

    try:
        db = firestore.Client()
        db.collection("scans").document(scan_id).set({
            "target_url": target_url,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "running",
            "scan_mode": scan_mode,
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

    initial_state = {
        "scan_id": scan_id,
        "target_url": target_url,
        "login_url": login_url,
        "login_email": login_email,
        "login_password": login_password,
        "personas": personas,
        "max_mapper_actions": max_mapper_actions,
        "max_persona_actions": max_persona_actions,
        # Pre-populate empty action logs so report agents never crash if a persona fails
        **{f"action_log_{p}": "No actions recorded." for p in personas},
        **{f"bug_report_{p}": '{"bugs": []}' for p in personas},
    }

    session = await session_service.create_session(
        app_name="scriptsim",
        user_id="scanner",
        state=initial_state,
        session_id=scan_id,
    )

    await start_browser(target_url)

    current_agent = None
    async for event in runner.run_async(
        user_id="scanner",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Begin.")]
        ),
    ):
        author = getattr(event, "author", None)

        # Switch named browser context when a new agent starts
        if author and author != current_agent:
            current_agent = author
            _on_agent_start(author)
            if author.startswith("persona_"):
                set_context_name(author[len("persona_"):])
            else:
                set_context_name("setup")

        # Token tracking
        if hasattr(event, "usage_metadata") and event.usage_metadata:
            meta = event.usage_metadata
            in_tok  = getattr(meta, "prompt_token_count", 0) or 0
            out_tok = getattr(meta, "candidates_token_count", 0) or 0
            if in_tok or out_tok:
                _on_tokens(author or "unknown", in_tok, out_tok)

        if hasattr(event, "content") and event.content:
            text_parts = []
            if hasattr(event.content, "parts"):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text:
                        text_parts.append(p.text)
                    elif hasattr(p, "function_call") and p.function_call:
                        text_parts.append(f"Action: {p.function_call.name}")

            text_part = " ".join(text_parts).strip()
            if not text_part and author:
                text_part = f"Agent {author} is thinking..."

            _log(f"[{author}] {text_part}")

            # Log to Firestore for dashboard live activity
            try:
                db_client = firestore.Client()
                db_client.collection("scans").document(scan_id).collection("activity").add({
                    "author": str(author) if author else "system",
                    "message": text_part,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"Activity write error: {e}")

    await close_browser()
    _save_logs()

    updated_session = await session_service.get_session(
        app_name="scriptsim",
        user_id="scanner",
        session_id=session.id,
    )
    final_report_raw = updated_session.state.get("final_report", {})

    if isinstance(final_report_raw, dict):
        final_report = final_report_raw
    else:
        try:
            final_report = json.loads(_strip_fences(final_report_raw))
        except (json.JSONDecodeError, TypeError):
            final_report = {"raw": str(final_report_raw)}

    try:
        db_client = firestore.Client()
        db_client.collection("scans").document(scan_id).update({
            "status": "completed",
            "report": final_report
        })
    except Exception as e:
        print(f"Failed to update scan status: {e}")

    _log(f"[scan:{scan_id}] Complete — {final_report.get('total_bugs', '?')} bugs found.")
    return {"scan_id": scan_id, "report": final_report}


if __name__ == "__main__":
    import sys

    url           = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TARGET_URL", "http://localhost:5000")
    email         = sys.argv[2] if len(sys.argv) > 2 else None
    password      = sys.argv[3] if len(sys.argv) > 3 else None
    login_url_arg = sys.argv[4] if len(sys.argv) > 4 else None

    print(f"Running ScriptSim scan against: {url}")
    result = asyncio.run(run_scan(
        target_url=url,
        login_email=email,
        login_password=password,
        login_url=login_url_arg,
    ))
    print(json.dumps(result["report"], indent=2))