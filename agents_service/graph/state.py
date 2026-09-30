from typing import Annotated

from typing_extensions import TypedDict

from agents_service.models import (
    ChallengeResult,
    ClaimGraph,
    IntentClassification,
    Report,
    ReportOutline,
    ReportSection,
    ReplanPlan,
    ResearchPlan,
    Task,
    TaskResult,
)


def merge_dicts(old: dict, new: dict) -> dict:
    """
    Reducer: merge a partial mapping into the accumulated one.

    Shallow by design — every value written here is a whole model keyed by id
    (task id, section order), so there is nothing nested to merge.
    """
    merged = dict(old)
    merged.update(new)
    return merged


class ResearchGraphState(TypedDict, total=False):
    """Global state for the entire research runtime."""

    report_id: str
    # Inputs
    query: str
    categories: list[str]

    # Planning
    plan: ResearchPlan | None
    # Tasks added by replan, appended across rounds
    replan_tasks: Annotated[list[Task], lambda old, new: old + new]
    # How many replan rounds have run; caps the challenge/replan loop
    replan_count: int

    # Research execution. Accumulates across rounds, so a replan round's
    # results sit alongside the original run's and build_claims sees both.
    task_results: Annotated[dict[str, TaskResult], merge_dicts]

    # Consolidation
    claim_graph: ClaimGraph | None
    challenge_result: ChallengeResult | None
    replan_plan: ReplanPlan | None

    # Synthesis
    report_outline: ReportOutline | None
    written_sections: Annotated[dict[int, str], merge_dicts]  # order -> content
    final_report: Report | None

    # Control flow
    error: str | None


class SectionWriteState(TypedDict):
    """Input state for a single section writer node, dispatched via Send."""

    goal: str
    outline: ReportOutline
    section: ReportSection
    claim_graph: ClaimGraph
    results: dict[str, TaskResult]
    order: int


class TaskExecutionState(TypedDict):
    """Input state for a single research task node, dispatched via Send."""

    task: Task
    results_so_far: dict[str, TaskResult]
    # Only present on replan rounds
    prior_claims: list[str]
    known_problems: list[str]
