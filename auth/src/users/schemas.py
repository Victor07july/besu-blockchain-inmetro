from pydantic import BaseModel


class PostUser(BaseModel):
    id: int
    email: str


class ListUser(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_active: bool
