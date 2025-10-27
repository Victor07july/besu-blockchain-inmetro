"""
Script para interagir com o contrato SimpleStorage deployado

Funções disponíveis:
- get(): Retorna o valor armazenado
- set(value): Define um novo valor
- storedData: Variável pública (mesma coisa que get())
"""

import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# ===========================
# CONFIGURAÇÃO
# ===========================

# Endereço do contrato deployado
CONTRACT_ADDRESS = "0x4245CF4518CB2C280f5e9c6a03c90C147F80B4d9"

# RPC do Besu
BESU_RPC_URL = "http://localhost:8547"

# Sua chave privada (para enviar transações)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# ABI do SimpleStorage
ABI = [
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_initialValue",
                "type": "uint256"
            }
        ],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "sender",
                "type": "address"
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "value",
                "type": "uint256"
            }
        ],
        "name": "DataStored",
        "type": "event"
    },
    {
        "inputs": [],
        "name": "get",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "_value",
                "type": "uint256"
            }
        ],
        "name": "set",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "storedData",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


async def get_stored_value(contract):
    """
    Lê o valor armazenado (função VIEW - não gasta gas)
    """
    print("\n📖 Lendo valor armazenado...")
    
    # Método 1: usando get()
    value = await contract.functions.get().call()
    print(f"✅ Valor atual (via get()): {value}")
    
    # Método 2: usando storedData (variável pública)
    value2 = await contract.functions.storedData().call()
    print(f"✅ Valor atual (via storedData): {value2}")
    
    return value


async def set_new_value(w3, contract, account, new_value):
    """
    Define um novo valor (transação - gasta gas)
    """
    print(f"\n✏️  Definindo novo valor: {new_value}...")
    
    # Obter informações para a transação
    nonce = await w3.eth.get_transaction_count(account.address)
    gas_price = await w3.eth.gas_price
    chain_id = await w3.eth.chain_id
    
    # Estimar gas necessário
    gas_estimate = await contract.functions.set(new_value).estimate_gas({
        'from': account.address
    })
    
    print(f"   Gas estimado: {gas_estimate:,}")
    print(f"   Gas price: {w3.from_wei(gas_price, 'gwei')} Gwei")
    
    # Montar transação
    transaction = await contract.functions.set(new_value).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': gas_estimate + 10000,  # Margem de segurança
        'gasPrice': gas_price,
        'chainId': chain_id
    })
    
    # Assinar transação
    signed = account.sign_transaction(transaction)
    
    # Enviar transação
    print("   Enviando transação...")
    tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"   Hash: {tx_hash.hex()}")
    print("   Aguardando confirmação...")
    
    # Aguardar confirmação
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt['status'] == 1:
        print(f"✅ Transação confirmada!")
        print(f"   Gas usado: {receipt['gasUsed']:,}")
        print(f"   Bloco: {receipt['blockNumber']}")
        
        # Ler eventos emitidos
        print("\n📡 Eventos emitidos:")
        events = contract.events.DataStored().process_receipt(receipt)
        for event in events:
            print(f"   - DataStored: sender={event['args']['sender']}, value={event['args']['value']}")
        
        return receipt
    else:
        print("❌ Transação falhou!")
        return None


async def main():
    print("=" * 70)
    print("🔧 INTERAÇÃO COM SIMPLESTORAGE")
    print("=" * 70)
    
    # Conectar ao Besu
    print(f"\n📡 Conectando ao Besu em {BESU_RPC_URL}...")
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    
    # Adicionar middleware para Besu (PoA)
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not await w3.is_connected():
        print("❌ Não foi possível conectar ao Besu!")
        return
    
    print(f"✅ Conectado! Chain ID: {await w3.eth.chain_id}")
    
    # Criar conta
    account = Account.from_key(PRIVATE_KEY)
    print(f"👤 Conta: {account.address}")
    
    # Verificar saldo
    balance = await w3.eth.get_balance(account.address)
    print(f"💰 Saldo: {w3.from_wei(balance, 'ether')} ETH")
    
    # Criar instância do contrato
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
    print(f"📄 Contrato: {CONTRACT_ADDRESS}")
    
    # ===========================
    # 1. LER VALOR INICIAL
    # ===========================
    initial_value = await get_stored_value(contract)
    
    # ===========================
    # 2. DEFINIR NOVO VALOR
    # ===========================
    new_value = 999
    
    print("\n" + "=" * 70)
    response = input(f"Deseja definir o valor como {new_value}? (s/n): ")
    
    if response.lower() == 's':
        await set_new_value(w3, contract, account, new_value)
        
        # ===========================
        # 3. VERIFICAR NOVO VALOR
        # ===========================
        print("\n" + "=" * 70)
        print("🔍 Verificando valor após mudança...")
        final_value = await get_stored_value(contract)
        
        if final_value == new_value:
            print(f"\n✅ SUCESSO! Valor mudou de {initial_value} para {final_value}")
        else:
            print(f"\n⚠️  Valor esperado: {new_value}, mas obteve: {final_value}")
    else:
        print("\n⏭️  Operação cancelada.")
    
    print("\n" + "=" * 70)
    print("✨ Script finalizado!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
