from google.adk.agents import LlmAgent
from tools.get_page_state import get_page_state
from tools.click_element import click_element
from tools.go_back import go_back

mapper_agent = LlmAgent(
    name="mapper_agent",
    model="gemini-2.5-flash-lite",
    description="Crawls the target app and builds a feature map of all discoverable pages and actions.",
    instruction="""You are a site mapper. Your job is to crawl the target web app and produce a
feature map listing every distinct page, feature, and interactive element you can find.

The browser is already open and logged in at the target URL.

Process:
1. Call get_page_state to see the current page.
2. Click every link and button you can find (one at a time).
3. After each click call get_page_state to record the new page.
4. Call go_back to return to the previous page before trying the next link.
5. Do not re-visit URLs you have already seen.
6. Explore for a maximum of 30 actions total.

Output a JSON object with this exact structure — raw JSON only, no markdown fences:
{
  "pages": [
    {"url": "...", "title": "...", "key_actions": ["button1", "link2"]}
  ],
  "features": ["search", "cart", "checkout", "login", "profile"]
}

Output ONLY the raw JSON object, nothing else. Do not wrap it in ```json or any markdown.""",
    tools=[get_page_state, click_element, go_back],
    output_key="feature_map",
)
