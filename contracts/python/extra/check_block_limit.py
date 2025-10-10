import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware

async def check():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    latest_block = await w3.eth.get_block('latest')
    
    print(f"📊 CONFIGURAÇÃO DO BESU")
    print(f"=" * 60)
    print(f"🔥 Gas Limit do Bloco: {latest_block.gasLimit:,}")
    print(f"⛽ Gas Usado no Bloco: {latest_block.gasUsed:,}")
    print(f"📈 Utilização: {(latest_block.gasUsed / latest_block.gasLimit * 100):.2f}%")
    print()
    print(f"💡 Seu contrato precisa de ~12-15M gas")
    print(f"⚠️  Limite atual do bloco: {latest_block.gasLimit:,}")
    print()
    
    if latest_block.gasLimit < 15000000:
        print(f"❌ O block gas limit ({latest_block.gasLimit:,}) é menor que o necessário!")
        print(f"✅ Você precisa aumentar o gas limit dos blocos para pelo menos 20M")
    else:
        print(f"✅ O block gas limit é suficiente!")

asyncio.run(check())
