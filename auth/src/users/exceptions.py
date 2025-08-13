from http import HTTPStatus
from fastapi import HTTPException


class UserNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=HTTPStatus.BAD_REQUEST, detail="User not found for given ID."
        )
