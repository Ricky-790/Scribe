import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

load_dotenv()

pg_username = os.getenv("POSTGRES_USERNAME")
pg_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB_NAME")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

DATABASE_URL = (
    f"postgresql+asyncpg://{pg_username}:{pg_password}@{db_host}:{db_port}/{db_name}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
