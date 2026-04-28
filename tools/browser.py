"""
Async Playwright browser — per-task isolated contexts.

Each asyncio Task (i.e. each parallel persona) gets its own BrowserContext
and Page, so personas cannot interfere with each other. SetupAgent's login
call stores cookies globally so every new context starts logged-in.
"""
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright

_playwright: Playwright = None
_browser: Browser = None
_contexts: dict = {}        # task_id → (BrowserContext, Page)
_default_url: str = None
_default_cookies: list = []
_default_storage_state: dict = None  # Full storage state (cookies + localStorage)


def _task_id() -> int:
    task = asyncio.current_task()
    return id(task) if task else 0


async def _ensure_context(url: str = None) -> Page:
    """Return the Page for the current task, creating one if needed."""
    tid = _task_id()
    if tid not in _contexts:
        if _default_storage_state:
            context = await _browser.new_context(
                viewport={"width": 1280, "height": 800},
                storage_state=_default_storage_state,
            )
        else:
            context = await _browser.new_context(viewport={"width": 1280, "height": 800})
            if _default_cookies:
                await context.add_cookies(_default_cookies)
        page = await context.new_page()
        nav_url = url or _default_url
        if nav_url:
            await page.goto(nav_url)
            await page.wait_for_load_state("networkidle", timeout=10000)
        _contexts[tid] = (context, page)
    return _contexts[tid][1]


async def start_browser(url: str = None) -> Page:
    """Start the shared browser and create a context for the current task."""
    global _playwright, _browser, _default_url, _default_cookies, _default_storage_state
    _default_url = url
    _default_cookies = []
    _default_storage_state = None
    # Close any stale browser from a previous scan
    if _browser:
        try:
            for ctx, _ in list(_contexts.values()):
                await ctx.close()
            _contexts.clear()
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is None:
        _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1280,800"],
    )
    return await _ensure_context(url)


async def get_page() -> Page:
    """Get the Page for the current task. Auto-creates an isolated context if needed."""
    if _browser is None:
        raise RuntimeError("Browser not started. Call await start_browser() first.")
    return await _ensure_context()


async def inject_storage_state(state: dict):
    """Store full browser storage state (cookies + localStorage) for persona contexts.
    Called by login.py after a successful login. Works for cookie-based AND
    localStorage-based auth (SPAs like saucedemo.com)."""
    global _default_storage_state, _default_cookies
    _default_storage_state = state
    if state and "cookies" in state:
        _default_cookies = state["cookies"]


async def inject_cookies(cookies: list[dict]):
    """Inject cookies into the current context AND store them for future contexts.
    Called by login.py after a successful login so all persona contexts start logged in."""
    global _default_cookies
    _default_cookies = list(cookies)
    tid = _task_id()
    if tid in _contexts:
        context = _contexts[tid][0]
        await context.add_cookies(cookies)


async def set_zoom(percent: int):
    """Set browser zoom level. Used for retiree persona (150%)."""
    page = await get_page()
    await page.evaluate(f"document.body.style.zoom = '{percent}%'")


async def close_browser():
    """Close all contexts and the browser. Called after every scan."""
    global _browser, _playwright, _contexts, _default_cookies, _default_url, _default_storage_state
    for context, _ in list(_contexts.values()):
        try:
            await context.close()
        except Exception:
            pass
    _contexts.clear()
    _default_cookies = []
    _default_storage_state = None
    _default_url = None
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
    if _playwright:
        try:
            await _playwright.stop()
        except Exception:
            pass
    _browser = None
    _playwright = None
