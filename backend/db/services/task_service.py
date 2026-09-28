from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents_service.models import ResearchPlan, TaskStatus
from backend.db.models import Task


class TaskService:
    def __init__(self) -> None:
        pass

    # --- writes ---

    async def create_tasks_from_plan(
        self, session: AsyncSession, report_id: UUID, plan: ResearchPlan
    ) -> None:
        """
        Bulk-insert all Task rows derived from a ResearchPlan in one go.

        Every task is created with status=PENDING. Existing tasks for the same
        report_id are not touched; callers should ensure this is only called once
        per report.
        """
        try:
            rows = [
                Task(
                    id=task.id,
                    report_id=report_id,
                    task_name=task.name,
                    objective=task.objective,
                    depends_on=task.depends_on,
                    status=TaskStatus.PENDING.value,
                )
                for task in plan.tasks
            ]
            session.add_all(rows)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def update_task_status(
        self, session: AsyncSession, report_id: UUID, task_id: str, status: str
    ) -> None:
        """Update the status of a single task identified by (report_id, task_id)."""
        try:
            await session.execute(
                update(Task)
                .where(Task.report_id == report_id, Task.id == task_id)
                .values(status=status)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def save_task_result(
        self, session: AsyncSession, report_id: UUID, task_id: str, result: dict
    ) -> None:
        """Persist the task's result and mark it done/failed based on the result's own status."""
        try:
            task_status = (
                TaskStatus.FAILED.value
                if result.get("status") == "failed"
                else TaskStatus.DONE.value
            )
            await session.execute(
                update(Task)
                .where(Task.report_id == report_id, Task.id == task_id)
                .values(result=result, status=task_status)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    # --- reads ---

    async def get_tasks_by_report(
        self, session: AsyncSession, report_id: UUID
    ) -> list[Task]:
        """Return all tasks belonging to a report, ordered by creation time."""
        try:
            result = await session.execute(
                select(Task)
                .where(Task.report_id == report_id)
                .order_by(Task.created_at)
            )
            return list(result.scalars().all())
        except Exception:
            await session.rollback()
            raise

    async def get_task(
        self, session: AsyncSession, report_id: UUID, task_id: str
    ) -> Task | None:
        """Return a single task by composite key (report_id, task_id), or None."""
        try:
            result = await session.execute(
                select(Task).where(Task.report_id == report_id, Task.id == task_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            await session.rollback()
            raise


tasks_service = TaskService()
