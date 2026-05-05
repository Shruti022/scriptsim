import sys
import os
import uuid
import asyncio
import threading
import json
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orchestrator import run_scan

app = FastAPI(title="ScriptSim API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SESSIONS_FILE = os.path.join(project_root, "captured_sessions.json")

def _load_sessions() -> dict:
    if os.path.exists(_SESSIONS_FILE):
        try:
            with open(_SESSIONS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_sessions(sessions: dict):
    try:
        with open(_SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)
    except Exception as e:
        print(f"Warning: Failed to save sessions: {e}")

_captured_sessions: dict = _load_sessions()


class ScanRequest(BaseModel):
    url: str
    email: Optional[str] = None
    password: Optional[str] = None
    personas: list[str] = ["kid", "power_user", "parent", "retiree"]
    scan_mode: str = "full"
    is_demo: bool = False


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str


class SessionStatusResponse(BaseModel):
    url: str
    has_session: bool
    cookies_count: int = 0


async def capture_session_async(url: str) -> dict:
    """Open a visible browser with a floating button overlay.
    User logs in manually then clicks the button to capture session."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        # Re-inject the button on every navigation so it persists across redirects
        async def inject_button(p_page):
            try:
                await p_page.evaluate("""
                    if (!document.getElementById('scriptsim-ready-btn')) {
                        const btn = document.createElement('div');
                        btn.id = 'scriptsim-ready-btn';
                        btn.innerHTML = '✅ I am logged in — Start Scan';
                        btn.style.cssText = `
                            position: fixed; bottom: 30px; right: 30px; z-index: 999999;
                            background: #2563eb; color: white; font-size: 15px;
                            font-weight: bold; padding: 14px 22px; border-radius: 10px;
                            cursor: pointer; box-shadow: 0 4px 20px rgba(0,0,0,0.4);
                            font-family: sans-serif;
                        `;
                        btn.onclick = () => {
                            window.__scriptsim_ready = true;
                            btn.innerHTML = '⏳ Capturing session...';
                            btn.style.background = '#16a34a';
                        };
                        document.body.appendChild(btn);
                    }
                """)
            except Exception:
                pass

        page.on("load", lambda: asyncio.ensure_future(inject_button(page)))
        await page.goto(url)
        await inject_button(page)

        print(f"\n{'='*60}")
        print(f"[ScriptSim] Browser opened at: {url}")
        print(f"[ScriptSim] Log in manually, then click the BLUE BUTTON")
        print(f"[ScriptSim] '✅ I am logged in — Start Scan' to continue.")
        print(f"[ScriptSim] Button will turn green when clicked.")
        print(f"[ScriptSim] Waiting up to 3 minutes...")
        print(f"{'='*60}\n")

        # Wait for button click — up to 3 minutes
        for _ in range(90):
            await asyncio.sleep(2)
            try:
                ready = await page.evaluate("window.__scriptsim_ready === true")
                if ready:
                    print(f"[ScriptSim] Login confirmed — capturing session...")
                    break
            except Exception:
                pass
        else:
            print(f"[ScriptSim] 3 min timeout — capturing session as-is...")

        await asyncio.sleep(1)
        storage_state = await context.storage_state()
        await browser.close()
        return storage_state


def trigger_scan_task(
    url: str, email: str, password: str, scan_id: str,
    personas: list[str], scan_mode: str, storage_state: dict = None
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_scan(
            target_url=url,
            login_email=email,
            login_password=password,
            scan_id=scan_id,
            personas=personas,
            scan_mode=scan_mode,
            storage_state=storage_state,
        ))
    except Exception as e:
        print(f"Scan {scan_id} failed: {e}")
    finally:
        loop.close()


async def capture_then_scan(
    url: str, email: str, password: str, scan_id: str,
    personas: list[str], scan_mode: str
):
    try:
        print(f"[ScriptSim] No saved session for {url} — opening browser...")
        storage_state = await capture_session_async(url)
        _captured_sessions[url] = storage_state
        _save_sessions(_captured_sessions)
        cookies_count = len(storage_state.get("cookies", []))
        print(f"[ScriptSim] Session captured ({cookies_count} cookies) — starting scan...")

        thread = threading.Thread(
            target=trigger_scan_task,
            args=(url, email, password, scan_id, personas, scan_mode, storage_state),
            daemon=True,
        )
        thread.start()
    except Exception as e:
        print(f"[ScriptSim] Session capture failed: {e}")


@app.post("/scan", response_model=ScanResponse)
async def create_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if not request.url:
        raise HTTPException(status_code=400, detail="Target URL is required")

    scan_id = str(uuid.uuid4())
    is_demo = request.is_demo or any(port in request.url for port in ["5000", "5001", "5002"]) or "localhost" in request.url or "127.0.0.1" in request.url
    has_credentials = bool(request.email and request.password)

    background_tasks.add_task(
        trigger_scan_task,
        request.url,
        request.email,
        request.password,
        scan_id,
        request.personas,
        request.scan_mode,
        None,
    )
    return ScanResponse(
        scan_id=scan_id,
        status="started",
        message="Scan started.",
    )


@app.get("/session-status")
async def session_status(url: str):
    state = _captured_sessions.get(url)
    return SessionStatusResponse(
        url=url,
        has_session=state is not None,
        cookies_count=len(state.get("cookies", [])) if state else 0,
    )


@app.delete("/session")
async def delete_session(url: str):
    if url in _captured_sessions:
        del _captured_sessions[url]
        _save_sessions(_captured_sessions)
        return {"success": True, "message": f"Session for {url} cleared."}
    return {"success": False, "message": "No session found for that URL."}


@app.get("/health")
async def health_check():
    return {"status": "ok"}