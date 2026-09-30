"""
Tools the challenge agent uses to interrogate the claim graph.

The point of this stage is judging whether claims are actually supported, so the
tools are biased toward pulling the underlying quote rather than trusting the
claim statement. `get_evidence_source` exists so the agent can read the passage
and decide for itself whether it backs the claim attached to it.
"""

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from agents_service.tools.store import ResearchStore

CLAIM_INDEX_LIMIT = 80


class ClaimIndexEntry(BaseModel):
    claim_id: str = Field(..., description="Id of the claim.")
    statement: str = Field(..., description="The claim statement.")
    status: str = Field(..., description="supported | conflicting | unsupported.")
    evidence_count: int = Field(
        ..., description="How many pieces of evidence back this claim."
    )
    has_quote: bool = Field(
        ..., description="Whether any evidence carries a verbatim passage."
    )
    supporting_tasks: list[str] = Field(
        default_factory=list, description="Tasks this claim was built from."
    )
    conflicts: list[str] = Field(
        default_factory=list, description="Claim ids that contradict this one."
    )
    answers: list[str] = Field(
        default_factory=list, description="Parts of the question this claim answers."
    )


def list_claims(ctx: RunContext[ResearchStore]) -> list[ClaimIndexEntry]:
    """
    List every claim in the graph with its status and evidence count.

    Start here to see what the consolidation produced and which claims are thin
    on support. Note the exact claim_id spelling — pass it back verbatim to
    get_claim.
    """
    entries: list[ClaimIndexEntry] = []
    for claim in ctx.deps.claims:
        entries.append(
            ClaimIndexEntry(
                claim_id=claim.claim_id,
                statement=claim.statement,
                status=str(claim.status),
                evidence_count=len(claim.evidence),
                has_quote=any(e.quote for e in claim.evidence),
                supporting_tasks=claim.supporting_tasks,
                conflicts=claim.conflicts,
                answers=claim.answers,
            )
        )
        if len(entries) >= CLAIM_INDEX_LIMIT:
            break
    return entries


def get_claim(ctx: RunContext[ResearchStore], claim_id: str) -> dict:
    """
    Return one claim in full: statement, status, conflicts, and every piece of
    evidence attached to it.

    Use this for any claim you intend to challenge. If its evidence is empty,
    thin, or all from one task, open the source to see whether it really
    supports the statement before deciding.
    """
    for claim in ctx.deps.claims:
        if claim.claim_id == claim_id:
            return claim.model_dump(mode="json")
    return {
        "error": f"No claim with id '{claim_id}'.",
        "available_claim_ids": [c.claim_id for c in ctx.deps.claims],
    }


def get_evidence_source(ctx: RunContext[ResearchStore], claim_id: str) -> list[dict]:
    """
    Return just the sources and quoted passages behind a claim.

    This is how you check that a quote genuinely supports the claim it is
    attached to. A quote that discusses the topic without stating the claim, or
    that came from a single weak source, is a real gap even though the claim is
    technically marked supported.
    """
    for claim in ctx.deps.claims:
        if claim.claim_id == claim_id:
            return [
                {
                    "task_id": e.task_id,
                    "url": e.source.url,
                    "title": e.source.title,
                    "source_type": e.source.source_type,
                    "quote": e.quote,
                }
                for e in claim.evidence
            ]
    return []


def get_research_question(ctx: RunContext[ResearchStore]) -> str:
    """
    The original research question, exactly as the user asked it.

    Read this to judge coverage: a claim graph can be perfectly supported and
    still fail if some part of the question has no claim answering it. Check
    every clause of the question against the claims' `answers` fields.
    """
    return ctx.deps.question


def get_task_claim(ctx: RunContext[ResearchStore], task_id: str) -> dict:
    """
    The original finding behind a task, before consolidation.

    Use this when a claim looks like it lost something in the merge, or to see
    whether a claim was over-condensed from what the researcher actually found.
    """
    result = ctx.deps.task_results.get(task_id)
    if result is None:
        return {"error": f"No result for task '{task_id}'."}
    return result.model_dump(mode="json")


def search_claims(ctx: RunContext[ResearchStore], term: str) -> list[dict]:
    """
    Search claim statements, evidence quotes and source titles for a term.

    Use this to find claims about something you did not think to look for — for
    instance when checking whether two claims about the same entity are
    actually compatible, or tracking a specific figure across the graph.
    """
    needle = (term or "").strip().lower()
    if not needle:
        return []

    hits: list[dict] = []
    for claim in ctx.deps.claims:
        haystack = " ".join(
            part
            for evidence in claim.evidence
            for part in (evidence.quote, evidence.source.title)
            if part
        )
        if needle in claim.statement.lower() or needle in haystack.lower():
            hits.append(
                {
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "status": str(claim.status),
                    "conflicts": claim.conflicts,
                }
            )
    return hits
