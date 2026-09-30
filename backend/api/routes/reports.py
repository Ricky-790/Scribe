import json
from time import monotonic
from types import SimpleNamespace
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.sse import EventSourceResponse, format_sse_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import (
    AuthenticatedUser,
    get_current_user,
    get_redis_client,
)
from backend.api.dto_models import (
    ReportResponse,
    ReportsListResponse,
    ReportStatusResponse,
    ReportSummary,
)
from backend.api.utils import attach_signed_url
from backend.db.models import RunStatus, UserReport
from backend.db.services.user_report_service import reports_service
from backend.db.session import async_session_factory, get_session

router = APIRouter()

# How often the stream re-reads the report status while no event has arrived.
STATUS_POLL_SECONDS = 2.0
# Idle time after which a comment-free keepalive event is sent, so proxies and
# load balancers do not drop a long-running stream.
KEEPALIVE_SECONDS = 15.0

TERMINAL_STATUSES = {RunStatus.DONE, RunStatus.FAILED}


def _report_channel(report_id: UUID) -> str:
    return f"report:{report_id}"


async def _signed_content(report_content: str | None) -> str:
    """Report markdown with diagram URLs signed, tolerating a storage outage."""
    raw = report_content or ""
    if not raw:
        return ""
    try:
        return await attach_signed_url(raw)
    except Exception:
        # A Supabase failure must not make an otherwise readable report
        # unavailable; serve the markdown with the placeholders left in place.
        return raw


async def _build_report_response(report: UserReport) -> ReportResponse:
    """
    Map a completed report row to its API response, signing image URLs.

    Every attribute is read here, so the caller must pass a row whose scalar
    fields are already materialised.
    """
    content = await _signed_content(report.report_content)
    return ReportResponse(
        report_id=report.id,
        goal=report.goal,
        intent=report.intent,
        categories=report.categories,
        strategy_summary=report.strategy_summary,
        title=report.report_title,
        content=content,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )


