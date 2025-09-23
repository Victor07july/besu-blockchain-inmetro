from pydantic import BaseModel

class BesuStatus(BaseModel):
    status: str