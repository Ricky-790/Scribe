from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RunStatus, UserReport


class UserReportService:
    def __init__(self) -> None:
        pass

    # --- writes ---

    async def create_report(
        self, session: AsyncSession, user_id: UUID, goal: str, message_id: UUID
    ) -> UserReport:
        """Create a new UserReport with PENDING status and return it."""
        try:
            report = UserReport(
                user_id=user_id,
                goal=goal,
                status=RunStatus.PENDING,
                message_id=message_id,
            )
            session.add(report)
            await session.commit()
            await session.refresh(report)
            return report
        except Exception:
            await session.rollback()
            raise

    async def update_status(
        self, session: AsyncSession, report_id: UUID, status: str
    ) -> None:
        """Update the status field of an existing report."""
        try:
            await session.execute(
                update(UserReport)
                .where(UserReport.id == report_id)
                .values(status=status)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def save_classification(
        self,
        session: AsyncSession,
        report_id: UUID,
        intent: str,
        categories: list[str] | None,
        response: str | None,
    ) -> None:
        """Persist classifier output (intent, categories, response) onto a report."""
        try:
            await session.execute(
                update(UserReport)
                .where(UserReport.id == report_id)
                .values(intent=intent, categories=categories, response=response)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def save_plan_metadata(
        self, session: AsyncSession, report_id: UUID, strategy_summary: str
    ) -> None:
        """Persist the planner's strategy summary onto a report."""
        try:
            await session.execute(
                update(UserReport)
                .where(UserReport.id == report_id)
                .values(strategy_summary=strategy_summary)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def save_report_content(
        self, session: AsyncSession, report_id: UUID, title: str, content: str
    ) -> None:
        """Persist the synthesised report title and markdown content."""
        try:
            await session.execute(
                update(UserReport)
                .where(UserReport.id == report_id)
                .values(report_title=title, report_content=content)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def delete_report(
        self, session: AsyncSession, report_id: UUID, user_id: UUID
    ) -> bool:
        """
        Delete a report owned by the given user.

        Returns True if a row was deleted, False if no matching row was found.
        """
        try:
            result = await session.execute(
                select(UserReport).where(
                    UserReport.id == report_id, UserReport.user_id == user_id
                )
            )
            report = result.scalar_one_or_none()
            if report is None:
                return False
            await session.delete(report)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            raise

    # --- reads ---

    async def get_report_by_id(
        self, session: AsyncSession, report_id: UUID
    ) -> UserReport | None:
        """Return the UserReport with the given id, or None if not found."""
        try:
            result = await session.execute(
                select(UserReport).where(UserReport.id == report_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            await session.rollback()
            raise

    async def get_reports_by_user(
        self, session: AsyncSession, user_id: UUID, limit: int, offset: int
    ) -> list[tuple[UUID, str | None]]:
        """Return a paginated list of (id, report_title) tuples for a user, newest first."""
        try:
            result = await session.execute(
                select(UserReport.id, UserReport.report_title, UserReport.status)
                .where(UserReport.user_id == user_id)
                .order_by(UserReport.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.all())
        except Exception:
            await session.rollback()
            raise

    async def get_report_status(
        self, session: AsyncSession, report_id: UUID
    ) -> str | None:
        """Return just the status string for a report, or None if not found."""
        try:
            result = await session.execute(
                select(UserReport.status).where(UserReport.id == report_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            await session.rollback()
            raise


reports_service = UserReportService()
