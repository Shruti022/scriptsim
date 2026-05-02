import json
try:
    from tools.browser import get_page, get_default_url
except ImportError:
    from browser import get_page, get_default_url


async def go_back() -> str:
    """Navigate the browser back to the previous page in history.
    Use this instead of clicking a 'Back' button — it always works.
    Returns the new URL after navigating back."""
    try:
        page = await get_page()
        url_before = page.url
        await page.go_back(timeout=3000, wait_until="load")
        # If go_back lands on about:blank (no history), return to the app home page
        if page.url in ("about:blank", "", None):
            fallback = get_default_url()
            if fallback:
                await page.goto(fallback)
                await page.wait_for_load_state("networkidle", timeout=10000)
        return json.dumps({
            "success": True,
            "previous_url": url_before,
            "new_url": page.url,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "current_url": ""})
