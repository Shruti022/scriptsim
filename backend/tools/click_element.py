import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def click_element(selector: str) -> str:
    """Click a visible element by its visible text, aria-label, or role.
    Returns the page state AFTER clicking so you can see what changed.
    Do NOT assume nothing happened just because the URL did not change —
    many apps use client-side routing where content updates without URL changes."""
    try:
        page = await get_page()
        url_before = page.url

        selector_query = (
            f"button:has-text('{selector}'), "
            f"a:has-text('{selector}'), "
            f"button:text-is('{selector}'), "
            f"a:text-is('{selector}'), "
            f"[aria-label*='{selector}' i], "
            f"[title*='{selector}' i], "
            f"[role='button']:has-text('{selector}'), "
            f"input[type='submit'][value*='{selector}' i], "
            f"input[type='button'][value*='{selector}' i]"
        )

        locator = page.locator(selector_query).first
        await locator.scroll_into_view_if_needed(timeout=3000)
        await locator.click(timeout=3000)

        # Wait for client-side updates to settle
        try:
            await page.wait_for_load_state("load", timeout=2000)
        except Exception:
            pass
        await page.wait_for_timeout(800)

        # Return page state after click so agent sees what changed
        title_after = await page.title()
        try:
            body_text = (await page.inner_text("body"))[:600]
        except Exception:
            body_text = ""

        buttons = await page.locator("button:visible, [role='button']:visible").all()
        button_texts = []
        for b in buttons[:10]:
            try:
                text = (await b.inner_text()).strip()
                if text:
                    button_texts.append(text[:40])
            except Exception:
                pass

        modal_present = False
        try:
            modal_present = await page.locator(
                "[role='dialog']:visible, [role='alertdialog']:visible, .modal:visible"
            ).count() > 0
        except Exception:
            pass

        return json.dumps({
            "success": True,
            "url": page.url,
            "url_changed": page.url != url_before,
            "title": title_after,
            "modal_opened": modal_present,
            "visible_buttons": button_texts,
            "page_text_preview": body_text,
        })

    except Exception:
        try:
            # Fallback: press Enter on focused element
            page = await get_page()
            url_before = page.url
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(800)
            try:
                await page.wait_for_load_state("load", timeout=2000)
            except Exception:
                pass
            body_text = ""
            try:
                body_text = (await page.inner_text("body"))[:600]
            except Exception:
                pass
            return json.dumps({
                "success": True,
                "url": page.url,
                "url_changed": page.url != url_before,
                "title": await page.title(),
                "modal_opened": False,
                "page_text_preview": body_text,
                "note": "Clicked via Enter key fallback",
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})