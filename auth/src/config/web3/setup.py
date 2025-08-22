from web3 import AsyncWeb3
from os import getenv

BESU_RPC_HOST = getenv("BESU_RPC_HOST", "localhost")
BESU_RPC_PORT = getenv("BESU_RPC_PORT", "8545")

def get_web3_client() -> AsyncWeb3:
    return AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(f"http://{BESU_RPC_HOST}:{BESU_RPC_PORT}"))