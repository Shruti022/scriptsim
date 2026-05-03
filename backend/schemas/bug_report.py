from pydantic import BaseModel, Field
from typing import List


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


class BugReportList(BaseModel):
    bugs: List[BugReport] = Field(description="All bugs found by this persona. Empty list if none found.")


class DeduplicatedBug(BaseModel):
    title: str = Field(description="Short title summarising the bug (max 80 chars)")
    description: str = Field(description="Full description of the bug and its impact")
    severity: int = Field(description="1-5 rating", ge=1, le=5)
    url: str = Field(description="URL where the bug was observed")
    personas_affected: List[str] = Field(description="List of personas that found this bug")
    steps_to_reproduce: str = Field(description="Numbered steps to trigger the bug")
    expected_behavior: str = Field(description="What should have happened")
    actual_behavior: str = Field(description="What actually happened")
    screenshot_url: str = Field(description="GCS URI gs://... or empty string")


class DeduplicatedBugList(BaseModel):
    bugs: List[DeduplicatedBug] = Field(description="List of deduplicated bugs")


class FinalBug(DeduplicatedBug):
    rank: int = Field(description="Rank from 1 to N (1 being most severe)")
    severity_label: str = Field(description="CRITICAL | MAJOR | MODERATE | MINOR | COSMETIC")


class FinalReport(BaseModel):
    scan_summary: str = Field(description="One paragraph summary of overall product quality")
    total_bugs: int = Field(description="Total number of unique bugs found")
    critical_count: int = Field(description="Number of critical bugs (severity 5)")
    major_count: int = Field(description="Number of major bugs (severity 4)")
    bugs: List[FinalBug] = Field(description="Ranked list of bugs")
