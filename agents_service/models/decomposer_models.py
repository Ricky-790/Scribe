import re
from enum import Enum, StrEnum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.util.typing import Literal


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class DiagramTypes(StrEnum):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    FLOW_CHART = "flow_chart"
    BLOCK_DIAGRAM = "block_diagram"


class DiagramPlan(BaseModel):
    diagram_type: DiagramTypes = Field(
        ..., description="The type of diagram to generate for this task."
    )
    instruction: str = Field(
        ...,
        description="a specific, directive instruction to the sub-agent describing EXACTLY what data to collect or what structure to map out FOR the diagram",
    )


class Task(BaseModel):
    id: str = Field(
        ..., description="Unique short identifier for this task, e.g. 'task_1'."
    )
    name: str = Field(..., description="Short human-readable name for the task.")
    objective: str = Field(
        ...,
        description=(
            "Clear, fully-resolved description of what this task needs to find out. "
            "Written so a sub-agent with no other context could execute it correctly."
        ),
    )
    evidence_requirements: str = Field(
        default="",
        description=(
            "What specific evidence this task must produce for its claim to count as "
            "supported — e.g. 'a lifecycle gCO2e/kWh figure from at least two "
            "independent analyses'. Consumed by the challenge stage to judge whether "
            "the resulting claim is adequately supported."
        ),
    )
    diagram: bool = Field(
        default=False, description="Does this task need a representing diagram for it?"
    )
    diagram_plan: Optional[DiagramPlan] = Field(
        default=None, description="Explain the diagram requirements in this"
    )

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        # Round 2+ tasks are prefixed so they cannot collide with round 1 on the
        # (id, report_id) primary key.
        if not re.fullmatch(r"r\d+_task_\d+|task_\d+", v):
            raise ValueError(
                f"Task id '{v}' does not match required format 'task_N' or "
                f"'rN_task_N' (e.g. 'task_1', 'r2_task_1')"
            )
        return v

    @model_validator(mode="after")
    def validate_diagram_dependencies(self) -> "Task":
        if self.diagram and self.diagram_plan is None:
            raise ValueError(
                f"Task id '{self.id}': diagram needed, but diagram_plan not provided."
            )
        return self


class ResearchPlan(BaseModel):
    categories: list[str] = Field(
        ..., description="The category/categories this topic was classified under."
    )
    strategy_summary: str = Field(
        ...,
        description="Brief note on which strategy dimensions were used and how they were adapted to this specific goal.",
    )
    tasks: list[Task] = Field(
        ...,
        description=(
            "The full list of research tasks for this goal. All tasks run in "
            "parallel, so they must be independently executable."
        ),
    )

    @model_validator(mode="after")
    def validate_no_duplicate_ids(self) -> "ResearchPlan":
        ids = [t.id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate task ids found: {ids}")
        return self
