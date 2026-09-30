import os

from dotenv import load_dotenv
from pydantic_ai import Agent

from agents_service.models import ResearchPlan
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.prompts import (
    DECOMPOSER_PROMPT_TEMPLATE,
    build_decomposer_instructions,
)

load_dotenv()

_default_model: str = os.getenv("DECOMPOSER_MODEL", "gemini-3.1-flash-lite")


def get_decomposer_agent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """
    Build the planning agent.

    Instructions are attached per run rather than here, because they depend on
    the topic's categories — see create_research_plan.
    """
    model = build_model(
        model_name or _default_model, provider or Provider.GOOGLE
    )
    return Agent(model, output_type=ResearchPlan)


async def create_research_plan(
    agent: Agent, goal: str, categories: list[str]
) -> ResearchPlan:
    """
    Produce a research plan for a goal.

    `agent` is supplied by the orchestrator so that a provider failure can be
    retried elsewhere. The per-category strategy is layered in with override()
    because it depends on the goal, which the agent is not built with.
    """
    prompt = DECOMPOSER_PROMPT_TEMPLATE.format(
        goal=goal,
        categories=", ".join(categories),
    )

    with agent.override(instructions=build_decomposer_instructions(categories)):
        result = await agent.run(prompt)
    return result.output
