from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from agents_service.models.sub_agent_models import Source


class ClaimStatus(StrEnum):
    SUPPORTED = "supported"
    """Backed by at least one piece of evidence from the research."""

    CONFLICTING = "conflicting"
    """Two or more sources disagree on this point. Both sides are recorded."""

    UNSUPPORTED = "unsupported"
    """Asserted during consolidation but not actually backed by any task finding."""


class Evidence(BaseModel):
    """
    One piece of support for a claim, traced back to the task that found it.

    This is the provenance link: `task_id` says which researcher's finding this
    came from, `source` is the material, and `quote` is the passage within it.
    """

    task_id: str = Field(
        ...,
        description="The task whose research produced this evidence.",
    )
    source: Source = Field(
        ...,
        description="The source material backing the claim.",
    )
    quote: str = Field(
        ...,
        description=(
            "The passage from the source that supports the claim. Copy it from the "
            "task's source; do not rewrite it."
        ),
    )


class Claim(BaseModel):
    """
    A single canonical assertion in the final report's evidence base.

    Claims are created by consolidating task results — one task's claim may be
    merged into another's, a compound claim may be split in two, and
    contradictory findings may be preserved side by side as CONFLICTING.
    """

    claim_id: str = Field(
        ...,
        description="Unique short identifier, e.g. 'C1'.",
    )
    statement: str = Field(
        ...,
        description="The claim as one precise, self-contained sentence.",
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description=(
            "Every piece of evidence supporting this claim, from any task. A claim "
            "drawn from two tasks should carry evidence from both."
        ),
    )
    supporting_tasks: list[str] = Field(
        default_factory=list,
        description=(
            "Ids of the tasks whose findings this claim was built from. Used to "
            "check that the research as a whole was actually used."
        ),
    )
    conflicts: list[str] = Field(
        default_factory=list,
        description=(
            "Ids of claims that contradict this one. Set when the research produced "
            "genuinely opposing findings."
        ),
    )
    status: ClaimStatus = Field(
        default=ClaimStatus.SUPPORTED,
        description="Whether this claim is supported, conflicting, or unsupported.",
    )
    answers: list[str] = Field(
        default_factory=list,
        description=(
            "Which part(s) of the original research question this claim answers. "
            "Claims that answer nothing may point at a gap in the plan."
        ),
    )


class ClaimGraph(BaseModel):
    claims: list[Claim] = Field(
        default_factory=list,
        description="The canonical, consolidated set of claims for this research question.",
    )

    @model_validator(mode="after")
    def validate_claim_ids_unique(self) -> "ClaimGraph":
        ids = [c.claim_id for c in self.claims]
        if len(ids) != len(set(ids)):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Duplicate claim ids found: {duplicates}")
        return self

    @model_validator(mode="after")
    def validate_conflicts_resolve(self) -> "ClaimGraph":
        """Every referenced conflict must name a claim that exists."""
        known = {c.claim_id for c in self.claims}
        for claim in self.claims:
            unknown = set(claim.conflicts) - known
            if unknown:
                raise ValueError(
                    f"Claim '{claim.claim_id}' lists conflicts against unknown "
                    f"claim id(s): {sorted(unknown)}"
                )
        return self


class ChallengeIssue(BaseModel):
    claim_id: str = Field(
        ...,
        description="The claim this problem affects.",
    )
    problem: str = Field(
        ...,
        description="What is wrong — unsupported, conflicting, or not answering the question.",
    )
    missing_evidence: str = Field(
        ...,
        description="Specifically what evidence is absent or inadequate.",
    )
    recommended_research: str = Field(
        ...,
        description=(
            "A directive instruction for a research agent describing exactly what "
            "new research would resolve this problem."
        ),
    )


class ChallengeResult(BaseModel):
    status: str = Field(
        ...,
        description="'sufficient' if the claims are adequately supported and answer the question, 'needs_research' otherwise.",
    )
    issues: list[ChallengeIssue] = Field(
        default_factory=list,
        description="The problems found. Empty when status is 'sufficient'.",
    )

    @model_validator(mode="after")
    def validate_issues_present(self) -> "ChallengeResult":
        if self.status not in ("sufficient", "needs_research"):
            raise ValueError(
                f"status must be 'sufficient' or 'needs_research', got {self.status!r}"
            )
        if self.status == "needs_research" and not self.issues:
            raise ValueError(
                "status is 'needs_research' but no issues were listed — the planner "
                "would have nothing to act on."
            )
        return self


class ReplanTask(BaseModel):
    task_id: str = Field(
        ...,
        description="Unique short identifier, e.g. 'r2_task_1'.",
    )
    name: str = Field(..., description="Short human-readable name for the task.")
    objective: str = Field(
        ...,
        description="Clear, fully-resolved description of what this task must find out.",
    )
    evidence_requirements: str = Field(
        ...,
        description=(
            "What specific evidence this task must produce for its claim to count "
            "as supported. Written so the researcher knows what 'good' looks like."
        ),
    )
    addresses_claim_ids: list[str] = Field(
        default_factory=list,
        description="The claim ids this task is meant to resolve.",
    )


class ReplanPlan(BaseModel):
    tasks: list[ReplanTask] = Field(
        default_factory=list,
        description="The additional research tasks to run.",
    )

    @model_validator(mode="after")
    def validate_ids_unique(self) -> "ReplanPlan":
        ids = [t.task_id for t in self.tasks]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate task ids found: {ids}")
        return self
