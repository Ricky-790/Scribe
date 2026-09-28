import os

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.groq import GroqProvider

from agents_service.models import ResearchPlan
from agents_service.prompts import (
    DECOMPOSER_PROMPT_TEMPLATE,
    build_decomposer_instructions,
)

load_dotenv()

model_name: str = os.getenv("DECOMPOSER_MODEL", "")


async def create_research_plan(goal: str, categories: list[str]) -> ResearchPlan:
    instructions = build_decomposer_instructions(categories)

    # model = GroqModel(
    #     model_name,
    #     provider=GroqProvider(api_key=os.getenv("GROQ_API_KEY", "")),
    # )
    model = GoogleModel(
        model_name,
        provider=GoogleProvider(api_key=os.getenv("GOOGLE_API_KEY", "")),
    )
    decomposer_agent = Agent(model, instructions=instructions, output_type=ResearchPlan)

    prompt = DECOMPOSER_PROMPT_TEMPLATE.format(
        goal=goal,
        categories=", ".join(categories),
    )

    result = await decomposer_agent.run(prompt)
    return result.output


import asyncio

# asyncio.run(create_research_plan("Research btc vs sol", ["tech", "finance"]))
