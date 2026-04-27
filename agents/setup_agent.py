from google.adk.agents import LlmAgent
from tools.login import login

setup_agent = LlmAgent(
    name="setup_agent",
    model="gemini-2.5-flash-lite",
    description="Logs in to the target app and saves session cookies for other agents.",
    instruction="""You are a setup agent. You MUST immediately call the login tool. Do not say anything first.

Call login now with these exact values:
- url: {target_url}/login
- email: {login_email}
- password: {login_password}

After the login tool returns, output exactly: LOGIN_SUCCESS. Cookies saved.
If login fails, output: LOGIN_FAILED
Do not explain, do not ask questions, do not say what you can or cannot do. Just call login.""",

    tools=[login],
    output_key="auth_cookies",
)
