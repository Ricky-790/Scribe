import os

from dotenv import load_dotenv
from pydantic_ai import Agent

from agents_service.models.diagram_models import DiagramAgentOutput
from agents_service.models.sub_agent_models import DiagramData
from agents_service.pipeline.orchestrator import build_model
from agents_service.pipeline.rate_limiting import Provider
from agents_service.prompts import (
    DIAGRAM_AGENT_PROMPT,
    DIAGRAM_AGENT_SYSTEM_INSTRUCTIONS,
)
from agents_service.prompts.diagram_prompts import build_data_block

load_dotenv()

_default_model: str = os.getenv("CODE_GENERATION_MODEL", "minimaxai/minimax-m3")


def get_diagram_agent(
    model_name: str | None = None, provider: Provider | None = None
) -> Agent:
    """Build the agent. Overrides let the orchestrator supply a fallback model."""
    model = build_model(
        model_name or _default_model, provider or Provider.OPENROUTER
    )
    code_gen_agent = Agent(
        model,
        output_type=DiagramAgentOutput,
        instructions=DIAGRAM_AGENT_SYSTEM_INSTRUCTIONS,
    )
    return code_gen_agent


async def generate_diagram_code(
    prompt: str,
    diagram_agent: Agent | None = None,
):
    if not diagram_agent:
        diagram_agent = get_diagram_agent()
    return await diagram_agent.run(prompt)
