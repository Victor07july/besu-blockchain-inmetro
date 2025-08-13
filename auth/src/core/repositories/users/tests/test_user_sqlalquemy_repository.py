import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.models import User
from src.core.repositories.users.user_sqlalquemy_repository import (
    UserSQLAlchemyRepository,
)


class TestUserSQLAlchemyRepository:

    @pytest.mark.asyncio
    async def test_get_users_returns_list_of_users(self, db_session: AsyncSession):
        # Arrange
        # Create users for test
        user1 = User(email="test1@email.com", hashed_password="hashedpass1")
        user2 = User(email="test2@email.com", hashed_password="hashedpass2")
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()

        repository = UserSQLAlchemyRepository(db_session)

        # Act
        users = await repository.get_users()

        # Assert
        assert len(users) == 2
        assert any(u.email == "test1@email.com" for u in users)
        assert any(u.email == "test2@email.com" for u in users)

    @pytest.mark.asyncio
    async def test_get_user_by_email_returns_correct_user(
        self, db_session: AsyncSession
    ):
        # Arrange
        email = "specific@email.com"
        user = User(email=email, hashed_password="hashedpass")
        db_session.add(user)
        await db_session.commit()

        repository = UserSQLAlchemyRepository(db_session)

        # Act
        found_user = await repository.get_user_by_email(email)

        # Assert
        assert found_user is not None
        assert found_user.email == email

    @pytest.mark.asyncio
    async def test_get_user_by_email_returns_none_for_nonexistent_user(
        self, db_session: AsyncSession
    ):
        # Arrange
        repository = UserSQLAlchemyRepository(db_session)

        # Act
        found_user = await repository.get_user_by_email("nonexistent@email.com")

        # Assert
        assert found_user is None

    @pytest.mark.asyncio
    async def test_add_user_creates_new_user(self, db_session: AsyncSession):
        # Arrange
        repository = UserSQLAlchemyRepository(db_session)
        email = "new@email.com"
        hashed_password = "hashedpassword123"

        # Act
        created_user = await repository.add_user(email, hashed_password)

        # Verify directly from database to ensure it was saved
        result = await db_session.execute(select(User).where(User.email == email))
        db_user = result.scalar_one_or_none()

        # Assert
        assert created_user is not None
        assert created_user.email == email
        assert created_user.hashed_password == hashed_password

        assert db_user is not None
        assert db_user.email == email
        assert db_user.hashed_password == hashed_password

    @pytest.mark.asyncio
    async def test_add_user_with_existing_email_raises_exception(
        self, db_session: AsyncSession
    ):
        # Arrange
        email = "duplicate@email.com"
        user = User(email=email, hashed_password="original_hash")
        db_session.add(user)
        await db_session.commit()

        repository = UserSQLAlchemyRepository(db_session)

        # Act & Assert
        with pytest.raises(Exception):
            await repository.add_user(email, "new_hash")
