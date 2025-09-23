from http import HTTPStatus
from typing import Annotated
from web3 import AsyncWeb3

from fastapi import APIRouter, Header, Depends
from src.core.middlewares.authentication_middleware import check_authorization
from src.besu.services import is_besu_connected
from src.besu.schemas import BesuStatus
from src.config.web3.setup import get_web3_client

besu_v1_router = APIRouter(prefix="/v1/besu")

@besu_v1_router.get("/connected/", response_model=BesuStatus, status_code=HTTPStatus.OK)
async def is_connected(
        authorization: Annotated[str | None, Header()] = None, 
        web3_client: AsyncWeb3 = Depends(get_web3_client),
    ):
    is_authorized = await check_authorization(authorization)
    if is_authorized:
        return await is_besu_connected(web3_client)
    return None