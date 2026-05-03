import json
try:
    from tools.browser import get_page, inject_cookies, inject_storage_state
except ImportError:
    from browser import get_page, inject_cookies, inject_storage_state


async def login(url: str, email: str, password: str) -> str:
    """Navigate to a login page, fill credentials, and submit the form.
    On success, stores cookies globally so every parallel persona context
    starts logged in automatically."""
    try:
        page = await get_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle", timeout=10000)

        await page.locator(
            "input[type='email'], input[name='email'], input[name='username'], "
            "input[name='user-name'], input[placeholder*='email' i], "
            "input[id*='email' i], input[placeholder*='username' i], "
            "input[placeholder*='user' i]"
        ).first.fill(email)

        await page.locator("input[type='password']").first.fill(password)

        await page.locator(
            "button[type='submit'], input[type='submit'], "
            "button:has-text('Log in'), button:has-text('Login'), "
            "button:has-text('Sign in')"
        ).first.click()
        await page.wait_for_load_state("networkidle", timeout=10000)

        cookies = await page.context.cookies()

        # Capture full storage state (cookies + localStorage) so persona contexts
        # start authenticated on ANY site, including SPAs that use localStorage.
        storage_state = await page.context.storage_state()
        await inject_storage_state(storage_state)

        # Legacy cookie injection kept for backward compatibility
        await inject_cookies(cookies)

        return json.dumps({
            "success": True,
            "current_url": page.url,
            "cookies": cookies,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "cookies": []})
