from google.adk.agents import LlmAgent
from schemas.bug_report import BugReport


def make_report_agent(persona: str) -> LlmAgent:
    """Create a ReportAgent for the given persona.
    Agent has output_schema=BugReport and NO tools (ADK constraint)."""
    return LlmAgent(
        name=f"report_{persona}",
        model="gemini-2.5-flash",
        description=f"Converts the {persona} persona action log into structured BugReport objects.",
        instruction=f"""You are a QA analyst reading a bug-hunting session log from the "{persona}" persona.

Action log from the {persona} persona:
{{{f"action_log_{persona}"}}}

Your task:
1. Read the action log carefully.
2. Identify the single MOST IMPORTANT bug described in the log.
3. Fill out the BugReport schema completely for that bug.

Severity guide:
- 1 = cosmetic (wrong colour, typo)
- 2 = minor (confusing but workable)
- 3 = moderate (feature partially broken)
- 4 = major (feature completely broken, data loss risk)
- 5 = critical (security vulnerability, crash, payment failure)

Be precise and factual. Do not invent bugs not mentioned in the log.
The steps_to_reproduce must be actionable numbered steps.""",
        output_schema=BugReport,
        output_key=f"bug_report_{persona}",
        # NO tools — ADK constraint: output_schema and tools are mutually exclusive
    )