@router.get("/all", response_model=ReportsListResponse)
async def get_user_reports(
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReportsListResponse:
    """
    Return a paginated list of report summaries (id + title) for the
    authenticated user, ordered newest first.
    """
    rows = await reports_service.get_reports_by_user(
        session, user.user_id, limit=limit, offset=offset
    )
    return ReportsListResponse(
        reports=[
            ReportSummary(report_id=row[0], title=row[1], status=row[2]) for row in rows
        ],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse | ReportStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_report(
    report_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportResponse | ReportStatusResponse:
    """
    Return a single report.

    A finished report yields the full markdown body; anything else (including
    a failed run) yields just its status, so the caller can decide whether to
    stream live progress, render the report, or surface a failure.
    """
    report = await reports_service.get_report_by_id(session, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )

    if report.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )

    if report.status == RunStatus.DONE:
        return await _build_report_response(report)

    return ReportStatusResponse(
        report_id=report.id,
        status=report.status,
    )


@router.get("/{report_id}/stream")
async def stream_report_progress(
    report_id: UUID,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    redis_client=Depends(get_redis_client),
) -> EventSourceResponse:
    """
    Stream live progress for a report as Server-Sent Events.

    Emits:
      ``status`` — the current state, then one event per pipeline update
      ``report`` — the finished report, once the run reaches DONE
      ``error``  — why the run failed, if it did
      ``done``   — always the final event

    Redis pub/sub carries the events, but the database is the authority on
    *termination*: the loop re-checks the report status whenever the channel
    goes quiet. A client that connects after the last event was published
    therefore still receives the report instead of hanging.
    """
    # Authorize before opening a stream so a bad id or someone else's report
    # surfaces as a real HTTP status rather than an event inside a 200.
    async with async_session_factory() as session:
        report = await reports_service.get_report_by_id(session, report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )
        if report.user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found.",
            )
        initial_status = report.status

    # A projection, not a full ORM row: the poll runs for the life of the
    # stream and only needs these two facts.
    async def load_progress() -> tuple[str | None, bool]:
        """Return (status, has_body). status is None when the row is gone."""
        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(
                        UserReport.status, UserReport.report_content.isnot(None)
                    ).where(UserReport.id == report_id)
                )
            ).one_or_none()
            if row is None:
                return None, False
            return row[0], bool(row[1])

    async def load_report() -> UserReport | None:
        """
        Load a report as a detached snapshot of plain values.

        The session closes on return, which expires every attribute, so the
        fields are copied out while the row is still attached; otherwise the
        caller would get DetachedInstanceError on the first attribute read.
        """
        async with async_session_factory() as session:
            row = (
                await session.execute(
                    select(
                        UserReport.id,
                        UserReport.goal,
                        UserReport.intent,
                        UserReport.categories,
                        UserReport.strategy_summary,
                        UserReport.status,
                        UserReport.report_title,
                        UserReport.report_content,
                        UserReport.created_at,
                        UserReport.updated_at,
                    ).where(UserReport.id == report_id)
                )
            ).one_or_none()
            if row is None:
                return None
            keys = (
                "id",
                "goal",
                "intent",
                "categories",
                "strategy_summary",
                "status",
                "report_title",
                "report_content",
                "created_at",
                "updated_at",
            )
            return SimpleNamespace(**dict(zip(keys, row)))

    def is_final(status: str | None, has_body: bool) -> bool:
        """
        Whether a run has genuinely finished.

        DONE alone is not enough: the graph's terminal event flips the status
        before the markdown is written, so treating it as final here would hand
        the client an empty report. Waiting for the body is also what makes this
        stream immune to a `done` event arriving ahead of its own write.
        """
        if status == RunStatus.FAILED:
            return True
        return status == RunStatus.DONE and has_body

    async def events():
        channel = _report_channel(report_id)
        pubsub = redis_client.pubsub()

        if is_final(*await load_progress()):
            # Already finished — no need to subscribe at all.
            async for frame in _terminal_events(await load_report()):
                yield frame
            return

        await pubsub.subscribe(channel)
        last_poll = monotonic()
        last_keepalive = monotonic()
        force_check = False

        try:
            # Tell the client where the run stands before any live event, so a
            # client that attaches mid-run renders the correct step.
            yield _sse("status", {"report_id": str(report_id), "status": initial_status})

            while True:
                if await request.is_disconnected():
                    return

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message is not None:
                    payload = message["data"].decode()
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        event = {
                            "phase": "unknown",
                            "status": "update",
                            "msg": payload,
                        }
                    yield _sse("status", event)
                    # A terminal event means "re-check the database now" rather
                    # than "you may stop" — the body may not have landed yet.
                    force_check = bool(event.get("done"))
                    if not force_check:
                        continue

                now = monotonic()
                if not force_check and now - last_keepalive >= KEEPALIVE_SECONDS:
                    last_keepalive = now
                    yield _sse("ping")

                if force_check or now - last_poll >= STATUS_POLL_SECONDS:
                    force_check = False
                    last_poll = now
                    status, has_body = await load_progress()
                    if status is None:
                        yield _sse("error", {"message": "Report not found."})
                        yield _sse("done")
                        return
                    if is_final(status, has_body):
                        break

            async for frame in _terminal_events(await load_report()):
                yield frame
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return EventSourceResponse(events())


def _sse(event: str, data: object = None) -> bytes:
    """Encode one SSE frame.

    The handler builds its own response instead of using
    ``response_class=EventSourceResponse`` because that path requires the route
    function to be a generator, which would force authorization to run inside
    the stream (turning a 404 into a broken 200) rather than before it.
    """
    return format_sse_event(data_str=json.dumps(data), event=event)


async def _terminal_events(report: UserReport | None):
    """
    Yield the closing ``report``/``error``/``done`` sequence for a finished run.

    Takes a plain snapshot rather than an ORM row so nothing here can touch a
    detached instance, and so one Supabase failure cannot take down a report
    that is otherwise readable.
    """
    if report is None:
        yield _sse("error", {"message": "Report not found."})
        yield _sse("done")
        return

    if report.status == RunStatus.DONE and report.report_content:
        content = await _signed_content(report.report_content)
        yield _sse(
            "report",
            {
                "report_id": str(report.id),
                "goal": report.goal,
                "intent": report.intent,
                "categories": report.categories,
                "strategy_summary": report.strategy_summary,
                "title": report.report_title,
                "content": content,
                "created_at": report.created_at.isoformat(),
                "updated_at": report.updated_at.isoformat(),
            },
        )
    else:
        yield _sse(
            "error",
            {
                "message": "Report failed during processing.",
                "report_id": str(report.id),
            },
        )
    yield _sse("done")
