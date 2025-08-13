from datetime import datetime, timedelta
from http.client import UNAUTHORIZED

from dotenv import load_dotenv
from jose import JWTError, jwt, ExpiredSignatureError
from os import getenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from src.core.models import User

load_dotenv("src/config/.env")

JWT_SECRET = getenv("JWT_SECRET")
JWT_ALGORITHM = getenv("JWT_ALGORITHM")
JWT_EXPIRATION_DAYS = getenv("JWT_EXPIRATION_DAYS")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

context = CryptContext(
    schemes=["sha512_crypt"], deprecated="auto", default="sha512_crypt"
)


async def validate_token(access_token: str = Depends(oauth2_scheme)) -> User:
    try:
        payload = jwt.decode(access_token, key=JWT_SECRET, algorithms=[JWT_ALGORITHM])

        return User(
            id=payload["user_id"],
            email=payload["email"],
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=UNAUTHORIZED,
            detail="Credential expired",
            headers={"Authorization": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"Authorization": "Bearer"},
        )


async def create_token(user_id: int, username: str):
    expire = datetime.utcnow() + timedelta(days=int(JWT_EXPIRATION_DAYS))
    access_token = jwt.encode(
        {
            "user_id": user_id,
            "email": username,
            "exp": expire,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return access_token
