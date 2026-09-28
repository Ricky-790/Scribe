import operator
from typing import Annotated, Any

from typing_extensions import TypedDict

from agents_service.models import (
    IntentClassification,
    Report,
    ReportOutline,
    ReportSection,
    ResearchPlan,
    Task,
    TaskResult,
)


def merge_dicts(old: dict, new: dict) -> dict:
    """Reducer: deep-merge two dicts (for task results)."""
    merged = dict(old)
    merged.update(new)
    return merged


def add_to_list(old: list, new: list) -> list:
    """Reducer: extend list."""
    return old + new


class ResearchGraphState(TypedDict):
    """Global state for the entire research runtime."""
    report_id: str
    # Inputs
    query: str
    categories: list[str]

    # Phase 1: Classification
    classification: IntentClassification | None

    # Phase 2: Planning
    plan: ResearchPlan | None

    # Phase 3: Research execution
    task_results: Annotated[dict[str, TaskResult], merge_dicts]

    # Phase 4: Synthesis
    report_outline: ReportOutline | None
    written_sections: Annotated[dict[int, str], merge_dicts]  # order -> content
    final_report: Report | None

    # Control flow
    error: str | None

    # Streaming / observability (accumulated for Redis pub/sub)
    stream_events: Annotated[list[dict], add_to_list]


# Subgraph state for the research DAG executor
class ResearchPhaseState(TypedDict):
    """State scoped to the research phase subgraph."""

    plan: ResearchPlan
    # Completed results
    task_results: Annotated[dict[str, TaskResult], merge_dicts]
    # Task IDs still pending
    pending: list[str]
    # Task IDs completed in this batch (for reducer bookkeeping)
    just_completed: Annotated[list[str], add_to_list]
    # Error if DAG stalls
    error: str | None
    stream_events: Annotated[list[dict], add_to_list]


# State for individual section writing
class SectionWriteState(TypedDict):
    """Input state for a single section writer node."""

    goal: str
    outline: ReportOutline
    section: ReportSection
    results: dict[str, TaskResult]
    order: int
