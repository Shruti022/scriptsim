from google.adk.agents import LlmAgent
from schemas.bug_report import FinalReport


def make_eval_agent() -> LlmAgent:
    return LlmAgent(
        name="eval_agent",
        model="gemini-2.5-flash",
        description="Assigns final severity scores and produces the ranked bug report.",
        instruction="""You are a principal QA engineer doing final evaluation of a bug report.

Deduplicated bug list:
{deduplicated_bugs}

Your tasks:
1. Re-evaluate every bug's severity using this rubric:
   - 5 CRITICAL: Security hole, data loss, payment failure, complete feature crash
   - 4 MAJOR: Core feature broken for most users, no workaround
   - 3 MODERATE: Feature degraded, workaround exists
   - 2 MINOR: Confusing UX but nothing is broken
   - 1 COSMETIC: Visual issues, typos, minor phrasing

2. Sort bugs from highest severity to lowest.

3. Fill out the FinalReport schema with the final ranked report.
Ensure each bug has a concise 'title' and a full 'description'.""",
        output_schema=FinalReport,
        output_key="final_report",
    )