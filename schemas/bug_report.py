from pydantic import BaseModel, Field


class BugReport(BaseModel):
    title: str = Field(description="Short title summarising the bug (max 80 chars)")
    description: str = Field(description="Full description of the bug and its impact")
    severity: int = Field(description="1=cosmetic 2=minor 3=moderate 4=major 5=critical", ge=1, le=5)
    url: str = Field(description="URL where the bug was observed")
    persona: str = Field(description="Persona that found it: kid | power_user | parent | retiree")
    steps_to_reproduce: str = Field(description="Numbered steps to trigger the bug")
    expected_behavior: str = Field(description="What should have happened")
    actual_behavior: str = Field(description="What actually happened")
    screenshot_url: str = Field(description="GCS URI gs://... or empty string if no screenshot")
