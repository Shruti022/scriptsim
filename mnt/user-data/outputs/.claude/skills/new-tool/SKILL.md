# Skill: new-tool

Scaffold a new Playwright tool function following ScriptSim conventions.

## Steps
1. Ask me: what is the tool name and what should it do?
2. Create tools/{tool_name}.py with:
   - Correct sync function signature
   - Docstring explaining what it does (this becomes the ADK tool description)
   - try/except wrapping everything
   - JSON string return value
   - Uses get_page() from tools/browser.py
3. Add the function to tools/__init__.py exports
4. Show me the file and ask if I want to test it with /test-tool
