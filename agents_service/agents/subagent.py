import os

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.groq import GroqProvider

from agents_service.models import Source, Task, TaskResult
from agents_service.prompts import (
    DEPENDENCY_CONTEXT_TEMPLATE,
    SUBAGENT_AGENT_INSTRUCTIONS,
    SUBAGENT_PROMPT_TEMPLATE,
)
from agents_service.tools import crawl_page, extract_page, web_search

model_name: str = os.getenv("SUBAGENT_MODEL", "llama-3.3-70b-versatile")

# model = GroqModel(
#     model_name,
#     provider=GroqProvider(api_key=os.getenv("GROQ_API_KEY", "")),
# )


def get_subagent():
    model = GoogleModel(
        model_name, provider=GoogleProvider(api_key=os.getenv("GOOGLE_API_KEY", ""))
    )
    subagent = Agent(
        model,
        output_type=TaskResult,
        tools=[web_search, extract_page, crawl_page],
        instructions=SUBAGENT_AGENT_INSTRUCTIONS,
    )
    return subagent


def _build_dependency_context(task: Task, results_so_far: dict[str, TaskResult]) -> str:
    if not task.depends_on:
        return ""

    findings_blocks = []
    for dep_id in task.depends_on:
        dep_result = results_so_far.get(dep_id)
        if dep_result is None:
            continue
        points = "\n".join(f"  - {f.point}" for f in dep_result.key_findings)
        findings_blocks.append(f"[{dep_id}] {dep_result.summary}\n{points}")

    if not findings_blocks:
        return ""

    return DEPENDENCY_CONTEXT_TEMPLATE.format(
        dependency_findings="\n\n".join(findings_blocks)
    )


async def execute_task(
    subagent: Agent, task: Task, results_so_far: dict[str, TaskResult] | None = None
) -> TaskResult:
    results_so_far = results_so_far or {}
    dependency_context = _build_dependency_context(task, results_so_far)

    prompt = SUBAGENT_PROMPT_TEMPLATE.format(
        objective=task.objective,
        dependency_context=dependency_context,
    )

    result = await subagent.run(prompt)
    output = result.output
    output.task_id = task.id

    if not output.sources:
        seen = {s.url for s in output.sources}
        for finding in output.key_findings:
            for url in finding.source_urls:
                if url not in seen:
                    output.sources.append(Source(url=url))
                    seen.add(url)

    return output
