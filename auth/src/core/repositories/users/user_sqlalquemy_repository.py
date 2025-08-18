from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config.database.setup import get_db_session
from src.core.models import User
from src.core.repositories.users.user_base_repository import UserBaseRepository


class UserSQLAlchemyRepository(UserBaseRepository):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_users(self) -> list[User]:
        result = await self.db_session.execute(select(User))
        user: list[User] = result.scalars().all()
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db_session.execute(
            select(User).where(User.email == email)
        )
        user: User = result.scalar_one_or_none()
        return user

    async def add_user(self, email: str, hashed_password: str):
        user = User(email=email, hashed_password=hashed_password)
        self.db_session.add(user)
        await self.db_session.commit()
        await self.db_session.refresh(user)
        return user


def get_user_repository(
    db_session: AsyncSession = Depends(get_db_session),
) -> UserBaseRepository:
    return UserSQLAlchemyRepository(db_session)
