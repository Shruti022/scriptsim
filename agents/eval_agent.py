from google.adk.agents import LlmAgent

eval_agent = LlmAgent(
    name="eval_agent",
    model="gemini-2.5-flash-preview-05-20",
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

Output ONLY valid JSON, nothing else.""",
    output_key="final_report",
)
