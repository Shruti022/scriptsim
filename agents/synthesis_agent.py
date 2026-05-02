from google.adk.agents import LlmAgent

def make_synthesis_agent(personas: list[str]) -> LlmAgent:
    persona_reports = "\n\n".join(
        f"{p.upper()} persona bugs (JSON object with a 'bugs' array — each item is one bug):\n{{bug_report_{p}}}" for p in personas
    )

    instruction = f"""You are a senior QA engineer reviewing bug reports from different user personas.

Each persona report below is a JSON object with a "bugs" array. Extract every bug from every persona's list.

{persona_reports}

Your tasks:
1. Collect ALL bugs from ALL personas — do not drop any.
2. Identify duplicates: bugs with the same root cause found by multiple personas.
   Merge duplicates into one entry listing all personas that encountered it.
3. Cross-persona severity boost: if 2+ personas hit the same bug, raise severity by 1 (max 5).
4. Produce a deduplicated list of ALL unique bugs with their final severity scores.

Output format — a JSON array of bug objects:
[
  {{
    "title": "...",
    "description": "...",
    "severity": 1-5,
    "url": "...",
    "personas_affected": ["kid", "parent"],
    "screenshot_url": "...",
    "steps_to_reproduce": "...",
    "expected_behavior": "...",
    "actual_behavior": "..."
  }}
]

CRITICAL OUTPUT RULE: your entire response must be only the JSON array above.
The first character of your response must be [ and the last must be ].
Do not write any text before or after the JSON.
Do not use ```json, ```, or any markdown formatting whatsoever."""

    return LlmAgent(
        name="synthesis_agent",
        model="gemini-2.5-flash",
        description="Deduplicates and cross-scores bugs found by personas.",
        instruction=instruction,
        output_key="deduplicated_bugs",
    )
