"""
Smoke test — runs a single agent against a live URL.
All ADK imports happen inside the async context so the event loop
exists before aiohttp/google-genai try to use it.

Usage (run in PowerShell, not inside Claude Code):
    python test_agent.py                          # MapperAgent on example.com
    python test_agent.py persona kid              # kid PersonaAgent
    python test_agent.py mapper https://myapp.com
"""
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from tools.browser import start_browser, close_browser


async def run_mapper(url: str):
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from agents.mapper_agent import mapper_agent

    print(f"\n=== MapperAgent smoke test on {url} ===")

    session_service = InMemorySessionService()
    runner = Runner(
        agent=mapper_agent,
        app_name="scriptsim_test",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="scriptsim_test",
        user_id="tester",
        state={"target_url": url, "scan_id": "test-001"},
    )

    async for event in runner.run_async(
        user_id="tester",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Map the features of {url}")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            print(f"  [{event.author}]", str(event.content)[:200])

    updated = await session_service.get_session(
        app_name="scriptsim_test", user_id="tester", session_id=session.id
    )
    result = updated.state.get("feature_map", "NOT SET")
    print("\n--- feature_map output ---")
    print(result[:800] if result else "EMPTY")


async def run_persona(persona: str, url: str):
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from agents.persona_agent import make_persona_agent
    from tools.login import login

    print(f"\n=== PersonaAgent [{persona}] smoke test on {url} ===")

    # Pre-authenticate so persona starts on the app (mirrors SetupAgent in real pipeline)
    print("  Pre-login: authenticating before persona starts...")
    login_result = await login(
        url=f"{url}/login",
        email="test@scriptsim.com",
        password="TestPass123!",
    )
    print(f"  Login result: {login_result[:80]}")

    agent = make_persona_agent(persona)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="scriptsim_test",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="scriptsim_test",
        user_id="tester",
        state={
            "scan_id": "test-001",
            "target_url": url,
            "max_persona_actions": 5,
        },
    )

    async for event in runner.run_async(
        user_id="tester",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Explore {url} as your persona and find bugs. Scan ID: test-001")]
        ),
    ):
        if hasattr(event, "content") and event.content:
            print(f"  [{event.author}]", str(event.content)[:200])

    updated = await session_service.get_session(
        app_name="scriptsim_test", user_id="tester", session_id=session.id
    )
    result = updated.state.get(f"action_log_{persona}", "NOT SET")
    print(f"\n--- action_log_{persona} output ---")
    print(result[:800] if result else "EMPTY")


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "mapper"

    if mode == "persona":
        persona = sys.argv[2] if len(sys.argv) > 2 else "kid"
        url = sys.argv[3] if len(sys.argv) > 3 else "https://example.com"
        print(f"Starting browser for persona [{persona}]...")
        await start_browser(url)
        try:
            await run_persona(persona, url)
        finally:
            await close_browser()
            print("Browser closed.")
    else:
        url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
        print(f"Starting browser for mapper...")
        await start_browser(url)
        try:
            await run_mapper(url)
        finally:
            await close_browser()
            print("Browser closed.")


if __name__ == "__main__":
    asyncio.run(main())
