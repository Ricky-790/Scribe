from pydantic import BaseModel, Field
from typing import Optional


class SearchResult(BaseModel):
    url: str = Field(
        ...,
        description="The URL of the search result webpage.",
    )
    content: str = Field(
        ...,
        description="The textual content or snippet extracted from the webpage.",
    )
    title: Optional[str] = Field(
        default=None, description="The title of the search result webpage."
    )
    similarity_score: Optional[float] = Field(
        default=None,
        description="The similarity or relevance score of the result compared to the search query.",
    )
