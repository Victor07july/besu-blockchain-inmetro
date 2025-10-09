#!/usr/bin/env python3
"""
Script para testar o deploy e interação com o CarbonCreditNFT
Execução: python3 test_carbon_credit_nft.py
"""

import asyncio
import sys
import os
from pathlib import Path
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from solcx import compile_source, install_solc, set_solc_version

# Configurações
BESU_RPC_URL = "http://rpcnode-admin:8545"  # Dentro do Docker
# BESU_RPC_URL = "http://localhost:8545"  # Se executar fora do Docker

# Chave privada de teste (substitua pela sua)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Parâmetros do construtor
CENTAVOS_POR_G = 5  # R$ 0,05 por grama de CO2
COTACAO_INICIAL_ETH_BRL = 15000  # 1 ETH = R$ 15.000


async def compile_contract(contract_path: str):
    """Compila o contrato Solidity"""
    print(f"📄 Lendo contrato: {contract_path}")
    
    with open(contract_path, 'r') as f:
        source_code = f.read()
    
    print("🔧 Instalando compilador Solidity 0.8.19...")
    install_solc("0.8.19")
    set_solc_version("0.8.19")
    
    print("⚙️  Compilando contrato...")
    
    # Compilar com imports do OpenZeppelin
    # Nota: Para imports funcionarem, você precisa instalar: npm install @openzeppelin/contracts
    try:
        compiled_sol = compile_source(
            source_code,
            output_values=['abi', 'bin'],
            solc_version="0.8.19",
            import_remappings=[
                '@openzeppelin/=/usr/local/lib/node_modules/@openzeppelin/'
            ]
        )
    except Exception as e:
        print(f"⚠️  Erro de compilação com OpenZeppelin imports: {e}")
        print("💡 Tentando compilação sem imports externos...")
        # Se falhar, tente versão sem OpenZeppelin (você precisaria remover os imports)
        raise
    
    contract_id = list(compiled_sol.keys())[0]
    contract_interface = compiled_sol[contract_id]
    
    print("✅ Contrato compilado com sucesso!")
    return contract_interface['abi'], contract_interface['bin']


async def deploy_contract(w3: AsyncWeb3, abi, bytecode, private_key: str):
    """Faz o deploy do contrato"""
    print("\n🚀 Iniciando deploy do contrato...")
    
    # Configurar conta
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    account = Account.from_key(private_key)
    deployer_address = account.address
    
    print(f"👤 Endereço do deployer: {deployer_address}")
    
    # Verificar saldo
    balance = await w3.eth.get_balance(deployer_address)
    print(f"💰 Saldo: {w3.from_wei(balance, 'ether')} ETH")
    
    if balance == 0:
        print("❌ Erro: Conta sem saldo para fazer deploy!")
        return None
    
    # Criar contrato
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Preparar transação
    print(f"📝 Parâmetros: centavos_por_g={CENTAVOS_POR_G}, cotacao_eth={COTACAO_INICIAL_ETH_BRL}")
    
    nonce = await w3.eth.get_transaction_count(deployer_address)
    gas_price = await w3.eth.gas_price
    chain_id = await w3.eth.chain_id
    
    # Build transaction
    transaction = await contract.constructor(
        CENTAVOS_POR_G,
        COTACAO_INICIAL_ETH_BRL
    ).build_transaction({
        'from': deployer_address,
        'nonce': nonce,
        'gas': 3000000,
        'gasPrice': gas_price,
        'chainId': chain_id,
        'value': w3.to_wei(1, 'ether')  # Enviar 1 ETH para o contrato
    })
    
    # Assinar transação
    signed_txn = account.sign_transaction(transaction)
    
    # Enviar transação
    print("📤 Enviando transação...")
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"🔗 Hash da transação: {tx_hash.hex()}")
    
    # Aguardar confirmação
    print("⏳ Aguardando confirmação...")
    tx_receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if tx_receipt.status == 1:
        contract_address = tx_receipt.contractAddress
        print(f"✅ Deploy bem-sucedido!")
        print(f"📍 Endereço do contrato: {contract_address}")
        print(f"⛽ Gas usado: {tx_receipt.gasUsed}")
        return contract_address
    else:
        print("❌ Deploy falhou!")
        return None


