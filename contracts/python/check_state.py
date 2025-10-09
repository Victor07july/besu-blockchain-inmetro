import asyncio
from web3 import AsyncWeb3

async def check():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    
    block = await w3.eth.block_number
    print(f"Current block: {block}")
    
    # Check block 59 (deployment block)
    try:
        block_59 = await w3.eth.get_block(59, full_transactions=True)
        print(f"\n✅ Block 59 exists!")
        print(f"Transactions in block: {len(block_59.transactions)}")
        for tx in block_59.transactions:
            print(f"  - TX: {tx['hash'].hex()}")
    except Exception as e:
        print(f"\n❌ Block 59 not found: {e}")
        print("⚠️  Blockchain was likely restarted!")

asyncio.run(check())
