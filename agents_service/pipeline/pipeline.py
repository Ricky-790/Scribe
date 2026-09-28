from agents_service.agents import (
    classify_query,
    create_research_plan,
    get_classifier_agent,
    get_outline_agent,
    get_section_writer_agent,
    get_subagent,
)
from agents_service.models import (
    IntentClassification,
    IntentEnum,
    Report,
    ResearchPlan,
    TaskResult,
)
from agents_service.pipeline.create_report import generate_report
from agents_service.pipeline.executor import execute_research_phase
from custom_logger import get_logger

logger = get_logger()


class Pipeline:
    def __init__(self, on_task_update, on_stage_complete):
        self.classifier_agent = get_classifier_agent()
        self.subagent = get_subagent()
        self.outline_agent = get_outline_agent()
        self.section_writer_agent = get_section_writer_agent()
        self.on_task_update = on_task_update
        self.on_stage_complete = on_stage_complete

    async def _classify_query(self, query) -> IntentClassification:
        classification = await classify_query(self.classifier_agent, query)
        logger.info(
            f"Classified as {classification.intent} | categories={classification.categories}"
        )
        return classification

    async def _create_research_plan(self, query, categories) -> ResearchPlan:
        plan = await create_research_plan(query, categories)
        logger.info(f"Plan generated with {len(plan.tasks)} tasks")
        return plan

    async def _execute_research_phase(
        self, plan: ResearchPlan, max_concurrency: int = 1
    ) -> dict[str, TaskResult]:
        results = await execute_research_phase(
            plan,
            max_concurrency=max_concurrency,
            on_task_update=self.on_task_update,
            subagent=self.subagent,
        )
        succeeded = sum(1 for r in results.values() if r.status.value == "success")
        logger.info(
            f"Research phase complete: {succeeded}/{len(results)} tasks succeeded"
        )
        return results

    async def _generate_report(self, query, results):
        report = await generate_report(
            goal=query,
            results=results,
            outline_agent=self.outline_agent,
            section_writer_agent=self.section_writer_agent,
        )
        logger.info(f"Report generated: '{report.title}' ({len(report.content)} chars)")
        return report

    async def run_pipeline(self, query: str, categories: list[str]) -> str | Report:
        """
        Runs the full pipeline: classify -> decompose -> execute research -> synthesize.
        """
        await self.on_stage_complete(phase="planning", status="starting")
        plan = await self._create_research_plan(query, categories)
        await self.on_stage_complete(phase="planning", status="finished", plan=plan)

        await self.on_stage_complete(phase="research", status="starting")
        results = await self._execute_research_phase(
            plan, max_concurrency=1
        )  # todo: publish research phase tasks done
        await self.on_stage_complete(phase="research", status="finished")

        await self.on_stage_complete(phase="synthesis", status="starting")
        report = await self._generate_report(query, results)
        await self.on_stage_complete(
            phase="synthesis", status="finished", report=report
        )
        return report
