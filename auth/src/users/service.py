from src.core.exceptions import InvalidEmail, Unauthorized
from src.core.middlewares.authentication_middleware import validate_token
from src.core.middlewares.email_validator import validate_email
from src.core.middlewares.password_validator import validate_password
from src.core.models import User
from passlib.hash import pbkdf2_sha512

from src.core.repositories.users.user_base_repository import UserBaseRepository


async def check_authorization(authorization: str) -> bool:
    if authorization is None:
        raise Unauthorized()

    token = authorization.split()[1]
    await validate_token(token)

    return True


async def get_users(user_repo: UserBaseRepository) -> list[User]:
    user: list[User] = await user_repo.get_users()
    return user


async def get_user_by_email(
    email: str, user_repo: UserBaseRepository
) -> User | None:
    user: User = await user_repo.get_user_by_email(email)
    return user


async def create_user(
    email: str,
    password: str,
    user_repo: UserBaseRepository,
) -> User:
    validate_email(email)
    validate_password(password)
    user = await user_repo.get_user_by_email(email)
    if user is not None:
        raise InvalidEmail()

    hashed_password = pbkdf2_sha512.hash(password)
    return await user_repo.add_user(email=email, hashed_password=hashed_password)
