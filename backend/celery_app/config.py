import os

from celery import Celery

REDIS_BROKER_URL = os.getenv("REDIS_BROKER_URL", "redis://localhost:6379/0")
REDIS_RESULT_BACKEND = os.getenv("REDIS_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "agents_service_backend",
    broker=REDIS_BROKER_URL,  # where to send and read task messages.
    backend=REDIS_RESULT_BACKEND,  # where to store task results/state
    include=["backend.celery_app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
)
