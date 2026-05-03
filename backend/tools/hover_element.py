import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def hover_element(selector: str) -> str:
    """Hover over a visible element to reveal tooltips, dropdown menus, or
    hidden controls. Identify by visible text or aria-label.
    Returns any tooltip text that appeared after hovering."""
    try:
        page = await get_page()
        await page.hover(f"text={selector}", timeout=3000)
        await page.wait_for_timeout(500)
        try:
            tooltip_text = await page.locator(
                "[role='tooltip']:visible, .tooltip:visible, .popover:visible"
            ).first.inner_text()
        except Exception:
            tooltip_text = ""
        return json.dumps({
            "success": True,
            "hovered": selector,
            "tooltip_text": tooltip_text,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
