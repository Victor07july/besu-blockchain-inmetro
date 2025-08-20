from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Header
from src.users.service import check_authorization
from src.besu.services import is_besu_connected
from src.besu.schemas import BesuStatus

besu_v1_router = APIRouter(prefix="/v1/besu")

@besu_v1_router.get("/connected/", response_model=BesuStatus, status_code=HTTPStatus.OK)
async def is_connected(authorization: Annotated[str | None, Header()] = None,):
    is_authorized = await check_authorization(authorization)
    if is_authorized:
        return await is_besu_connected()
    return None