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
        
        # Comprehensive selector strategy:
        # 1. Exact/partial text match on buttons, links, or inputs
        # 2. Aria-label match
        # 3. Role-based text match
        # 4. Title attribute
        selector_query = (
            f"button:has-text('{selector}'), "
            f"a:has-text('{selector}'), "
            f"text='{selector}', "
            f"[aria-label*='{selector}' i], "
            f"[title*='{selector}' i], "
            f"[role='button']:has-text('{selector}'), "
            f"input[type='submit'][value*='{selector}' i], "
            f"input[type='button'][value*='{selector}' i]"
        )
        
        locator = page.locator(selector_query).first
        await locator.scroll_into_view_if_needed()
        await locator.click(timeout=5000)
        
        # Wait for potential navigation
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except:
            pass

        return json.dumps({
            "success": True,
            "url_changed": page.url != url_before,
            "new_url": page.url,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

