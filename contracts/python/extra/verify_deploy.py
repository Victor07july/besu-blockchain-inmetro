import asyncio
from web3 import AsyncWeb3

async def verify():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    
    addr = "0x9a3DBCa554e9f6b9257aAa24010DA8377C57c17e"
    code = await w3.eth.get_code(addr)
    
    print(f"✅ Contract address: {addr}")
    print(f"📦 Contract code length: {len(code)} bytes")
    print(f"✅ Contract deployed: {len(code) > 0}")

asyncio.run(verify())
