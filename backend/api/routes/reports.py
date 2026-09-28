from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from backend.api.deps import (
    AuthenticatedUser,
    get_current_user,
    get_current_user_ws,
    get_redis_client,
)
from backend.api.dto_models import (
    ConnectionManager,
    PublishMessage,
    ReportResponse,
    ReportsListResponse,
    ReportStatusResponse,
    ReportSummary,
)
from backend.api.utils import attach_signed_url
from backend.celery_app.redis_client import client
from backend.db.models import RunStatus
from backend.db.services.user_report_service import reports_service
from backend.db.session import get_session

router = APIRouter()
# _report_service = UserReportService()
connection_manager = ConnectionManager()

@router.get("/all", response_model=ReportsListResponse)
async def get_user_reports(
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
    offset: int = 0,
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

    if report.status not in {RunStatus.DONE, RunStatus.FAILED}:
        # response.status_code = status.HTTP_202_ACCEPTED
        return ReportStatusResponse(
            report_id=report.id,
            status=report.status,
        )

    if report.status == RunStatus.DONE:
        try:
            formatted_content: str = await attach_signed_url(
                report.report_content if report.report_content else ""
            )
            return ReportResponse(
                report_id=report.id,
                goal=report.goal,
                intent=report.intent,
                categories=report.categories,
                strategy_summary=report.strategy_summary,
                title=report.report_title,
                content=formatted_content,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat(),
            )
        except:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    # RunStatus.FAILED or any unexpected value
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Report '{report_id}' failed during processing.",
    )





@router.websocket(
    "/ws/{report_id}"
)  # needs a dependency to check if user id has access to report id
async def websocket_endpoint(
    websocket: WebSocket,
    report_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user_ws),
    redis_client=Depends(get_redis_client),
    session: AsyncSession = Depends(get_session),
):
    report = await reports_service.get_report_by_id(session, report_id)
    if report is None or report.user_id != user.user_id:
        await websocket.close(code=1008)  # 1008: Policy violation
        return

    await connection_manager.connect(report_id, websocket)
    pubsub = redis_client.pubsub()  # fresh pubsub PER CONNECTION — still important
    await pubsub.subscribe(f"report:{report_id}")

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1
            )

            if message:
                publish_message = PublishMessage.model_validate_json(
                    message["data"].decode()
                )
                await connection_manager.send(report_id, publish_message)
                if publish_message.done:
                    await websocket.close()
                    break

    except WebSocketDisconnect:
        connection_manager.disconnect(report_id)
    finally:
        connection_manager.disconnect(report_id)
        await pubsub.unsubscribe(f"report:{report_id}")
        await pubsub.close()
