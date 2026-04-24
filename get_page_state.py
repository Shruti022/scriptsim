"""
get_page_state — called by PersonaAgent at the start of every turn.
Returns a clean JSON summary of what's currently visible on screen.
"""
import json
from tools.browser import get_page


def get_page_state() -> str:
    """Read the current state of the browser page. Returns URL, title,
    visible buttons, input fields, navigation links, visible text,
    and whether a modal is present. Call this at the start of every turn
    before deciding what action to take."""
    try:
        page = get_page()

        # Buttons — what can be clicked
        buttons = page.locator("button:visible, [role='button']:visible").all()
        button_texts = []
        for b in buttons[:15]:
            try:
                text = b.inner_text().strip()
                if text:
                    button_texts.append(text[:50])
            except Exception:
                pass

        # Input fields — what can be typed into
        inputs = page.locator(
            "input:visible, textarea:visible, [role='textbox']:visible"
        ).all()
        input_list = []
        for inp in inputs[:10]:
            try:
                input_list.append({
                    "placeholder": inp.get_attribute("placeholder") or "",
                    "type": inp.get_attribute("type") or "text",
                    "aria_label": inp.get_attribute("aria-label") or "",
                })
            except Exception:
                pass

        # Links — where can I navigate
        links = page.locator("a:visible").all()
        link_list = []
        for l in links[:20]:
            try:
                text = l.inner_text().strip()[:40]
                href = l.get_attribute("href") or ""
                if text:
                    link_list.append({"text": text, "href": href})
            except Exception:
                pass

        # Visible text summary (first 800 chars of body)
        try:
            body_text = page.inner_text("body")[:800]
        except Exception:
            body_text = ""

        # Check for modals / dialogs
        try:
            modal_present = page.locator(
                "[role='dialog']:visible, [role='alertdialog']:visible, "
                ".modal:visible, #modal:visible"
            ).count() > 0
        except Exception:
            modal_present = False

        # Check for error messages
        try:
            errors = page.locator(
                "[role='alert']:visible, .error:visible, "
                ".error-message:visible"
            ).all_inner_texts()[:3]
        except Exception:
            errors = []

        return json.dumps({
            "url": page.url,
            "title": page.title(),
            "buttons": button_texts,
            "inputs": input_list,
            "links": link_list,
            "text_summary": body_text,
            "modal_present": modal_present,
            "error_messages": errors,
        })

    except Exception as e:
        return json.dumps({
            "error": str(e),
            "url": "unknown",
            "title": "unknown",
            "buttons": [],
            "inputs": [],
            "links": [],
            "text_summary": "",
            "modal_present": False,
            "error_messages": [],
        })


if __name__ == "__main__":
    # Quick test — run: python tools/get_page_state.py
    import sys
    from tools.browser import start_browser, close_browser

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(f"Testing get_page_state on {url}...")

    start_browser(url)
    result = get_page_state()
    parsed = json.loads(result)

    print(f"URL: {parsed['url']}")
    print(f"Title: {parsed['title']}")
    print(f"Buttons: {parsed['buttons']}")
    print(f"Inputs: {[i['placeholder'] for i in parsed['inputs']]}")
    print(f"Links: {[l['text'] for l in parsed['links'][:5]]}")
    print(f"Modal: {parsed['modal_present']}")
    print("\nFull JSON:")
    print(json.dumps(parsed, indent=2))

    close_browser()
    print("\nPASS" if "error" not in parsed else "FAIL")
