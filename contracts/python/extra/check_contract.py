import asyncio
from web3 import AsyncWeb3

async def check():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    
    # Verifica se o contrato existe
    code = await w3.eth.get_code("0xa50a51c09a5c451C52BB714527E1974b686D8e77")
    print(f"Contract code length: {len(code)} bytes")
    print(f"Contract exists: {len(code) > 0}")
    
    if len(code) > 0:
        print(f"First 100 bytes: {code[:100].hex()}")

asyncio.run(check())
