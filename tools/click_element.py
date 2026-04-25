import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


def click_element(selector: str) -> str:
    """Click a visible element by its visible text, aria-label, or role.
    Prefer button text (e.g. 'Add to Cart') over CSS selectors.
    Returns success status and whether the page URL changed."""
    try:
        page = get_page()
        url_before = page.url

        page.click(f"text={selector}", timeout=3000)
        page.wait_for_load_state("networkidle", timeout=5000)

        return json.dumps({
            "success": True,
            "url_changed": page.url != url_before,
            "new_url": page.url,
        })
    except Exception:
        # Fall back to aria-label match
        try:
            page = get_page()
            url_before = page.url
            page.click(f"[aria-label='{selector}']", timeout=3000)
            page.wait_for_load_state("networkidle", timeout=5000)
            return json.dumps({
                "success": True,
                "url_changed": page.url != url_before,
                "new_url": page.url,
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
    print(click_element(selector))
    close_browser()
