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
        locator = page.locator(
            f"input[placeholder*='{selector}' i], "
            f"input[aria-label*='{selector}' i], "
            f"textarea[placeholder*='{selector}' i], "
            f"textarea[aria-label*='{selector}' i], "
            f"[role='textbox'][aria-label*='{selector}' i]"
        ).first
        if clear_first:
            await locator.clear()
        await locator.fill(text)
        return json.dumps({"success": True, "typed": text})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
