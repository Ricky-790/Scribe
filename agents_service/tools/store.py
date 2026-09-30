"""
The data the consolidation stages read through tools.

Neither build_claims nor challenge receives the research inline — they are
handed a `ResearchStore` as pydantic-ai `deps` and pull what they need. That
keeps prompt size independent of how many tasks ran, so a twelve-task
investigation costs the agent roughly the same as a four-task one until it
decides to open a specific result.
"""

from dataclasses import dataclass, field

from agents_service.models import (
    Claim,
    ClaimGraph,
    TaskResult,
    TaskResultStatus,
)


@dataclass
class ResearchStore:
    """Everything build_claims and challenge need to do their job."""

    question: str
    task_results: dict[str, TaskResult] = field(default_factory=dict)
    # Populated after build_claims runs; challenge reads the same store.
    claim_graph: ClaimGraph | None = None

    @property
    def claims(self) -> list[Claim]:
        return list(self.claim_graph.claims) if self.claim_graph else []

    def contributing_task_ids(self) -> list[str]:
        """Tasks that actually produced something, i.e. worth consolidating."""
        return [
            task_id
            for task_id, result in self.task_results.items()
            if result.status != TaskResultStatus.FAILED
        ]

    def with_claims(self, claim_graph: ClaimGraph) -> "ResearchStore":
        """Return a copy carrying the built claims, for the challenge stage."""
        return ResearchStore(
            question=self.question,
            task_results=self.task_results,
            claim_graph=claim_graph,
        )
