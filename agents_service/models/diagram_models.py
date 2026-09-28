from typing import Optional

from pydantic import BaseModel, Field


class DiagramAgentOutput(BaseModel):
    code: str = Field(
        ...,
        description="Complete, self-contained Python script that generates the diagram and saves it as a PNG",
    )
    output_filename: str = Field(
        ...,
        description="The filename the script saves to, e.g. 'gold_silver_prices' or 'timeline'. NO PATH, NO FILE EXTENSION, just the filename.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any notes about assumptions made or data that was estimated due to gaps.",
    )
