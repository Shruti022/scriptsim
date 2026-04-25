"""
Shared async Playwright browser instance.
All tool functions are async and call get_page() to get the current page.
"""
from playwright.async_api import async_playwright, Page, Browser, Playwright

_playwright: Playwright = None
_browser: Browser = None
_page: Page = None


async def start_browser(url: str = None) -> Page:
    """Start the browser and optionally navigate to a URL."""
    global _playwright, _browser, _page
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
        ]
    )
    _page = await _browser.new_page(viewport={"width": 1280, "height": 800})
    if url:
        await _page.goto(url)
        await _page.wait_for_load_state("networkidle", timeout=10000)
    return _page


async def get_page() -> Page:
    """Get the current browser page. Raises if browser not started."""
    if _page is None:
        raise RuntimeError("Browser not started. Call await start_browser() first.")
    return _page


async def inject_cookies(cookies: list[dict]):
    """Inject auth cookies so agent browses as logged-in user."""
    if _page is None:
        raise RuntimeError("Browser not started.")
    await _page.context.add_cookies(cookies)


async def set_zoom(percent: int):
    """Set browser zoom level. Use 150 for retiree persona."""
    if _page is None:
        raise RuntimeError("Browser not started.")
    await _page.evaluate(f"document.body.style.zoom = '{percent}%'")


async def close_browser():
    """Clean up browser resources."""
    global _browser, _page, _playwright
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _browser = None
    _page = None
    _playwright = None
