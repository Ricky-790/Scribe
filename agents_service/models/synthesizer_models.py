from pydantic import BaseModel, Field, model_validator

from agents_service.models.sub_agent_models import DiagramData


class GeneratedDiagram(DiagramData):
    url: str | None = None



class ReportSection(BaseModel):
    order: int = Field(
        ...,
        description="The order this section should appear in the final report.",
        gt=0,
    )
    title: str = Field(..., description="The section's heading.")
    description: str = Field(
        ..., description="What this section should cover — guides the section writer."
    )
    relevant_task_ids: list[str] = Field(
        default_factory=list,
        description="task_ids whose findings are relevant to this section. Can be empty for sections like an introduction or conclusion that synthesize across everything rather than drawing on one specific set of findings.",
    )
    diagrams: list[GeneratedDiagram] = Field(
        default_factory=list,
        description="Diagram data collected from relevant task results. Populated after outline generation, NOT by the outline agent.",
    )


class ReportOutline(BaseModel):
    title: str
    sections: list[ReportSection]

    @model_validator(mode="after")
    def validate_section_order(self) -> "ReportOutline":
        orders = sorted(s.order for s in self.sections)
        expected = list(range(1, len(self.sections) + 1))
        if orders != expected:
            raise ValueError(
                f"Section order values must be 1..N with no gaps/duplicates, got {orders}"
            )
        return self


class Report(BaseModel):
    title: str = Field(..., description="The report's title.")
    content: str = Field(
        ...,
        description="The full report content, assembled from all sections, formatted as Markdown.",
    )
