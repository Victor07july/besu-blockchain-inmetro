from pydantic import BaseModel


class PostUser(BaseModel):
    id: int
    email: str


class ListUser(BaseModel):
    id: int
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
