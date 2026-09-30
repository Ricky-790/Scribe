import os
import re

from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from agents_service.models import ChallengeResult, ClaimGraph, ReplanPlan
from agents_service.prompts import REPLAN_AGENT_INSTRUCTIONS, REPLAN_PROMPT_TEMPLATE
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.tools import get_claim, list_claims
from agents_service.tools.store import ResearchStore
from custom_logger import get_logger

_default_model: str = os.getenv("REPLAN_MODEL", "gemini-3.1-flash-lite")

logger = get_logger()

# Only a handful of gaps should ever need a second pass.
MAX_TOOL_CALLS = 20

_TASK_ID_RE = re.compile(r"(?:r(\d+)_)?task_(\d+)")


def get_replan_agent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(model_name or _default_model, provider or Provider.GOOGLE)
    return Agent(
        model,
        deps_type=ResearchStore,
        output_type=ReplanPlan,
        tools=[list_claims, get_claim],
        instructions=REPLAN_AGENT_INSTRUCTIONS,
    )


def _render_claims(claim_graph: ClaimGraph | None) -> str:
    if claim_graph is None or not claim_graph.claims:
        return "(no claims were built)"

    lines = []
    for claim in claim_graph.claims:
        lines.append(f"[{claim.claim_id}] ({claim.status}) {claim.statement}")
        if claim.evidence:
            sources = ", ".join(
                {
                    f"{e.source.title or e.source.url}"
                    for e in claim.evidence
                }
            )
            lines.append(f"      evidence: {sources}")
        if claim.conflicts:
            lines.append(f"      conflicts with: {', '.join(claim.conflicts)}")
    return "\n".join(lines)


def _render_issues(challenge: ChallengeResult) -> str:
    if not challenge.issues:
        return "(no issues were recorded)"

    lines = []
    for issue in challenge.issues:
        lines.append(f"- Claim {issue.claim_id}: {issue.problem}")
        lines.append(f"    missing evidence: {issue.missing_evidence}")
        lines.append(f"    recommended research: {issue.recommended_research}")
    return "\n".join(lines)


def _highest_task_number(task_ids: list[str]) -> int:
    highest = 0
    for task_id in task_ids:
        match = _TASK_ID_RE.fullmatch(task_id)
        if match:
            highest = max(highest, int(match.group(2)))
    return highest


def normalise_replan_ids(
    plan: ReplanPlan, round_number: int, existing_task_ids: list[str]
) -> ReplanPlan:
    """
    Force replan task ids into `rN_task_M` form, unique within the report.

    The model is told the format but is not trusted to respect it, and these ids
    are part of the tasks table's primary key — a collision would be a write
    error, not a cosmetic problem. Numbering continues from the highest existing
    task so ids stay unique across rounds.
    """
    taken = set(existing_task_ids)
    next_number = _highest_task_number(existing_task_ids) + 1

    seen: set[str] = set()
    for task in plan.tasks:
        candidate = f"r{round_number}_task_{next_number}"
        while candidate in taken or candidate in seen:
            next_number += 1
            candidate = f"r{round_number}_task_{next_number}"
        task.task_id = candidate
        taken.add(candidate)
        seen.add(candidate)
        next_number += 1

    return plan


async def create_replan(
    agent: Agent,
    store: ResearchStore,
    challenge: ChallengeResult,
    round_number: int,
) -> ReplanPlan:
    """Turn the challenge stage's issues into the next round of research tasks."""
    prompt = REPLAN_PROMPT_TEMPLATE.format(
        question=store.question,
        claims=_render_claims(store.claim_graph),
        issues=_render_issues(challenge),
    )

    try:
        result = await agent.run(
            prompt,
            deps=store,
            usage_limits=UsageLimits(tool_calls_limit=MAX_TOOL_CALLS),
        )
        plan = result.output
    except Exception:
        # A failure here means we cannot fix what challenge found, but it must
        # not take down a report that may still be writable.
        logger.exception("Replan agent failed; proceeding without additional research")
        return ReplanPlan(tasks=[])

    return normalise_replan_ids(
        plan, round_number, list(store.task_results.keys())
    )
