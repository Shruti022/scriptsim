"""
Shared Playwright browser instance.
All tool functions call get_page() to get the current page.
This module manages one browser and one page per container.
"""
from playwright.sync_api import sync_playwright, Page, Browser

_browser: Browser = None
_page: Page = None
_playwright = None


def start_browser(url: str = None):
    """Start the browser and optionally navigate to a URL.
    Call this once at the start of each persona scan."""
    global _browser, _page, _playwright

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,800",
        ]
    )
    _page = _browser.new_page(viewport={"width": 1280, "height": 800})

    if url:
        _page.goto(url)
        _page.wait_for_load_state("networkidle", timeout=10000)

    return _page


def get_page() -> Page:
    """Get the current browser page. Raises if browser not started."""
    if _page is None:
        raise RuntimeError("Browser not started. Call start_browser() first.")
    return _page


def inject_cookies(cookies: list[dict]):
    """Inject auth cookies so agent browses as logged-in user."""
    if _page is None:
        raise RuntimeError("Browser not started.")
    _page.context.add_cookies(cookies)


def set_zoom(percent: int):
    """Set browser zoom level. Use 150 for elderly retiree, 200 for grandma."""
    if _page is None:
        raise RuntimeError("Browser not started.")
    _page.evaluate(f"document.body.style.zoom = '{percent}%'")


def close_browser():
    """Clean up browser resources."""
    global _browser, _page, _playwright
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = None
    _page = None
    _playwright = None
