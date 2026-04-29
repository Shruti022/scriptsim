# Skill: test-tool

Run this skill to test a single Playwright tool against the demo app.

## Steps
1. Ask me which tool to test (get_page_state, click_element, etc.)
2. Read the tool file at tools/{tool_name}.py
3. Write a standalone test script at tools/test_{tool_name}.py that:
   - Imports the tool function
   - Calls browser.py to start a browser
   - Navigates to the demo app URL
   - Calls the tool with realistic arguments
   - Prints the JSON output
   - Asserts the output is valid JSON
   - Prints PASS or FAIL
4. Run it with: python tools/test_{tool_name}.py
5. Show me the output and whether it passed

## Expected output format
```
Testing get_page_state...
URL: https://demo-app.railway.app
Output: {"url": "...", "title": "...", "buttons": [...]}
✓ Valid JSON
✓ Contains required keys: url, title, buttons, inputs, links
PASS
```
