import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def type_text(selector: str, text: str, clear_first: bool = True) -> str:
    """Type text into an input field. Identify the field by its placeholder text,
    aria-label, or label text (e.g. 'Search', 'Email address', 'Password').
    Handles standard inputs, textareas, contenteditable divs, and rich text editors.
    Set clear_first=True to erase existing content before typing."""
    try:
        page = await get_page()

        locator = page.locator(
            f"input[placeholder*='{selector}' i], "
            f"input[aria-label*='{selector}' i], "
            f"input[name*='{selector}' i], "
            f"textarea[placeholder*='{selector}' i], "
            f"textarea[aria-label*='{selector}' i], "
            f"[contenteditable='true'][aria-label*='{selector}' i], "
            f"[role='textbox'][aria-label*='{selector}' i], "
            f"[contenteditable='true'][placeholder*='{selector}' i], "
            f"label:has-text('{selector}') + input, "
            f"label:has-text('{selector}') input, "
            f"label:has-text('{selector}') + textarea, "
            f"label:has-text('{selector}') textarea, "
            f"label:has-text('{selector}') [contenteditable='true'], "
            f"label:has-text('{selector}') [role='textbox'], "
            f"div:has-text('{selector}') + input, "
            f"p:has-text('{selector}') + input"
        ).first

        await locator.scroll_into_view_if_needed(timeout=3000)

        try:
            # Standard approach — works for input, textarea
            if clear_first:
                await locator.clear(timeout=3000)
            await locator.fill(text, timeout=3000)
            return json.dumps({"success": True, "typed": text})
        except Exception:
            # Fallback — click the element then keyboard type
            # Works for rich text editors (ProseMirror, Slate, Quill, contenteditable)
            try:
                await locator.click(timeout=3000)
                if clear_first:
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                await page.keyboard.type(text, delay=20)
                return json.dumps({"success": True, "typed": text, "method": "keyboard"})
            except Exception as e2:
                # Last resort — find any visible focused element and type into it
                try:
                    await page.click(f"text={selector}", timeout=2000)
                    await page.wait_for_timeout(300)
                    if clear_first:
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Delete")
                    await page.keyboard.type(text, delay=20)
                    return json.dumps({"success": True, "typed": text, "method": "text-click-keyboard"})
                except Exception as e3:
                    return json.dumps({"success": False, "error": str(e3)})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})