from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from agents_service.models.decomposer_models import DiagramTypes


class TaskResultStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Source(BaseModel):
    url: str = Field(..., description="The URL of the source used.")
    title: Optional[str] = Field(
        default=None, description="The title of the source page, if available."
    )


class DiagramData(BaseModel):
    diagram_type: DiagramTypes = Field(
        ...,
        description="Echoed from the task's diagram_plan. Tells downstream what kind of diagram to render.",
    )
    tabular: Optional[list[dict]] = Field(
        default=None,
        description="For line_chart or bar_chart. List of row dicts where the first key is the X-axis variable and remaining keys are Y-series. e.g. [{'year': 2020, 'gold_usd': 1800, 'silver_usd': 20.5}, ...]",
    )
    mermaid: Optional[str] = Field(
        default=None,
        description="For flowchart or block_diagram. A valid Mermaid diagram string.",
    )
    caption: str = Field(
        ..., description="One sentence describing what this diagram shows."
    )

    @model_validator(mode="after")
    def validate_data_matches_type(self) -> "DiagramData":
        chart_types = {DiagramTypes.LINE_CHART, DiagramTypes.BAR_CHART}
        diagram_types = {DiagramTypes.FLOW_CHART, DiagramTypes.BLOCK_DIAGRAM}

        if self.diagram_type in chart_types and not self.tabular:
            raise ValueError(
                f"diagram_type '{self.diagram_type}' requires tabular data, but tabular is empty or null."
            )
        if self.diagram_type in diagram_types and not self.mermaid:
            raise ValueError(
                f"diagram_type '{self.diagram_type}' requires a mermaid string, but mermaid is null."
            )
        return self


class KeyFinding(BaseModel):
    point: str = Field(
        ...,
        description="One distinct, self-contained finding relevant to the task's objective. Should be specific and factual, not vague.",
    )
    supporting_detail: Optional[str] = Field(
        default=None,
        description="Additional context, numbers, or explanation backing this finding, if needed.",
    )
    source_urls: list[str] = Field(
        default_factory=list,
        description="URLs (from the sources list) that support this specific finding",
    )


class TaskResult(BaseModel):
    task_id: str = Field(
        ..., description="The id of the Task this result corresponds to."
    )
    status: TaskResultStatus = Field(
        ...,
        description="'success' if the task was completed, 'partial' if some information could not be found, 'failed' if the task could not be meaningfully completed.",
    )
    summary: str = Field(
        ...,
        description="A short (2-4 sentence) narrative summary of what was found, giving a reader the gist without needing the full findings list.",
    )
    key_findings: list[KeyFinding] = Field(
        default=[],
        description="The distinct, structured findings gathered for this task's objective. This is the primary content the synthesizer will draw on.",
    )
    sources: list[Source] = Field(
        default_factory=list,
        description="All sources consulted while completing this task.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes on limitations, contradictions between sources, or gaps in available information — useful context for the synthesizer, not for the reader.",
    )
    diagram_data: Optional[DiagramData] = Field(
        default=None,
        description="Populated only if the task had a diagram_plan. Null otherwise.",
    )
