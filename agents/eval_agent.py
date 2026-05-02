from google.adk.agents import LlmAgent


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

3. Output the final ranked report as a JSON object:
{
  "scan_summary": "One paragraph summary of the overall product quality",
  "total_bugs": <number>,
  "critical_count": <number>,
  "major_count": <number>,
  "bugs": [
    {
      "rank": 1,
      "title": "...",
      "severity": 5,
      "severity_label": "CRITICAL",
      "url": "...",
      "personas_affected": ["kid", "power_user"],
      "description": "...",
      "steps_to_reproduce": "...",
      "expected_behavior": "...",
      "actual_behavior": "...",
      "screenshot_url": "..."
    }
  ]
}

CRITICAL OUTPUT RULE: your entire response must be only the JSON object above.
The first character of your response must be { and the last must be }.
Do not write any text before or after the JSON.
Do not use ```json, ```, or any markdown formatting whatsoever.""",
        output_key="final_report",
    )