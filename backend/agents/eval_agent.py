from google.adk.agents import LlmAgent
from schemas.bug_report import FinalReport


def make_eval_agent() -> LlmAgent:
    return LlmAgent(
        name="eval_agent",
        model="gemini-2.5-flash",
        description="Assigns final severity scores and produces the ranked bug report.",
        instruction="""You are a principal QA engineer and Behavioral Accessibility Analyst.
        
Your tasks:
1. Re-evaluate every bug's severity (1-5) and provide a concise 'title' and 'description'.
2. Sort bugs from highest severity to lowest (rank them).
3. Analyze the persona action logs in the session state to calculate behavioral metrics:
   - time_on_task_seconds: Use the deterministic values provided in the 'persona_durations' session state (e.g., {persona_durations}). If missing, provide a best estimate.
   - total_actions: Count the total number of distinct actions performed.
   - friction_score: (1-10) How much did they struggle? 
     * 1-3 (Seamless): Linear path, no backtracking, goal achieved quickly.
     * 4-6 (Clunky): Minor backtracking, one or two redundant clicks, hesitant path.
     * 7-10 (High Friction): Major loops, 50%+ time spent correcting mistakes, getting stuck in dead-ends.
   - confusion_areas: Provide descriptive strings of what exactly went wrong and why the agent struggled (e.g., 'Retried search button 3 times' or 'Stuck on login form due to missing labels'). DO NOT include URLs in these strings.
4. Fill out the FinalReport schema with the final ranked report and the 'metrics' list for all personas.""",
        output_schema=FinalReport,
        output_key="final_report",
    )