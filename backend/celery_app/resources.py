import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()


@asynccontextmanager  # implements aenter and aexit methods
async def pipeline_resources():
    """
    Creates DB engine + Redis client scoped to the CURRENT event loop,
    guarantees disposal on exit. Must only be entered inside a fresh
    asyncio.run() call — never reused across separate asyncio.run() calls.
    """
    pg_username = os.getenv("POSTGRES_USERNAME")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB_NAME")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    database_url = f"postgresql+asyncpg://{pg_username}:{pg_password}@{db_host}:{db_port}/{db_name}"

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    redis_client = redis.from_url(
        os.getenv("REDIS_BROKER_URL", "redis://localhost:6379/0")
    )

    try:
        yield session_factory, redis_client
    finally:
        await redis_client.aclose()
        await engine.dispose()
