#!/usr/bin/env python3
"""
Script para interagir com o CarbonCreditNFT_E2 já deployado
Execução: python3 interact_carbon_e2.py
"""

import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# ===== CONFIGURAÇÕES =====
# Endereço do contrato que você acabou de fazer deploy
CONTRACT_ADDRESS = "0x9B8397f1B0FEcD3a1a40CdD5E8221Fa461898517"

# RPC do Besu
BESU_RPC_URL = "http://localhost:8547"  # rpcnode-user (SEM autenticação)
# BESU_RPC_URL = "http://localhost:8545"  # rpcnode-admin (COM autenticação JWT)

# Chave privada (substitua pela sua)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# ABI simplificada do contrato (funções principais)
CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "bool", "name": "status", "type": "bool"}],
        "name": "setAuthorized",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "nextTokenId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "highwayDistance", "type": "uint256"},
                    {"internalType": "uint256", "name": "cityDistance", "type": "uint256"},
                    {"internalType": "uint256", "name": "ethanolPercent", "type": "uint256"},
                    {"internalType": "uint256", "name": "roadGasoline", "type": "uint256"},
                    {"internalType": "uint256", "name": "roadEthanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "cityGasoline", "type": "uint256"},
                    {"internalType": "uint256", "name": "cityEthanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "precoGasolina", "type": "uint256"},
                    {"internalType": "uint256", "name": "precoEtanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "behaviorCautious", "type": "uint256"},
                    {"internalType": "uint256", "name": "behaviorNormal", "type": "uint256"},
                    {"internalType": "uint256", "name": "behaviorAggressive", "type": "uint256"}
                ],
                "internalType": "struct CarbonCreditNFT_E2Calculator.CalculationParams",
                "name": "params",
                "type": "tuple"
            },
            {"internalType": "address", "name": "recipient", "type": "address"}
        ],
        "name": "calculateE2AndTokenize",
        "outputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "uint256", "name": "e2Value", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "getCalculationDetails",
        "outputs": [
            {
                "components": [
                    {"internalType": "uint256", "name": "tanqueGasoline", "type": "uint256"},
                    {"internalType": "uint256", "name": "dtEstradaGasolina", "type": "uint256"},
                    {"internalType": "uint256", "name": "dtEstradaEtanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "dfEstrada", "type": "uint256"},
                    {"internalType": "uint256", "name": "dtCidadeGasolina", "type": "uint256"},
                    {"internalType": "uint256", "name": "dtCidadeEtanol", "type": "uint256"},
                    {"internalType": "uint256", "name": "dfCidade", "type": "uint256"},
                    {"internalType": "uint256", "name": "propBonus", "type": "uint256"},
                    {"internalType": "uint256", "name": "e2Final", "type": "uint256"},
                    {"internalType": "uint256", "name": "totalDistance", "type": "uint256"}
                ],
                "internalType": "struct CarbonCreditNFT_E2Calculator.CalculationResult",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getContractBalance",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "e2Value", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "totalDistance", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
        ],
        "name": "E2Calculated",
        "type": "event"
    }
]


