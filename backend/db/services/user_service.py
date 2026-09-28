from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User


class UserService:
    def __init__(self) -> None:
        pass

    async def create_user(
        self, session: AsyncSession, username: str, email: str, password_hash: str
    ) -> User:
        """Insert a new user row and return the persisted instance."""
        try:
            user = User(username=username, email=email, password_hash=password_hash)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except Exception:
            await session.rollback()
            raise

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Return the User with the given email, or None if not found."""
        try:
            result = await session.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception:
            await session.rollback()
            raise

    async def email_exists(self, session: AsyncSession, email: str) -> bool:
        """Return True if a user with the given email already exists."""
        try:
            result = await session.execute(select(User.id).where(User.email == email))
            return result.scalar_one_or_none() is not None
        except Exception:
            await session.rollback()
            raise


users_service = UserService()
