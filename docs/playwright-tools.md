---
paths:
- "tools/*.py"
- "tools/**/*.py"
---
# Playwright Tool Rules

Every function in tools/ is a Google ADK tool that PersonaAgent calls.
Follow these rules exactly or the agent loop will break.

## Function signature pattern
Every tool must be a regular Python function (not async) that:
1. Takes simple typed parameters (str, int, bool only)
2. Returns a JSON string (not a dict, not None, always a string)
3. Has a docstring — ADK uses this as the tool description for the LLM
4. Wraps everything in try/except and returns error as JSON string

## Correct pattern
```python
def click_element(selector: str) -> str:
    """Click a visible element. Use button text or aria-label.
    Returns success status and whether the page changed."""
    try:
        page = get_page()
        url_before = page.url
        page.click(f"text={selector}", timeout=3000)
        page.wait_for_load_state("networkidle", timeout=5000)
        return json.dumps({
            "success": True,
            "url_changed": page.url != url_before,
            "new_url": page.url
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
```

## Wrong patterns (never do these)
- async def — tools must be sync
- return None — must return JSON string
- raise exceptions — catch everything, return error JSON
- import playwright inside the function — use the browser singleton

## Browser singleton
All tools use the shared browser instance from tools/browser.py.
Never create a new browser inside a tool function.
Call get_page() to get the current page object.

## Selector strategy (in order of preference)
1. text= selector: page.click("text=Submit")
2. aria-label: page.click("[aria-label='Like']")
3. role: page.click("button[role='button']:has-text('Post')")
4. CSS as last resort: page.click("button.submit-btn")

## After every navigation
Always call: page.wait_for_load_state("networkidle", timeout=5000)
