import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def click_element(selector: str) -> str:
    """Click a visible element by its visible text, aria-label, or role.
    Prefer button text (e.g. 'Add to Cart') over CSS selectors.
    Returns success status and whether the page URL changed."""
    try:
        page = await get_page()
        url_before = page.url
        
        # Try 1: Exact or partial text match (Playwright's 'text=' is smart)
        try:
            await page.click(f"text={selector}", timeout=3000)
        except Exception:
            # Try 2: Case-insensitive 'has-text' which is more flexible for partials
            await page.wait_for_load_state("load", timeout=3000)

        await page.wait_for_load_state("networkidle", timeout=5000)
        return json.dumps({
            "success": True,
            "url_changed": page.url != url_before,
            "new_url": page.url,
        })
    except Exception:
        try:
            page = await get_page()
            url_before = page.url
            # Try 3: Aria-label match (escape single quotes)
            escaped = selector.replace("'", "\\'")
            await page.click(f"[aria-label*='{escaped}' i]", timeout=3000)
            await page.wait_for_load_state("load", timeout=3000)
            return json.dumps({
                "success": True,
                "url_changed": page.url != url_before,
                "new_url": page.url,
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

