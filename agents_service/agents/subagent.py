import os

from pydantic_ai import Agent

from agents_service.models import Task, TaskResult
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.prompts import (
    NO_PRIOR_CONTEXT,
    PRIOR_CONTEXT_TEMPLATE,
    SUBAGENT_AGENT_INSTRUCTIONS,
    SUBAGENT_PROMPT_TEMPLATE,
)
from agents_service.tools import crawl_page, extract_page, web_search

# Research sub-agents run on OpenRouter rather than Google: they are the most
# numerous calls in the pipeline, and keeping them off the Gemini quota leaves
# that budget for the consolidation stages that have no alternative provider.
_default_model: str = os.getenv(
    "SUBAGENT_MODEL", "inclusionai/ling-3.0-flash-sante:free"
)


def get_subagent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(
        model_name or _default_model, provider or Provider.OPENROUTER
    )
    return Agent(
        model,
        output_type=TaskResult,
        tools=[web_search, extract_page, crawl_page],
        instructions=SUBAGENT_AGENT_INSTRUCTIONS,
    )


def _build_prior_context(prior_claims: list[str], known_problems: list[str]) -> str:
    """
    Brief the agent on what a previous attempt got wrong.

    Only correction rounds carry this. On the first round it stays empty so the
    prompt is unchanged.
    """
    if not prior_claims and not known_problems:
        return NO_PRIOR_CONTEXT

    return PRIOR_CONTEXT_TEMPLATE.format(
        known_problems="\n".join(f"- {p}" for p in known_problems)
        or "- (none recorded)",
        prior_claims="\n".join(f"- {c}" for c in prior_claims)
        or "- (nothing established yet)",
    )


async def execute_task(
    subagent: Agent,
    task: Task,
    prior_claims: list[str] | None = None,
    known_problems: list[str] | None = None,
) -> TaskResult:
    """
    Run one research task and return its single claim.

    `prior_claims` and `known_problems` are only supplied on replan rounds, where
    they tell the agent what the previous attempt established and why a reviewer
    rejected it.
    """
    prompt = SUBAGENT_PROMPT_TEMPLATE.format(
        objective=task.objective,
        evidence_requirements=task.evidence_requirements
        or "(no specific requirements were set for this task — produce the best "
        "well-sourced claim you can for the objective above)",
        prior_context=_build_prior_context(
            prior_claims or [], known_problems or []
        ),
    )

    result = await subagent.run(prompt)
    output = result.output
    output.task_id = task.id
    return output
