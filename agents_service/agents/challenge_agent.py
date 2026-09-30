import os

from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from agents_service.models import ChallengeResult
from agents_service.prompts import (
    CHALLENGE_AGENT_INSTRUCTIONS,
    CHALLENGE_PROMPT_TEMPLATE,
)
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.tools import (
    get_claim,
    get_evidence_source,
    get_task_claim,
    list_claims,
    search_claims,
)
from agents_service.tools.challenge_tools import (
    get_research_question as get_question_tool,
)
from agents_service.tools.store import ResearchStore

_default_model: str = os.getenv("CHALLENGE_MODEL", "gemini-3.1-flash-lite")

# Reading a quote for every claim is the whole job here, so the ceiling is
# higher than for build_claims.
MAX_TOOL_CALLS = 60


def get_challenge_agent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(model_name or _default_model, provider or Provider.GOOGLE)
    return Agent(
        model,
        deps_type=ResearchStore,
        output_type=ChallengeResult,
        tools=[
            list_claims,
            get_claim,
            get_evidence_source,
            get_task_claim,
            search_claims,
            get_question_tool,
        ],
        instructions=CHALLENGE_AGENT_INSTRUCTIONS,
    )


async def challenge_claims(agent: Agent, store: ResearchStore) -> ChallengeResult:
    """Interrogate the claim graph and report whether it can be written up."""
    result = await agent.run(
        CHALLENGE_PROMPT_TEMPLATE,
        deps=store,
        usage_limits=UsageLimits(tool_calls_limit=MAX_TOOL_CALLS),
    )
    return result.output
