"""
ScriptSim orchestrator — runs the full 5-phase QA pipeline.

Phase 1: SetupAgent   — logs in, saves cookies to session state
Phase 2: MapperAgent  — crawls the app, builds feature map
Phase 3: ParallelAgent — 4 PersonaAgents browse simultaneously
Phase 4: ReportAgents — 4 ReportAgents produce structured BugReports (parallel)
Phase 5: SynthesisAgent + EvalAgent — dedup, score, rank
"""
import asyncio
import json
import uuid

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


def _build_pipeline() -> SequentialAgent:
    persona_agents = [make_persona_agent(p) for p in PERSONAS]
    report_agents = [make_report_agent(p) for p in PERSONAS]

    return SequentialAgent(
        name="scriptsim_pipeline",
        description="Full ScriptSim QA scan pipeline.",
        sub_agents=[
            setup_agent,
            mapper_agent,
            ParallelAgent(
                name="persona_parallel",
                description="All 4 personas explore the app simultaneously.",
                sub_agents=persona_agents,
            ),
            ParallelAgent(
                name="report_parallel",
                description="4 ReportAgents convert action logs to structured BugReports.",
                sub_agents=report_agents,
            ),
            synthesis_agent,
            eval_agent,
        ],
    )


async def run_scan(
    target_url: str,
    login_email: str = "test@scriptsim.com",
    login_password: str = "TestPass123!",
    scan_id: str = None,
) -> dict:
    """Run a full ScriptSim scan against target_url. Returns the final ranked report."""
    if scan_id is None:
        scan_id = str(uuid.uuid4())

    session_service = InMemorySessionService()
    pipeline = _build_pipeline()

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
    }

    session = await session_service.create_session(
        app_name="scriptsim",
        user_id="scanner",
        state=initial_state,
        session_id=scan_id,
    )

    # Phase 1 + 2: SetupAgent and MapperAgent — single shared browser
    print(f"[scan:{scan_id}] Starting browser for setup + mapping...")
    await start_browser(target_url)

    setup_events = []
    async for event in runner.run_async(
        user_id="scanner",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Run full QA scan on {target_url}. Scan ID: {scan_id}")]
        ),
    ):
        setup_events.append(event)
        if hasattr(event, "content") and event.content:
            print(f"[{event.author}] {str(event.content)[:120]}")

    await close_browser()

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
