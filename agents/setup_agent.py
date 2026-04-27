from google.adk.agents import LlmAgent
from tools.login import login

setup_agent = LlmAgent(
    name="setup_agent",
    model="gemini-2.5-flash-lite",
    description="Logs in to the target app and saves session cookies for other agents.",
    instruction="""You are a setup agent. Your only job is to log in to the target app.

Steps:
1. Call login with the URL, email, and password provided in the task.
   - url: {target_url}/login
   - email: {login_email}
   - password: {login_password}
2. If login succeeds, output ONLY the raw JSON string from the cookies field.
   Do not add any other text — just the cookies JSON array.
3. If login fails, output: LOGIN_FAILED

Once logged in, simply output: "LOGIN_SUCCESS. Cookies saved." followed by the JSON cookies. Do not add any conversational text about what you can or cannot do.""",

    tools=[login],
    output_key="auth_cookies",
)
