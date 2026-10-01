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
from agents_service.pipeline.rate_limiting import release_resources
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
            """Applies DB side effects for events from the graph nodes.

            Purely a persistence concern — publishing is the stream loop's job,
            so it must never emit anything itself.
            """
            phase = data.get("phase")
            status = data.get("status")
            if phase is None or status is None:
                raise ValueError("Invalid event data: missing phase or status")

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

                elif phase == "verifying" and status == "running":
                    # Build Claims is the first thing that runs once research
                    # settles, so it owns the transition into verification.
                    # Repeats are harmless; a replan round re-enters research
                    # and this fires again.
                    await reports_service.update_status(
                        session, report_id_uuid, "verifying"
                    )

                    replan_tasks = data.get("replan_tasks") or []
                    if replan_tasks:
                        # A correction round added tasks; persist them so the
                        # run's task list shows what the review stage asked for.
                        await tasks_service.create_tasks_from_replan(
                            session, report_id_uuid, replan_tasks
                        )

                elif phase == "verifying" and status == "finished":
                    # The claim graph survived review, so the report is being
                    # written.
                    await reports_service.update_status(
                        session, report_id_uuid, "synthesizing"
                    )

                elif phase == "synthesis" and status == "finished":
                    # Every section writer emits synthesis/finished, so only the
                    # terminal event (done=True, from compile_report_node) may
                    # mark the run complete — otherwise the report is announced
                    # as finished while its content is still being assembled.
                    if not data.get("done"):
                        return
                    await reports_service.update_status(session, report_id_uuid, "done")

        async def update_task_state(data: dict):
            """Applies per-task DB side effects for events from the research subgraph."""
            phase = data.get("phase")
            status = data.get("status")
            if phase is None or status is None:
                raise ValueError("Invalid event data: missing phase or status")
            if phase == "researching" and status == "running":
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

        graph = get_research_graph()

        initial_state = {
            "report_id": report_id,
            "query": query,
            "categories": categories or [],
            "plan": None,
            "replan_tasks": [],
            "replan_count": 0,
            "task_results": {},
            "claim_graph": None,
            "challenge_result": None,
            "replan_plan": None,
            "report_outline": None,
            "written_sections": {},
            "final_report": None,
            "error": None,
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
                # Emitted only after the body is persisted, so a client that
                # reacts to it can never read back a half-written report. The
                # status was already flipped to done by the terminal graph event.
                await publish(
                    {
                        "phase": "synthesis",
                        "status": "finished",
                        "done": True,
                        "msg": "Report ready.",
                    }
                )

        except Exception as exc:
            logger.exception(f"Pipeline failed for report_id={report_id}")
            async with session_factory() as session:
                await reports_service.update_status(session, report_id_uuid, "failed")
            await publish(
                {
                    "phase": "failed",
                    "status": "failed",
                    "done": True,
                    "msg": str(exc) or "Research pipeline failed.",
                }
            )
            raise
        finally:
            # This task's event loop is about to be torn down by asyncio.run(),
            # and the shared rate limiter holds a Redis pool bound to it. Close
            # it explicitly rather than waiting for the loop's GC.
            await release_resources()
