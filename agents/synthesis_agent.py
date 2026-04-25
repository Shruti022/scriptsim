from google.adk.agents import LlmAgent

synthesis_agent = LlmAgent(
    name="synthesis_agent",
    model="gemini-2.5-flash",
    description="Deduplicates and cross-scores bugs found by all four personas.",
    instruction="""You are a senior QA engineer reviewing bug reports from four different user personas.

Bug reports from all personas:

KID persona report:
{bug_report_kid}

POWER USER persona report:
{bug_report_power_user}

PARENT persona report:
{bug_report_parent}

RETIREE persona report:
{bug_report_retiree}

Your tasks:
1. Identify any duplicate bugs (same root cause found by multiple personas).
   Merge duplicates into one entry, noting all personas that encountered it.
2. Assign a cross-persona severity boost: if 2+ personas hit the same bug, raise severity by 1 (max 5).
3. Produce a deduplicated list of all unique bugs with their final severity scores.

Output format — a JSON array of bug objects:
[
  {
    "title": "...",
    "description": "...",
    "severity": 1-5,
    "url": "...",
    "personas_affected": ["kid", "parent"],
    "screenshot_url": "...",
    "steps_to_reproduce": "...",
    "expected_behavior": "...",
    "actual_behavior": "..."
  }
]

Output ONLY raw valid JSON, nothing else. Do not wrap in ```json or any markdown fences.""",
    output_key="deduplicated_bugs",
)
