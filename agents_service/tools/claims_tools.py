"""
Tools the build_claims agent uses to read the research.

Each function is a plain, side-effect-free reader over the store, so they can be
unit tested without a model. The docstrings are not decoration — they are the
tool schema the model sees, and they are what steers it toward exploring the
whole result set rather than stopping at the first two tasks.
"""

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from agents_service.models import TaskResultStatus
from agents_service.tools.store import ResearchStore

# How many task ids to list at once before the model must page through them.
# Enough to see the whole shape of a typical run in one call.
TASK_INDEX_LIMIT = 60
CLAIM_INDEX_LIMIT = 80


class TaskIndexEntry(BaseModel):
    task_id: str = Field(..., description="Id of the task.")
    claim: str = Field(..., description="The headline claim this task produced.")
    supporting_point_count: int = Field(
        ..., description="How many supporting points back the claim."
    )
    source_count: int = Field(
        ..., description="How many sources were consulted for this task."
    )
    has_quote: bool = Field(
        ...,
        description="Whether any source carries a verbatim quoted passage.",
    )


class ClaimsIndexEntry(BaseModel):
    claim_id: str = Field(
        ..., description="Id of the claim, e.g. 'C1'."
    )
    statement: str = Field(..., description="The claim statement.")
    supporting_tasks: list[str] = Field(
        default_factory=list, description="Tasks this claim was built from."
    )
    evidence_count: int = Field(
        ..., description="How many pieces of evidence back this claim."
    )
    conflicts: list[str] = Field(
        default_factory=list, description="Claim ids that contradict this one."
    )


def list_task_results(ctx: RunContext[ResearchStore]) -> list[TaskIndexEntry]:
    """
    List every research task that produced a finding, with its headline claim.

    Start here. This gives you the shape of the whole investigation without the
    cost of reading each result in full. Note the exact task_id spelling — you
    must pass it back verbatim to get_task_result.
    """
    entries: list[TaskIndexEntry] = []
    for task_id in ctx.deps.contributing_task_ids():
        result = ctx.deps.task_results[task_id]
        entries.append(
            TaskIndexEntry(
                task_id=result.task_id,
                claim=result.claim,
                supporting_point_count=len(result.supporting_points),
                source_count=len(result.sources),
                has_quote=any(s.quoted_passage for s in result.sources),
            )
        )
        if len(entries) >= TASK_INDEX_LIMIT:
            break
    return entries


def get_task_result(ctx: RunContext[ResearchStore], task_id: str) -> dict:
    """
    Return one task's full result: claim, supporting points, and every source
    with its quoted passage.

    Use this for any task whose claim you need to consolidate, split, or check
    against another. The quotes are the evidence you must attach, so copy them
    into the claim's evidence rather than paraphrasing the source.
    """
    result = ctx.deps.task_results.get(task_id)
    if result is None:
        return {
            "error": f"No result for task '{task_id}'.",
            "available_task_ids": ctx.deps.contributing_task_ids(),
        }
    return result.model_dump(mode="json")


def get_all_claims(ctx: RunContext[ResearchStore]) -> list[str]:
    """
    Cheap global view: every task's claim as one line, no sources.

    Use this to spot overlap between tasks before deciding which ones to open in
    full. Cheaper than get_task_result when you only need to compare wording.
    """
    return [
        f"[{task_id}] {ctx.deps.task_results[task_id].claim}"
        for task_id in ctx.deps.contributing_task_ids()
    ]


def search_evidence(ctx: RunContext[ResearchStore], term: str) -> list[dict]:
    """
    Search across all task claims, supporting points and source text for a term.

    Use this to find tasks you did not think to look at directly — for example
    when two tasks seem to disagree but neither names the other, or when a
    specific figure or entity is the thing being compared. Matching is
    case-insensitive and matches on whole-word-or-substring.
    """
    needle = (term or "").strip().lower()
    if not needle:
        return {"error": "Provide a non-empty search term."}

    hits: list[dict] = []
    for task_id in ctx.deps.contributing_task_ids():
        result = ctx.deps.task_results[task_id]
        matched_points = [p for p in result.supporting_points if needle in p.lower()]
        matched_sources = [
            {
                "url": s.url,
                "title": s.title,
                "quoted_passage": s.quoted_passage,
            }
            for s in result.sources
            if needle in " ".join(filter(None, [s.title, s.quoted_passage])).lower()
        ]
        if needle in result.claim.lower() or matched_points or matched_sources:
            hits.append(
                {
                    "task_id": task_id,
                    "claim": result.claim,
                    "matched_supporting_points": matched_points,
                    "matched_sources": matched_sources,
                }
            )
    return {"term": term, "match_count": len(hits), "matches": hits}


def get_research_question(ctx: RunContext[ResearchStore]) -> str:
    """
    The original research question, exactly as the user asked it.

    Read this before assigning claims to parts of the question. Every claim you
    write should populate `answers` with the specific part of the question it
    addresses, and a part of the question that no claim answers is a gap the
    challenge stage needs to see.
    """
    return ctx.deps.question
