import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def type_text(selector: str, text: str, clear_first: bool = True) -> str:
    """Type text into an input field. Identify the field by its placeholder text,
    aria-label, or label text (e.g. 'Search', 'Email address', 'Password').
    Set clear_first=True to erase existing content before typing."""
    try:
        page = await get_page()
        # Smart selector that looks for the field by:
        # 1. Direct placeholder/aria-label match
        # 2. Associated label text (via 'has-text')
        # 3. Nearby heading or label that might precede the input
        locator = page.locator(
            f"input[placeholder*='{selector}' i], "
            f"input[aria-label*='{selector}' i], "
            f"input[name*='{selector}' i], "
            f"textarea[placeholder*='{selector}' i], "
            f"textarea[aria-label*='{selector}' i], "
            f"label:has-text('{selector}') + input, "
            f"label:has-text('{selector}') input, "
            f"div:has-text('{selector}') + input, "
            f"p:has-text('{selector}') + input"
        ).first
        
        # Increase visibility check and wait time
        await locator.scroll_into_view_if_needed()
        if clear_first:
            await locator.clear(timeout=5000)
        await locator.fill(text, timeout=5000)
        return json.dumps({"success": True, "typed": text})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
