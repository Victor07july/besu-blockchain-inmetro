import asyncio
from web3 import AsyncWeb3

async def check():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    
    tx_hash = "0x7a155e5ec944abab6347777737b8fc48060bdcd5e24b6bf59a2a7a3c0deee291"
    
    try:
        receipt = await w3.eth.get_transaction_receipt(tx_hash)
        print("✅ Transaction found!")
        print(f"Status: {'SUCCESS' if receipt['status'] == 1 else 'FAILED'}")
        print(f"Contract Address: {receipt.get('contractAddress', 'None')}")
        print(f"Gas Used: {receipt['gasUsed']}")
        print(f"Block Number: {receipt['blockNumber']}")
    except Exception as e:
        print(f"❌ Transaction not found: {e}")

asyncio.run(check())
