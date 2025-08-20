from os import getenv
from web3 import Web3, AsyncWeb3

BESU_RPC_HOST = getenv("BESU_RPC_HOST", "localhost")
BESU_RPC_PORT = getenv("BESU_RPC_PORT", "8545")

def get_web3_client() -> AsyncWeb3:
    return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(f"http://{BESU_RPC_HOST}:{BESU_RPC_PORT}"))

async def is_besu_connected():
    w3 = get_web3_client()
    return {"status": "ok"} if await w3.is_connected() else {"status": "error"}