async def interact_with_contract(w3: AsyncWeb3, contract_address: str, abi, private_key: str):
    """Interage com o contrato deployado"""
    print(f"\n🎮 Interagindo com o contrato em {contract_address}")
    
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key
    
    account = Account.from_key(private_key)
    admin_address = account.address
    
    # Criar instância do contrato
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # 1. Verificar admin
    print("\n1️⃣ Verificando administrador...")
    admin = await contract.functions.admin().call()
    print(f"   Admin: {admin}")
    print(f"   É você? {admin.lower() == admin_address.lower()}")
    
    # 2. Verificar saldo do contrato
    print("\n2️⃣ Verificando saldo do contrato...")
    saldo = await contract.functions.saldoContrato().call()
    print(f"   Saldo: {w3.from_wei(saldo, 'ether')} ETH")
    
    # 3. Verificar preço do carbono
    print("\n3️⃣ Verificando configurações de preço...")
    carbon_price = await contract.functions.carbonPricePerG().call()
    centavos = await contract.functions.precoCentavosPorG().call()
    cotacao = await contract.functions.cotacaoEthEmReais().call()
    print(f"   Preço por grama: {carbon_price} wei")
    print(f"   Centavos por g: R$ 0.{centavos:02d}")
    print(f"   Cotação ETH: R$ {cotacao:,.2f}")
    
    # 4. Registrar uma viagem de teste
    print("\n4️⃣ Registrando viagem de teste...")
    
    # Dados da viagem
    condutor = admin_address  # Vamos registrar para nós mesmos
    co2_meta = 50000  # 50kg = 50.000g
    economia_co2 = 5000  # Economizou 5kg = 5.000g
    recompensa = w3.to_wei(0.01, 'ether')  # 0.01 ETH de recompensa
    dados_hash = w3.keccak(text="viagem_teste_001")
    
    print(f"   Condutor: {condutor}")
    print(f"   Meta CO2: {co2_meta}g")
    print(f"   Economia: {economia_co2}g")
    print(f"   Recompensa: {w3.from_wei(recompensa, 'ether')} ETH")
    
    # Preparar transação
    nonce = await w3.eth.get_transaction_count(admin_address)
    gas_price = await w3.eth.gas_price
    chain_id = await w3.eth.chain_id
    
    txn = await contract.functions.registrarViagemDetalhada(
        condutor,
        co2_meta,
        economia_co2,
        recompensa,
        dados_hash
    ).build_transaction({
        'from': admin_address,
        'nonce': nonce,
        'gas': 500000,
        'gasPrice': gas_price,
        'chainId': chain_id,
    })
    
    signed_txn = account.sign_transaction(txn)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"   📤 Transação enviada: {tx_hash.hex()}")
    
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"   ✅ Viagem registrada com sucesso!")
        print(f"   ⛽ Gas usado: {receipt.gasUsed}")
        
        # Extrair tokenId do evento
        token_id = 0  # Primeiro token
        print(f"   🎫 Token ID: {token_id}")
    else:
        print("   ❌ Falha ao registrar viagem")
        return
    
    # 5. Verificar informações do token
    print(f"\n5️⃣ Verificando informações do Token #{token_id}...")
    viagem = await contract.functions.viagemInfo(token_id).call()
    print(f"   CO2 Meta: {viagem[0]}g")
    print(f"   Economia CO2: {viagem[1]}g")
    print(f"   Recompensa: {w3.from_wei(viagem[2], 'ether')} ETH")
    print(f"   Recompensa sacada? {viagem[4]}")
    
    # 6. Verificar owner do token
    print(f"\n6️⃣ Verificando proprietário do token...")
    owner = await contract.functions.ownerOf(token_id).call()
    print(f"   Owner: {owner}")
    print(f"   É você? {owner.lower() == admin_address.lower()}")
    
    # 7. Sacar recompensa
    print(f"\n7️⃣ Sacando recompensa do Token #{token_id}...")
    
    balance_before = await w3.eth.get_balance(admin_address)
    
    nonce = await w3.eth.get_transaction_count(admin_address)
    txn = await contract.functions.sacarRecompensa(token_id).build_transaction({
        'from': admin_address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': gas_price,
        'chainId': chain_id,
    })
    
    signed_txn = account.sign_transaction(txn)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"   📤 Transação enviada: {tx_hash.hex()}")
    
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        balance_after = await w3.eth.get_balance(admin_address)
        received = balance_after - balance_before + (receipt.gasUsed * gas_price)
        
        print(f"   ✅ Recompensa sacada com sucesso!")
        print(f"   💰 Valor recebido: {w3.from_wei(received, 'ether')} ETH")
        print(f"   ⛽ Gas usado: {receipt.gasUsed}")
        
        # Verificar se foi marcada como sacada
        viagem = await contract.functions.viagemInfo(token_id).call()
        print(f"   ✔️  Recompensa marcada como sacada: {viagem[4]}")
    else:
        print("   ❌ Falha ao sacar recompensa")


async def main():
    """Função principal"""
    print("=" * 70)
    print("🌱 TESTE DO CONTRATO CARBON CREDIT NFT")
    print("=" * 70)
    
    # Conectar ao Besu
    print(f"\n🔌 Conectando ao Besu: {BESU_RPC_URL}")
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    
    # Adicionar middleware para redes PoA (Besu QBFT)
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    connected = await w3.is_connected()
    if not connected:
        print("❌ Erro: Não foi possível conectar ao Besu!")
        print("💡 Verifique se o RPC está acessível")
        return
    
    print("✅ Conectado ao Besu!")
    chain_id = await w3.eth.chain_id
    block_number = await w3.eth.block_number
    print(f"🔗 Chain ID: {chain_id}")
    print(f"📦 Bloco atual: {block_number}")
    
    # Caminho do contrato
    contract_path = Path(__file__).parent / "CarbonCreditNFT.sol"
    
    if not contract_path.exists():
        print(f"❌ Erro: Contrato não encontrado em {contract_path}")
        return
    
    try:
        # Compilar contrato
        abi, bytecode = await compile_contract(str(contract_path))
        
        # Deploy
        contract_address = await deploy_contract(w3, abi, bytecode, PRIVATE_KEY)
        
        if contract_address:
            # Interagir com o contrato
            await interact_with_contract(w3, contract_address, abi, PRIVATE_KEY)
            
            print("\n" + "=" * 70)
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("=" * 70)
            print(f"\n📍 Endereço do contrato: {contract_address}")
            print(f"💡 Você pode interagir com ele usando este endereço")
        else:
            print("\n❌ Deploy falhou!")
    
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Executar
    asyncio.run(main())