async def main():
    """Função principal"""
    print("=" * 80)
    print("🌱 INTERAÇÃO COM CARBON CREDIT NFT E2")
    print("=" * 80)
    
    # Conectar ao Besu
    print(f"\n🔌 Conectando ao Besu: {BESU_RPC_URL}")
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    
    # Adicionar middleware para redes PoA
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    connected = await w3.is_connected()
    if not connected:
        print("❌ Erro: Não foi possível conectar ao Besu!")
        return
    
    print("✅ Conectado ao Besu!")
    chain_id = await w3.eth.chain_id
    block_number = await w3.eth.block_number
    print(f"🔗 Chain ID: {chain_id}")
    print(f"📦 Bloco atual: {block_number}")
    
    # Configurar conta
    if not PRIVATE_KEY.startswith('0x'):
        private_key = '0x' + PRIVATE_KEY
    else:
        private_key = PRIVATE_KEY
    
    account = Account.from_key(private_key)
    user_address = account.address
    print(f"👤 Seu endereço: {user_address}")
    
    balance = await w3.eth.get_balance(user_address)
    print(f"💰 Saldo: {w3.from_wei(balance, 'ether')} ETH")
    
    # Criar instância do contrato
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    
    # 1. Verificar owner
    print("\n" + "=" * 80)
    print("1️⃣ VERIFICANDO OWNER DO CONTRATO")
    print("=" * 80)
    owner = await contract.functions.owner().call()
    print(f"Owner: {owner}")
    print(f"É você? {'✅ Sim' if owner.lower() == user_address.lower() else '❌ Não'}")
    
    # 2. Verificar próximo token ID
    print("\n" + "=" * 80)
    print("2️⃣ VERIFICANDO PRÓXIMO TOKEN ID")
    print("=" * 80)
    next_token = await contract.functions.nextTokenId().call()
    print(f"Próximo Token ID: {next_token}")
    
    # 3. Verificar saldo do contrato
    print("\n" + "=" * 80)
    print("3️⃣ VERIFICANDO SALDO DO CONTRATO")
    print("=" * 80)
    contract_balance = await contract.functions.getContractBalance().call()
    print(f"Saldo: {w3.from_wei(contract_balance, 'ether')} ETH")
    
    # 4. Autorizar sua conta (se você for owner)
    if owner.lower() == user_address.lower():
        print("\n" + "=" * 80)
        print("4️⃣ AUTORIZANDO SUA CONTA")
        print("=" * 80)
        
        nonce = await w3.eth.get_transaction_count(user_address)
        gas_price = await w3.eth.gas_price
        
        txn = await contract.functions.setAuthorized(user_address, True).build_transaction({
            'from': user_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': gas_price,
            'chainId': chain_id,
        })
        
        signed_txn = account.sign_transaction(txn)
        tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"📤 Transação enviada: {tx_hash.hex()}")
        
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            print(f"✅ Autorização concedida!")
            print(f"⛽ Gas usado: {receipt.gasUsed}")
        else:
            print("❌ Falha na autorização")
    
    # 5. Calcular E2 e criar NFT
    print("\n" + "=" * 80)
    print("5️⃣ CALCULANDO E2 E CRIANDO NFT")
    print("=" * 80)
    
    # Parâmetros de exemplo (valores * 1e6 para precisão)
    params = {
        'highwayDistance': 100 * 1_000_000,      # 100 km
        'cityDistance': 50 * 1_000_000,          # 50 km
        'ethanolPercent': 30 * 1_000_000,        # 30% etanol
        'roadGasoline': 12 * 1_000_000,          # 12 km/L
        'roadEthanol': 10 * 1_000_000,           # 10 km/L
        'cityGasoline': 10 * 1_000_000,          # 10 km/L
        'cityEthanol': 8 * 1_000_000,            # 8 km/L
        'precoGasolina': 6 * 1_000_000,          # R$ 6,00/L
        'precoEtanol': 4 * 1_000_000,            # R$ 4,00/L
        'behaviorCautious': 50 * 1_000_000,      # 50% cautious
        'behaviorNormal': 40 * 1_000_000,        # 40% normal
        'behaviorAggressive': 10 * 1_000_000     # 10% aggressive
    }
    
    print(f"📊 Parâmetros da viagem:")
    print(f"   Distância estrada: {params['highwayDistance'] / 1_000_000} km")
    print(f"   Distância cidade: {params['cityDistance'] / 1_000_000} km")
    print(f"   Etanol: {params['ethanolPercent'] / 1_000_000}%")
    print(f"   Comportamento: {params['behaviorCautious'] / 1_000_000}% cautious, "
          f"{params['behaviorNormal'] / 1_000_000}% normal, "
          f"{params['behaviorAggressive'] / 1_000_000}% aggressive")
    
    nonce = await w3.eth.get_transaction_count(user_address)
    gas_price = await w3.eth.gas_price
    
    # Converter params para tupla
    params_tuple = tuple(params.values())
    
    txn = await contract.functions.calculateE2AndTokenize(
        params_tuple,
        user_address
    ).build_transaction({
        'from': user_address,
        'nonce': nonce,
        'gas': 500000,
        'gasPrice': gas_price,
        'chainId': chain_id,
    })
    
    signed_txn = account.sign_transaction(txn)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"\n📤 Transação enviada: {tx_hash.hex()}")
    
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"✅ NFT criado com sucesso!")
        print(f"⛽ Gas usado: {receipt.gasUsed}")
        
        # Extrair eventos
        event_signature = w3.keccak(text="E2Calculated(address,uint256,uint256,uint256,uint256)").hex()
        for log in receipt.logs:
            if log.topics[0].hex() == event_signature:
                token_id = int.from_bytes(log.topics[2], byteorder='big')
                e2_value = int.from_bytes(log.data[0:32], byteorder='big')
                total_distance = int.from_bytes(log.data[32:64], byteorder='big')
                
                print(f"\n🎫 Token ID: {token_id}")
                print(f"📈 Valor E2: {e2_value / 1_000_000:.2f}")
                print(f"🛣️  Distância total: {total_distance / 1_000_000:.2f} km")
                
                # 6. Buscar detalhes do cálculo
                print("\n" + "=" * 80)
                print("6️⃣ DETALHES DO CÁLCULO")
                print("=" * 80)
                
                details = await contract.functions.getCalculationDetails(token_id).call()
                print(f"Tanque gasolina: {details[0] / 1_000_000:.2f}%")
                print(f"Custo estrada: {details[3] / 1_000_000:.6f} BRL")
                print(f"Custo cidade: {details[6] / 1_000_000:.6f} BRL")
                print(f"Bônus: {details[7] / 1_000_000:.2f}x")
                print(f"E2 Final: {details[8] / 1_000_000:.6f}")
    else:
        print("❌ Falha ao criar NFT")
    
    print("\n" + "=" * 80)
    print("✅ TESTE CONCLUÍDO!")
    print("=" * 80)
    print(f"\n📍 Contrato: {CONTRACT_ADDRESS}")
    print(f"🎮 Você pode continuar interagindo com este endereço")


if __name__ == "__main__":
    asyncio.run(main())
