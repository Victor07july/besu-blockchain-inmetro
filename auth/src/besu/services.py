from os import getenv
from web3 import AsyncWeb3


async def is_besu_connected(w3: AsyncWeb3):
    return {"status": "ok"} if await w3.is_connected() else {"status": "error"}

