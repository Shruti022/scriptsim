from google.adk.agents import LlmAgent
from schemas.bug_report import DeduplicatedBugList

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

Title & Description Rule:
- The "title" MUST be a short, punchy summary of the bug (max 80 chars). DO NOT copy the description here.
- The "description" MUST be a full detailed impact and context.

Fill out the DeduplicatedBugList schema with the final merged bugs."""

    return LlmAgent(
        name="synthesis_agent",
        model="gemini-2.5-flash",
        description="Deduplicates and cross-scores bugs found by personas.",
        instruction=instruction,
        output_schema=DeduplicatedBugList,
        output_key="deduplicated_bugs",
    )
