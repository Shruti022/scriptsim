"""
ScriptSim orchestrator — runs the full 5-phase QA pipeline.

Phase 1: SetupAgent   — logs in, saves cookies to session state
Phase 2: MapperAgent  — crawls the app, builds feature map
Phase 3: ParallelAgent — PersonaAgents browse simultaneously
Phase 4: ReportAgents — produce structured BugReports
Phase 5: SynthesisAgent + EvalAgent — dedup, score, rank
"""
import asyncio
import json
import uuid
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import SequentialAgent, ParallelAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.setup_agent import setup_agent
from agents.mapper_agent import mapper_agent
from agents.persona_agent import make_persona_agent
from agents.report_agent import make_report_agent
from agents.synthesis_agent import make_synthesis_agent
from agents.eval_agent import eval_agent
from tools.browser import start_browser, close_browser, set_context_name

PERSONAS = ["kid", "power_user", "parent", "retiree"]


def _strip_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers that LLMs sometimes add."""
    text = text.strip()
    if text.startswith("```"):
        text = text[text.index("\n") + 1:] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:text.rfind("```")]
    return text.strip()


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
            description="ReportAgents convert action logs to structured BugReports.",
            sub_agents=report_agents,
        ),
        make_synthesis_agent(personas),
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
    login_url: str = None,
    scan_id: str = None,
    personas: list[str] = None,
    scan_mode: str = "full",
) -> dict:
    """Run a ScriptSim scan. Returns the final ranked report."""
    if login_url is None:
        login_url = f"{target_url}/login"

    if personas is None:
        personas = PERSONAS

    if scan_mode == "fast":
        # Login preamble costs ~4 tool calls; budget 10 total so ~6 remain for exploration.
        personas = [personas[0]] if personas else ["kid"]
        max_mapper_actions = 1
        max_persona_actions = 10
        skip_mapper = True
    elif scan_mode == "smoke":
        # Budget 15 total so ~11 remain for exploration after login.
        personas = [personas[0]] if personas else ["kid"]
        max_mapper_actions = 1
        max_persona_actions = 15
        skip_mapper = True
    else:
        # Full scan: budget 20 total so ~16 remain for exploration after login.
        max_mapper_actions = 20
        max_persona_actions = 20
        skip_mapper = True  # mapper loops on this app — skip until fixed

    if scan_id is None:
        scan_id = str(uuid.uuid4())

    print(f"[scan:{scan_id}] Starting — url={target_url} mode={scan_mode} personas={personas}")

    # Create Firestore document so the dashboard can find it
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
    }

    session = await session_service.create_session(
        app_name="scriptsim",
        user_id="scanner",
        state=initial_state,
        session_id=scan_id,
    )

    # start_browser sets the context name to "setup" automatically
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
            print(f"[{author}] started")
            if author.startswith("persona_"):
                persona_name = author[len("persona_"):]
                set_context_name(persona_name)
            else:
                set_context_name("setup")

        if hasattr(event, "content") and event.content:
            text_parts = []
            if hasattr(event.content, "parts"):
                for p in event.content.parts:
                    if hasattr(p, "text") and p.text:
                        text_parts.append(p.text)
                    elif hasattr(p, "function_call") and p.function_call:
                        text_parts.append(f"Action: {p.function_call.name}")

            text_part = " ".join(text_parts)
            if not text_part and author:
                text_part = f"Agent {author} is thinking..."

            print(f"  [{author}] {text_part}")

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

    # Retrieve final report from session state
    updated_session = await session_service.get_session(
        app_name="scriptsim",
        user_id="scanner",
        session_id=session.id,
    )
    final_report_raw = updated_session.state.get("final_report", "{}")

    try:
        final_report = json.loads(_strip_fences(final_report_raw))
    except (json.JSONDecodeError, TypeError):
        final_report = {"raw": final_report_raw}

    # Update Firestore scan status to completed
    try:
        db_client = firestore.Client()
        db_client.collection("scans").document(scan_id).update({
            "status": "completed",
            "report": final_report
        })
    except Exception as e:
        print(f"Failed to update scan status: {e}")

    print(f"[scan:{scan_id}] Complete — {final_report.get('total_bugs', '?')} bugs found.")
    return {"scan_id": scan_id, "report": final_report}


if __name__ == "__main__":
    import sys

    url           = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    email         = sys.argv[2] if len(sys.argv) > 2 else "test@scriptsim.com"
    password      = sys.argv[3] if len(sys.argv) > 3 else "TestPass123!"
    login_url_arg = sys.argv[4] if len(sys.argv) > 4 else None

    print(f"Running ScriptSim scan against: {url}")
    result = asyncio.run(run_scan(
        target_url=url,
        login_email=email,
        login_password=password,
        login_url=login_url_arg,
    ))
    print(json.dumps(result["report"], indent=2))