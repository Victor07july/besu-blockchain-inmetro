import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version

async def test_deploy():
    # Conectar ao Besu
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("http://localhost:8547"))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    print(f"✅ Conectado ao Besu: {await w3.is_connected()}")
    print(f"📊 Block number: {await w3.eth.block_number}")
    
    latest_block = await w3.eth.get_block('latest')
    print(f"🔥 Block Gas Limit: {latest_block.gasLimit:,}")
    
    # Ler contrato
    with open('/home/inmetro/besu-starter-victor/contracts/CarbonCreditNFT_E2_Optimized.sol', 'r') as f:
        source_code = f.read()
    
    # Compilar
    print("\n🔨 Compilando contrato...")
    install_solc("0.8.20")
    set_solc_version("0.8.20")
    
    compiled_sol = compile_source(
        source_code,
        import_remappings=['@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts'],
        allow_paths='/usr/local/lib/node_modules'
    )
    
    # Pegar o maior bytecode (contrato principal)
    main_contract = max(compiled_sol.items(), key=lambda x: len(x[1]['bin']))
    contract_id, contract_interface = main_contract
    
    bytecode = contract_interface['bin']
    abi = contract_interface['abi']
    
    print(f"📦 Contrato: {contract_id}")
    print(f"📏 Bytecode size: {len(bytecode)} bytes")
    print(f"📋 Funções: {len(abi)} items na ABI")
    
    # Estimar gas
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Conta de teste
    private_key = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
    account = Account.from_key(private_key)
    
    print(f"\n💰 Account: {account.address}")
    print(f"💵 Balance: {await w3.eth.get_balance(account.address)}")
    
    # Tentar estimar gas
    try:
        print("\n⏳ Estimando gas necessário...")
        gas_estimate = await w3.eth.estimate_gas({
            'from': account.address,
            'data': '0x' + bytecode
        })
        print(f"⛽ Gas estimado: {gas_estimate:,}")
    except Exception as e:
        print(f"❌ Erro ao estimar gas: {e}")
        gas_estimate = 5000000  # Fallback
    
    # Deploy com gas razoável
    gas_limit = min(gas_estimate * 2, 20000000)  # Máximo 20M
    print(f"\n🚀 Tentando deploy com gas_limit: {gas_limit:,}")
    
    nonce = await w3.eth.get_transaction_count(account.address)
    chain_id = await w3.eth.chain_id
    gas_price = await w3.eth.gas_price
    
    transaction = await contract.constructor().build_transaction({
        'from': account.address,
        'gas': gas_limit,
        'gasPrice': gas_price,
        'nonce': nonce,
        'chainId': chain_id,
    })
    
    signed_txn = account.sign_transaction(transaction)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"📤 TX enviada: {tx_hash.hex()}")
    print(f"⏳ Aguardando confirmação...")
    
    tx_receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    print(f"\n{'='*60}")
    if tx_receipt.status == 1:
        print(f"✅ SUCESSO!")
        print(f"📍 Contract Address: {tx_receipt.contractAddress}")
        print(f"⛽ Gas usado: {tx_receipt.gasUsed:,} / {gas_limit:,}")
        print(f"📊 Utilização: {(tx_receipt.gasUsed / gas_limit * 100):.1f}%")
    else:
        print(f"❌ FALHOU!")
        print(f"⛽ Gas usado: {tx_receipt.gasUsed:,} / {gas_limit:,}")
        print(f"📊 Utilização: {(tx_receipt.gasUsed / gas_limit * 100):.1f}%")
        
        if tx_receipt.gasUsed >= gas_limit * 0.95:
            print(f"⚠️  OUT OF GAS - Contract muito grande ou loop infinito")
    
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(test_deploy())
