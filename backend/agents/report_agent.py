from google.adk.agents import LlmAgent
from schemas.bug_report import BugReportList


def make_report_agent(persona: str) -> LlmAgent:
    """Create a ReportAgent for the given persona.
    Agent has output_schema=BugReportList and NO tools (ADK constraint)."""
    return LlmAgent(
        name=f"report_{persona}",
        model="gemini-2.5-flash",
        description=f"Converts the {persona} persona action log into structured BugReport objects.",
        instruction=f"""You are a QA analyst reading a bug-hunting session log from the "{persona}" persona.

Action log from the {persona} persona:
{{{f"action_log_{persona}"}}}

Your task:
1. Read the action log carefully.
2. Identify ALL bugs mentioned in the log — do not skip any.
3. Fill out the BugReportList schema with one BugReport per bug found.
4. If no bugs were found, return an empty bugs list.

Title & Description Rule:
- The "title" MUST be a short, distinct summary (max 80 chars).
- The "description" MUST contain the full details.
- DO NOT use the same text for both.

Severity guide:
- 1 = cosmetic (wrong colour, typo)
- 2 = minor (confusing but workable)
- 3 = moderate (feature partially broken)
- 4 = major (feature completely broken, data loss risk)
- 5 = critical (security vulnerability, crash, payment failure)

Be precise and factual. Do not invent bugs not mentioned in the log.
steps_to_reproduce must be actionable numbered steps.""",
        output_schema=BugReportList,
        output_key=f"bug_report_{persona}",
        # NO tools — ADK constraint: output_schema and tools are mutually exclusive
    )
