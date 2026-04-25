import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


def hover_element(selector: str) -> str:
    """Hover over a visible element to reveal tooltips, dropdown menus, or
    hidden controls. Identify by visible text or aria-label.
    Returns the visible text that appeared after hovering."""
    try:
        page = get_page()

        page.hover(f"text={selector}", timeout=3000)
        page.wait_for_timeout(500)  # let hover effects render

        # Capture any newly visible tooltip or popover text
        try:
            tooltip_text = page.locator(
                "[role='tooltip']:visible, [data-tooltip]:visible, "
                ".tooltip:visible, .popover:visible"
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


if __name__ == "__main__":
    import sys
    try:
        from tools.browser import start_browser, close_browser
    except ImportError:
        from browser import start_browser, close_browser

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    selector = sys.argv[2] if len(sys.argv) > 2 else "More information"
    start_browser(url)
    print(hover_element(selector))
    close_browser()
