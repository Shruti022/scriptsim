"""
Async Playwright browser — named contexts for persona isolation.

SetupAgent runs in the "setup" context. Each persona gets its own named
context pre-loaded with the auth storage state from login.
"""
import asyncio
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright

_playwright: Playwright = None
_browser: Browser = None
_contexts: dict = {}        # name → (BrowserContext, Page)
_default_url: str = None
_default_storage_state: dict = None  # Full storage state (cookies + localStorage)

# Name of the current context — set by orchestrator per agent phase
_current_context_name: str = "default"


def set_context_name(name: str):
    """Set which named context subsequent tool calls should use."""
    global _current_context_name
    _current_context_name = name


def _ctx_name() -> str:
    return _current_context_name


async def _ensure_context(url: str = None) -> Page:
    """Return the Page for the current named context, creating one if needed."""
    name = _ctx_name()
    if name not in _contexts:
        if _default_storage_state:
            context = await _browser.new_context(
                viewport={"width": 1280, "height": 800},
                storage_state=_default_storage_state,
            )
        else:
            context = await _browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()
        # Auto-dismiss alert/confirm/prompt dialogs so JS alerts don't block tool calls
        page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.dismiss()))
        nav_url = url or _default_url
        if nav_url:
            await page.goto(nav_url)
            await page.wait_for_load_state("networkidle", timeout=10000)
        _contexts[name] = (context, page)
    return _contexts[name][1]


async def start_browser(url: str = None) -> Page:
    """Start the shared browser. Call once per scan before running agents."""
    global _playwright, _browser, _default_url, _default_storage_state, _current_context_name
    _default_url = url
    _default_storage_state = None
    _current_context_name = "setup"

    # Close any stale browser from a previous scan.
    if _browser:
        for ctx, _ in list(_contexts.values()):
            try:
                await ctx.close()
            except Exception:
                pass
        _contexts.clear()
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    else:
        _contexts.clear()

    if _playwright is None:
        _playwright = await async_playwright().start()

    _browser = await _playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1280,800"],
    )
    return await _ensure_context(url)


async def get_page() -> Page:
    """Get the Page for the current named context."""
    if _browser is None:
        raise RuntimeError("Browser not started. Call await start_browser() first.")
    return await _ensure_context()


async def inject_storage_state(state: dict):
    """Store full browser storage state (cookies + localStorage) for persona contexts."""
    global _default_storage_state
    _default_storage_state = state


async def inject_cookies(cookies: list[dict]):
    """Inject cookies into the current context AND store for future contexts."""
    name = _ctx_name()
    if name in _contexts:
        context = _contexts[name][0]
        await context.add_cookies(cookies)


async def set_zoom(percent: int):
    """Set browser zoom level. Used for retiree persona (150%)."""
    page = await get_page()
    await page.evaluate(f"document.body.style.zoom = '{percent}%'")


async def close_browser():
    """Close all contexts and the browser. Called after every scan."""
    global _browser, _playwright, _contexts, _default_storage_state, _default_url, _current_context_name
    for context, _ in list(_contexts.values()):
        try:
            await context.close()
        except Exception:
            pass
    _contexts.clear()
    _default_storage_state = None
    _default_url = None
    _current_context_name = "default"
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