import json
try:
    from tools.browser import get_page
except ImportError:
    from browser import get_page


def login(url: str, email: str, password: str) -> str:
    """Navigate to a login page, fill credentials, and submit the form.
    Returns session cookies on success — SetupAgent saves these to Firestore
    so other persona agents can inject them via inject_cookies().
    Call start_browser() before this."""
    try:
        page = get_page()

        page.goto(url)
        page.wait_for_load_state("networkidle", timeout=10000)

        # Fill email field
        page.locator(
            "input[type='email'], input[name='email'], "
            "input[placeholder*='email' i], input[id*='email' i]"
        ).first.fill(email)

        # Fill password field
        page.locator("input[type='password']").first.fill(password)

        # Submit
        page.locator(
            "button[type='submit'], input[type='submit'], "
            "button:has-text('Log in'), button:has-text('Login'), "
            "button:has-text('Sign in')"
        ).first.click()
        page.wait_for_load_state("networkidle", timeout=10000)

        cookies = page.context.cookies()

        return json.dumps({
            "success": True,
            "current_url": page.url,
            "cookies": cookies,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "cookies": []})


if __name__ == "__main__":
    import sys
    try:
        from tools.browser import start_browser, close_browser
    except ImportError:
        from browser import start_browser, close_browser

    login_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000/login"
    email = sys.argv[2] if len(sys.argv) > 2 else "test@scriptsim.com"
    password = sys.argv[3] if len(sys.argv) > 3 else "TestPass123!"

    start_browser()
    result = login(login_url, email, password)
    parsed = json.loads(result)
    print(f"Success: {parsed['success']}")
    print(f"Current URL: {parsed.get('current_url', 'N/A')}")
    print(f"Cookies: {len(parsed.get('cookies', []))} cookies set")
    close_browser()
