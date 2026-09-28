import asyncio
import logging

from pydantic_ai import Agent

from agents_service.agents.subagent import execute_task
from agents_service.models import ResearchPlan, Task, TaskResult, TaskResultStatus
from agents_service.pipeline.rate_limiting import run_with_retry

logger = logging.getLogger(__name__)


async def execute_research_phase(
    plan: ResearchPlan,
    subagent: Agent,
    on_task_update,
    max_concurrency: int = 2,
) -> dict[str, TaskResult]:
    semaphore = asyncio.Semaphore(max_concurrency)
    done: dict[str, TaskResult] = {}
    remaining: dict[str, Task] = {t.id: t for t in plan.tasks}

    async def run_with_limit(task: Task) -> TaskResult:
        async with semaphore:
            # logger.info(f"Starting task {task.id}: {task.name}")
            try:
                result = await run_with_retry(execute_task, subagent, task, done)
            except Exception as e:
                logger.exception(f"Task {task.id} failed after retries")
                result = TaskResult(
                    task_id=task.id,
                    status=TaskResultStatus.FAILED,
                    summary=f"Task failed: {e}",
                    key_findings=[],
                    sources=[],
                    notes=str(e),
                )
            logger.info(f"Finished task {task.id} with status={result.status}")
            return result

    while remaining:
        ready = [
            t for t in remaining.values() if all(dep in done for dep in t.depends_on)
        ]

        if not ready:
            raise RuntimeError(
                f"DAG execution stalled — remaining tasks {list(remaining.keys())} have "
                f"unresolvable dependencies."
            )

        results = await asyncio.gather(*[run_with_limit(t) for t in ready])

        for t, r in zip(ready, results):
            done[t.id] = r
            task_name = remaining[t.id].name
            await on_task_update(
                r.task_id, r.status, r.model_dump(mode="json"), task=task_name
            )
            del remaining[t.id]

    return done
