import json
from collections.abc import Awaitable, Callable

from langgraph.types import StreamWriter

from backend.api.dto_models import PublishMessage


class RedisStreamBridge:
    """
    Bridges LangGraph's streaming to your existing Redis pub/sub.
    Use inside nodes via StreamWriter for native LangGraph streaming,
    or collect events from astream_events in the Celery task.
    """

    def __init__(self, redis_client, report_id: str):
        self.redis = redis_client
        self.channel = f"report:{report_id}"

    async def publish(self, stream_message: PublishMessage):
        message = stream_message.model_dump_json()
        await self.redis.publish(self.channel, message)

    @staticmethod
    def make_on_task_update(publish_fn: Callable[..., Awaitable[None]]):
        """Factory matching your old Pipeline callback signature."""

        async def on_task_update(
            task_id: str, status: str, result: dict | None, task: str
        ):
            await publish_fn(
                phase="research",
                status=status,
                task=task,
                payload={"task_id": task_id, "result": result},
            )

        return on_task_update

    @staticmethod
    def make_on_stage_complete(publish_fn: Callable[..., Awaitable[None]]):
        """Factory matching your old Pipeline callback signature."""

        async def on_stage_complete(phase: str, status: str, **extra):
            await publish_fn(phase=phase, status=status, payload=extra)

        return on_stage_complete
