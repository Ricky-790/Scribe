import os

from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from agents_service.models import ClaimGraph
from agents_service.prompts import (
    BUILD_CLAIMS_AGENT_INSTRUCTIONS,
    BUILD_CLAIMS_PROMPT_TEMPLATE,
)
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.tools import (
    get_all_claims,
    get_task_result,
    list_task_results,
    search_evidence,
)
from agents_service.tools import get_claims_question as get_question_tool
from agents_service.tools.challenge_tools import list_claims
from agents_service.tools.store import ResearchStore

_default_model: str = os.getenv("CLAIMS_MODEL", "gemini-3.1-flash-lite")

# Tool-driven agents can loop; cap the exploration so a confused run terminates.
MAX_TOOL_CALLS = 40


def get_claims_agent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(model_name or _default_model, provider or Provider.GOOGLE)
    return Agent(
        model,
        deps_type=ResearchStore,
        output_type=ClaimGraph,
        tools=[
            list_task_results,
            get_task_result,
            get_all_claims,
            search_evidence,
            get_question_tool,
            # Lets the agent check the graph it is about to replace, when a
            # previous round already built one.
            list_claims,
        ],
        instructions=BUILD_CLAIMS_AGENT_INSTRUCTIONS,
    )


async def build_claims(agent: Agent, store: ResearchStore) -> ClaimGraph:
    """
    Consolidate every task result into a canonical claim graph.

    The agent reads the research through tools rather than receiving it in the
    prompt, so cost stays flat as the task count grows.
    """
    result = await agent.run(
        BUILD_CLAIMS_PROMPT_TEMPLATE,
        deps=store,
        usage_limits=UsageLimits(tool_calls_limit=MAX_TOOL_CALLS),
    )
    return result.output
