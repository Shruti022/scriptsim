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
        ParallelAgent(
            name="report_parallel",
            description="ReportAgents convert action logs to structured BugReports.",
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
        max_persona_actions = 15
        skip_mapper = False

    if scan_id is None:
        scan_id = str(uuid.uuid4())

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
            text_parts = []
            if hasattr(event.content, "parts"):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text:
                        text_parts.append(p.text)
                    elif hasattr(p, "function_call") and p.function_call:
                        text_parts.append(f"Action: {p.function_call.name}")
                    elif hasattr(p, "function_response") and p.function_response:
                        # Optional: log function result
                        pass
            
            text_part = " ".join(text_parts)
            if not text_part and hasattr(event, "author"):
                text_part = f"Agent {event.author} is thinking..."

            print(f"[{event.author}] {text_part[:120]}")
            
            # Log to Firestore for dashboard live activity
            try:
                db = firestore.Client()
                db.collection("scans").document(scan_id).collection("activity").add({
                    "author": event.author,
                    "message": text_part[:500],
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
            except: pass

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
