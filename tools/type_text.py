import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


def type_text(selector: str, text: str, clear_first: bool = True) -> str:
    """Type text into an input field. Identify the field by its placeholder text,
    aria-label, or label text (e.g. 'Search', 'Email address', 'Password').
    Set clear_first=True to erase existing content before typing."""
    try:
        page = get_page()

        locator = page.locator(
            f"input[placeholder*='{selector}' i], "
            f"input[aria-label*='{selector}' i], "
            f"textarea[placeholder*='{selector}' i], "
            f"textarea[aria-label*='{selector}' i], "
            f"[role='textbox'][aria-label*='{selector}' i]"
        ).first

        if clear_first:
            locator.clear()
        locator.fill(text)

        return json.dumps({"success": True, "typed": text})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


if __name__ == "__main__":
    import sys
    try:
        from tools.browser import start_browser, close_browser
    except ImportError:
        from browser import start_browser, close_browser

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    selector = sys.argv[2] if len(sys.argv) > 2 else "Search"
    text = sys.argv[3] if len(sys.argv) > 3 else "hello"
    start_browser(url)
    print(type_text(selector, text))
    close_browser()
