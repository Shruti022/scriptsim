import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


async def login(url: str, email: str, password: str) -> str:
    """Navigate to a login page, fill credentials, and submit the form.
    Returns session cookies on success — SetupAgent saves these to Firestore."""
    try:
        page = await get_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle", timeout=10000)

        await page.locator(
            "input[type='email'], input[name='email'], "
            "input[placeholder*='email' i], input[id*='email' i]"
        ).first.fill(email)

        await page.locator("input[type='password']").first.fill(password)

        await page.locator(
            "button[type='submit'], input[type='submit'], "
            "button:has-text('Log in'), button:has-text('Login'), "
            "button:has-text('Sign in')"
        ).first.click()
        await page.wait_for_load_state("networkidle", timeout=10000)

        cookies = await page.context.cookies()
        return json.dumps({
            "success": True,
            "current_url": page.url,
            "cookies": cookies,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "cookies": []})
