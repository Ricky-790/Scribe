from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from agents_service.models.decomposer_models import DiagramTypes


class TaskResultStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Source(BaseModel):
    """
    A single consulted source.

    ``quoted_passage`` is a verbatim excerpt backing the claim this source is
    attached to. It is deliberately optional and never validated: a subagent
    that cannot find a clean quote should omit it rather than invent text, and
    a claim with no quote still counts as supported.
    """

    url: str = Field(..., description="The URL of the source used.")
    title: Optional[str] = Field(
        default=None, description="The title of the source page, if available."
    )
    quoted_passage: Optional[str] = Field(
        default=None,
        description=(
            "A short verbatim excerpt from this source that directly supports the "
            "claim. Omit if no clean supporting passage was found — never paraphrase "
            "or reconstruct a quote."
        ),
    )
    source_type: Optional[str] = Field(
        default=None,
        description=(
            "What kind of source this is, e.g. 'peer_reviewed', 'government', "
            "'industry', 'news', 'encyclopedia', 'blog'."
        ),
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


class TaskResult(BaseModel):
    """
    What one research subagent found for its assigned question.

    A task produces exactly one headline ``claim``; ``supporting_points`` carries
    the detail behind it. Consolidation — merging duplicates, splitting compound
    claims, spotting conflicts — is deliberately NOT done here. It is the job of
    the build_claims stage, which can see every result at once.
    """

    task_id: str = Field(
        ..., description="The id of the Task this result corresponds to."
    )
    status: TaskResultStatus = Field(
        ...,
        description="'success' if the task was completed, 'partial' if some information could not be found, 'failed' if the task could not be meaningfully completed.",
    )
    claim: str = Field(
        ...,
        description=(
            "The single most important finding for this task, as one self-contained "
            "assertive sentence. If the task genuinely uncovered two distinct facts, "
            "join them here — build_claims will split the claim apart again."
        ),
    )
    supporting_points: list[str] = Field(
        default_factory=list,
        description=(
            "The specific evidence, numbers, and context behind the claim — one "
            "self-contained item each. Omit if the claim is self-explanatory."
        ),
    )
    sources: list[Source] = Field(
        default_factory=list,
        description="All sources consulted while completing this task.",
    )
    diagram_data: Optional[DiagramData] = Field(
        default=None,
        description="Populated only if the task had a diagram_plan. Null otherwise.",
    )
