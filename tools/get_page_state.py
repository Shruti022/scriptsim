import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def get_page_state() -> str:
    """Read the current state of the browser page. Returns URL, title,
    visible buttons, input fields, navigation links, visible text,
    and whether a modal is present. Call this at the start of every turn
    before deciding what action to take."""
    try:
        page = await get_page()

        buttons = await page.locator("button:visible, [role='button']:visible").all()
        button_texts = []
        for b in buttons[:15]:
            try:
                text = (await b.inner_text()).strip()
                if text:
                    button_texts.append(text[:50])
            except Exception:
                pass

        inputs = await page.locator(
            "input:visible, textarea:visible, [role='textbox']:visible"
        ).all()
        input_list = []
        for inp in inputs[:10]:
            try:
                input_list.append({
                    "placeholder": await inp.get_attribute("placeholder") or "",
                    "type": await inp.get_attribute("type") or "text",
                    "aria_label": await inp.get_attribute("aria-label") or "",
                })
            except Exception:
                pass

        links = await page.locator("a:visible").all()
        link_list = []
        for l in links[:20]:
            try:
                text = (await l.inner_text()).strip()[:40]
                href = await l.get_attribute("href") or ""
                if text:
                    link_list.append({"text": text, "href": href})
            except Exception:
                pass

        try:
            body_text = (await page.inner_text("body"))[:800]
        except Exception:
            body_text = ""

        try:
            modal_present = await page.locator(
                "[role='dialog']:visible, [role='alertdialog']:visible, "
                ".modal:visible, #modal:visible"
            ).count() > 0
        except Exception:
            modal_present = False

        try:
            errors = await page.locator(
                "[role='alert']:visible, .error:visible, .error-message:visible"
            ).all_inner_texts()
            errors = errors[:3]
        except Exception:
            errors = []

        return json.dumps({
            "url": page.url,
            "title": await page.title(),
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
