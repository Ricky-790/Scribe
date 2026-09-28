import asyncio
import json
from uuid import UUID

from langgraph.types import StreamWriter

from agents_service.graph.graph import get_research_graph
from agents_service.models import IntentEnum, Report
from backend.api.dto_models import PublishMessage
from backend.celery_app import celery_app, pipeline_resources
from backend.db.models import RunStatus
from backend.db.services.task_service import tasks_service
from backend.db.services.user_report_service import reports_service
from custom_logger import get_logger

logger = get_logger()


@celery_app.task(name="run_research_pipeline", bind=True, max_retries=0)
def run_research_pipeline_task(self, report_id: str):
    asyncio.run(run_pipeline(report_id))


async def run_pipeline(report_id: str) -> None:
    async with pipeline_resources() as (session_factory, redis_client):
        report_id_uuid = UUID(report_id)

        # Load report
        async with session_factory() as session:
            report = await reports_service.get_report_by_id(session, report_id_uuid)
            if report is None:
                logger.error(f"No report found for report_id={report_id}")
                return

            query = report.goal
            categories = report.categories

        # Redis publisher
        async def publish(data: dict):
            message = PublishMessage(
                phase=data.get("phase"),
                status=data.get("status"),
                done=data.get("done", False),
                task_name=data.get("task_name", None),
                task_status=data.get("task_status", None),
                task_id=data.get("task_id", None),
                msg=data.get("msg", None),
            )
            await redis_client.publish(
                f"report:{report_id}",
                message.model_dump_json(),
            )

        async def update_db(data):
            """Handles 'stage' events from graph nodes."""
            phase = data.get("phase")
            status = data.get("status")
            if phase is None or status is None:
                raise ValueError("Invalid event data: missing phase or status")

            await publish(data)
            async with session_factory() as session:
                if phase == "planning" and status == "starting":
                    await reports_service.update_status(
                        session, report_id_uuid, "planning"
                    )

                elif phase == "planning" and status == "finished":
                    await reports_service.update_status(
                        session, report_id_uuid, "researching"
                    )
                    strategy: str = data.get("strategy")
                    plan = data.get("plan", None)
                    if strategy is not None and plan is not None:
                        await reports_service.save_plan_metadata(
                            session, report_id_uuid, strategy
                        )
                        await tasks_service.create_tasks_from_plan(
                            session, report_id_uuid, plan
                        )
                    else:
                        raise ValueError("Strategy or Plan is missing")

                elif phase == "researching" and status == "finished":
                    await reports_service.update_status(
                        session, report_id_uuid, "synthesizing"
                    )

                elif phase == "synthesis" and status == "finished":
                    await reports_service.update_status(session, report_id_uuid, "done")

        async def update_task_state(data: dict):
            """Handles 'task' events from research subgraph nodes."""
            phase = data.get("phase")
            status = data.get("status")
            if phase is None or status is None:
                raise ValueError("Invalid event data: missing phase or status")
            if phase == "researching" and status == "running":
                # logger.info(f"INSIDE UPDATE TASK: {data}")
                task_id = data.get("task_id")
                task_status = data.get("task_status")
                result = data.get("task_result", None)
                result = json.loads(result) if result is not None else None
                if task_id is None or task_status is None:
                    raise ValueError(
                        f"Invalid event: task_id: {task_id} or task_status:{task_status}"
                    )
                async with session_factory() as session:
                    if result is not None:
                        await tasks_service.save_task_result(
                            session, report_id_uuid, task_id, result
                        )
                    else:
                        await tasks_service.update_task_status(
                            session, report_id_uuid, task_id, task_status
                        )

                # await publish(data)

        graph = get_research_graph()

        initial_state = {
            "report_id": report_id,
            "query": query,
            "categories": categories or [],
            "classification": None,
            "plan": None,
            "task_results": {},
            "report_outline": None,
            "written_sections": {},
            "final_report": None,
            "error": None,
            "stream_events": [],
        }

        final_state = None

        try:
            async for event in graph.astream(
                initial_state,
                stream_mode=["updates", "custom", "values"],
                version="v2",
                subgraphs=True,
            ):
                # logger.info(f"EVENT: {event}")
                if event.get("type") == "custom":
                    data = event.get("data")
                    await publish(data)
                    # logger.info(f"DATA : {data}")
                    await update_db(data)
                    await update_task_state(data)
                elif event.get("type") == "values":
                    final_state = event.get("data", None)

            if final_state and final_state.get("final_report"):
                report = final_state["final_report"]
                async with session_factory() as session:
                    await reports_service.save_report_content(
                        session, report_id_uuid, report.title, report.content
                    )

            await publish({"phase": "Full", "status": "finished"})

        except Exception:
            logger.exception(f"Pipeline failed for report_id={report_id}")
            async with session_factory() as session:
                await reports_service.update_status(session, report_id_uuid, "failed")
            await publish({"phase": "Unknown", "status": "failed"})
            raise
