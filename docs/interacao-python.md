# 🐍 Guia de Interação com Contratos Solidity via Python

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Estrutura Básica](#estrutura-básica)
- [Configuração do Ambiente](#configuração-do-ambiente)
- [Anatomia do Script](#anatomia-do-script)
- [Adaptando para Novos Contratos](#adaptando-para-novos-contratos)
- [Exemplos Práticos](#exemplos-práticos)
- [Funções Avançadas](#funções-avançadas)
- [Troubleshooting](#troubleshooting)
- [Referências](#referências)

---

## 🎯 Visão Geral

Este guia ensina como **interagir com contratos Solidity** deployados no Besu usando **Python + Web3.py**.

### **O que você vai aprender:**
- ✅ Conectar ao Besu via RPC
- ✅ Criar instância de contrato com ABI
- ✅ Chamar funções `view` (leitura)
- ✅ Executar funções `nonpayable` (escrita)
- ✅ Assinar transações localmente
- ✅ Ler eventos emitidos
- ✅ Adaptar scripts para qualquer contrato

---

## 📁 Estrutura Básica

```python
#!/usr/bin/env python3
"""
Script de interação com contrato Solidity
"""
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# ===== CONFIGURAÇÕES =====
CONTRACT_ADDRESS = "0x..."     # Endereço do contrato deployado
BESU_RPC_URL = "http://localhost:8547"
PRIVATE_KEY = "sua_chave_privada"

# ===== ABI DO CONTRATO =====
CONTRACT_ABI = [...]  # ABI extraída da compilação

# ===== FUNÇÕES =====
async def main():
    # 1. Conectar ao Besu
    # 2. Criar instância do contrato
    # 3. Interagir (read/write)
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ⚙️ Configuração do Ambiente

### **1️⃣ Instalar Dependências**

```bash
pip install web3 eth-account asyncio
```

**Ou com requirements.txt:**

```txt
web3==6.15.0
eth-account==0.11.0
```

```bash
pip install -r requirements.txt
```

### **2️⃣ Estrutura do Projeto**

```
projeto/
├── contracts/
│   ├── MeuContrato.sol          # Contrato Solidity
│   └── python/
│       ├── interact_contrato.py # Script de interação
│       └── requirements.txt     # Dependências
├── abi/
│   └── MeuContrato.json         # ABI do contrato (opcional)
└── .env                         # Variáveis de ambiente (opcional)
```

---

## 🔍 Anatomia do Script

### **Componentes Essenciais**

```python
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# ===== 1. CONFIGURAÇÕES =====
CONTRACT_ADDRESS = "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741"
BESU_RPC_URL = "http://localhost:8547"
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# ===== 2. ABI DO CONTRATO =====
# Copie do resultado da compilação (campo "abi")
CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    # ... mais funções
]

# ===== 3. FUNÇÃO PRINCIPAL =====
async def main():
    # Conectar ao Besu
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Verificar conexão
    connected = await w3.is_connected()
    if not connected:
        print("❌ Erro: Não foi possível conectar ao Besu!")
        return
    
    print("✅ Conectado ao Besu!")
    
    # Criar instância do contrato
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    
    # Sua conta
    account = Account.from_key(PRIVATE_KEY)
    user_address = account.address
    
    # ===== INTERAÇÕES =====
    # Exemplo: Ler função view
    owner = await contract.functions.owner().call()
    print(f"Owner: {owner}")
    
    # Exemplo: Executar função que modifica estado
    # (veremos abaixo)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔄 Adaptando para Novos Contratos

### **Passo 1: Obter ABI e Endereço**

Após fazer o deploy via API, você recebe:

```json
{
    "success": true,
    "contract_address": "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741",
    "compilation_output": {
        "abi": [...]  // ← COPIE ESTA PARTE
    }
}
```

### **Passo 2: Template Genérico**

Crie um arquivo base: `template_interact.py`

```python
#!/usr/bin/env python3
"""
Template genérico de interação com contratos Solidity
Adapte as seções marcadas com 🔧
"""
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

# ===== 🔧 CONFIGURAÇÕES - EDITE AQUI =====
CONTRACT_NAME = "MeuContrato"  # 🔧 Nome do seu contrato
CONTRACT_ADDRESS = "0x..."      # 🔧 Endereço após deploy
BESU_RPC_URL = "http://localhost:8547"
PRIVATE_KEY = "sua_chave_privada"  # 🔧 Sua chave privada

# ===== 🔧 ABI DO CONTRATO - COLE AQUI =====
CONTRACT_ABI = [
    # 🔧 Cole a ABI retornada pelo deploy
]


async def main():
    """Função principal de interação"""
    print("=" * 80)
    print(f"🔌 INTERAGINDO COM {CONTRACT_NAME}")
    print("=" * 80)
    
    # Conectar ao Besu
    print(f"\n🔌 Conectando ao Besu: {BESU_RPC_URL}")
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
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
    
    # ===== 🔧 ADICIONE SUAS INTERAÇÕES AQUI =====
    
    # Exemplo 1: Ler função view (não gasta gas)
    # result = await contract.functions.minhaFuncaoView().call()
    # print(f"Resultado: {result}")
    
    # Exemplo 2: Executar função que modifica estado (gasta gas)
    # await executar_transacao(w3, contract, account, chain_id)
    
    print("\n" + "=" * 80)
    print("✅ INTERAÇÃO CONCLUÍDA!")
    print("=" * 80)


async def executar_transacao(w3, contract, account, chain_id):
    """
    Template para executar transação (função que modifica estado)
    """
    print("\n📤 Executando transação...")
    
    nonce = await w3.eth.get_transaction_count(account.address)
    gas_price = await w3.eth.gas_price
    
    # 🔧 ADAPTE ESTA LINHA COM SUA FUNÇÃO
    txn = await contract.functions.minhaFuncao(param1, param2).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 500000,  # 🔧 Ajuste conforme necessário
        'gasPrice': gas_price,
        'chainId': chain_id,
    })
    
    # Assinar e enviar
    signed_txn = account.sign_transaction(txn)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"📤 Transação enviada: {tx_hash.hex()}")
    
    # Aguardar confirmação
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print(f"✅ Transação confirmada!")
        print(f"⛽ Gas usado: {receipt.gasUsed}")
        return receipt
    else:
        print("❌ Transação falhou")
        return None


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💡 Exemplos Práticos

### **Exemplo 1: Contrato SimpleStorage**

**Contrato:**
```solidity
pragma solidity ^0.8.19;

contract SimpleStorage {
    uint256 private value;
    
    function set(uint256 _value) public {
        value = _value;
    }
    
    function get() public view returns (uint256) {
        return value;
    }
}
```

**Script Python:**
```python
#!/usr/bin/env python3
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

CONTRACT_ADDRESS = "0x..."  # Endereço após deploy
BESU_RPC_URL = "http://localhost:8547"
PRIVATE_KEY = "sua_chave"

CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "get",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_value", "type": "uint256"}],
        "name": "set",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

async def main():
    # Setup
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    account = Account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    
    # 1. Ler valor atual
    print("\n📖 Lendo valor atual...")
    current_value = await contract.functions.get().call()
    print(f"Valor: {current_value}")
    
    # 2. Definir novo valor
    print("\n✏️ Definindo novo valor (42)...")
    nonce = await w3.eth.get_transaction_count(account.address)
    gas_price = await w3.eth.gas_price
    chain_id = await w3.eth.chain_id
    
    txn = await contract.functions.set(42).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': gas_price,
        'chainId': chain_id,
    })
    
    signed_txn = account.sign_transaction(txn)
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"📤 TX: {tx_hash.hex()}")
    
    receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Confirmado! Gas: {receipt.gasUsed}")
    
    # 3. Ler valor novamente
    print("\n📖 Lendo valor após update...")
    new_value = await contract.functions.get().call()
    print(f"Novo valor: {new_value}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### **Exemplo 2: ERC721 (NFT)**

**Script Python:**
```python
#!/usr/bin/env python3
import asyncio
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account

CONTRACT_ADDRESS = "0x..."
BESU_RPC_URL = "http://localhost:8547"
PRIVATE_KEY = "sua_chave"

# ABI com funções ERC721 básicas
CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

async def main():
    w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    account = Account.from_key(PRIVATE_KEY)
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
    
    # 1. Informações do contrato
    print("\n📋 Informações do NFT:")
    name = await contract.functions.name().call()
    symbol = await contract.functions.symbol().call()
    print(f"Nome: {name}")
    print(f"Símbolo: {symbol}")
    
    # 2. Saldo de NFTs do usuário
    print(f"\n💰 NFTs de {account.address}:")
    balance = await contract.functions.balanceOf(account.address).call()
    print(f"Quantidade: {balance}")
    
    # 3. Dono de um token específico
    if balance > 0:
        print(f"\n👤 Dono do Token #1:")
        try:
            owner = await contract.functions.ownerOf(1).call()
            print(f"Endereço: {owner}")
        except Exception as e:
            print(f"Token #1 não existe: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### **Exemplo 3: Contrato CarbonCreditNFT_E2 (Complexo)**

**Ver arquivo completo:** `/contracts/python/interact_carbon_e2.py`

**Destaques:**

```python
# 1. Chamar função com struct como parâmetro
params = {
    'highwayDistance': 100 * 1_000_000,
    'cityDistance': 50 * 1_000_000,
    # ... 12 parâmetros no total
}

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

# 2. Extrair eventos do receipt
event_signature = w3.keccak(text="E2Calculated(address,uint256,uint256,uint256,uint256)").hex()
for log in receipt.logs:
    if log.topics[0].hex() == event_signature:
        token_id = int.from_bytes(log.topics[2], byteorder='big')
        e2_value = int.from_bytes(log.data[0:32], byteorder='big')
        print(f"Token ID: {token_id}, E2: {e2_value}")

# 3. Ler mapping público
details = await contract.functions.tokenCalculations(token_id).call()
print(f"Tanque gasolina: {details[0] / 1_000_000:.2f}%")
print(f"Custo estrada: {details[3] / 1_000_000:.6f} BRL")
```

---

## 🚀 Funções Avançadas

### **1️⃣ Estimativa de Gas Dinâmica**

```python
async def estimar_gas(w3, contract, account, funcao, *args):
    """Estima gas necessário para uma transação"""
    try:
        gas_estimate = await contract.functions[funcao](*args).estimate_gas({
            'from': account.address
        })
        print(f"⛽ Gas estimado: {gas_estimate}")
        # Adicionar 20% de margem de segurança
        return int(gas_estimate * 1.2)
    except Exception as e:
        print(f"❌ Erro na estimativa: {e}")
        return 500000  # Fallback

# Uso:
gas = await estimar_gas(w3, contract, account, 'minhaFuncao', param1, param2)
```

---

### **2️⃣ Ler Eventos Históricos**

```python
async def ler_eventos(w3, contract, event_name, from_block=0, to_block='latest'):
    """Busca eventos emitidos pelo contrato"""
    event_filter = contract.events[event_name].create_filter(
        from_block=from_block,
        to_block=to_block
    )
    
    events = await event_filter.get_all_entries()
    
    print(f"\n📋 {len(events)} eventos '{event_name}' encontrados:")
    for event in events:
        print(f"Bloco {event.blockNumber}: {event.args}")
    
    return events

# Uso:
await ler_eventos(w3, contract, 'Transfer', from_block=0)
```

---

### **3️⃣ Monitorar Eventos em Tempo Real**

```python
async def monitorar_eventos(w3, contract, event_name):
    """Monitora novos eventos em tempo real"""
    print(f"👁️ Monitorando eventos '{event_name}'...")
    
    event_filter = contract.events[event_name].create_filter(
        from_block='latest'
    )
    
    while True:
        try:
            events = await event_filter.get_new_entries()
            for event in events:
                print(f"🔔 Novo evento: {event.args}")
            await asyncio.sleep(2)  # Verificar a cada 2 segundos
        except KeyboardInterrupt:
            print("\n⏹️ Monitoramento interrompido")
            break

# Uso:
await monitorar_eventos(w3, contract, 'Transfer')
```

---

### **4️⃣ Batch de Transações**

```python
async def executar_batch(w3, contract, account, chain_id, funcoes):
    """Executa múltiplas transações em sequência"""
    nonce = await w3.eth.get_transaction_count(account.address)
    gas_price = await w3.eth.gas_price
    
    receipts = []
    
    for i, (funcao, args) in enumerate(funcoes):
        print(f"\n📤 Transação {i+1}/{len(funcoes)}: {funcao}")
        
        txn = await contract.functions[funcao](*args).build_transaction({
            'from': account.address,
            'nonce': nonce + i,  # Incrementar nonce
            'gas': 500000,
            'gasPrice': gas_price,
            'chainId': chain_id,
        })
        
        signed_txn = account.sign_transaction(txn)
        tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"TX: {tx_hash.hex()}")
        
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)
        receipts.append(receipt)
        print(f"✅ Confirmado! Gas: {receipt.gasUsed}")
    
    return receipts

# Uso:
funcoes = [
    ('set', [42]),
    ('set', [100]),
    ('set', [200]),
]
await executar_batch(w3, contract, account, chain_id, funcoes)
```

---

### **5️⃣ Tratamento de Erros Avançado**

```python
async def executar_transacao_segura(w3, contract, account, chain_id, funcao, *args):
    """Executa transação com tratamento robusto de erros"""
    try:
        nonce = await w3.eth.get_transaction_count(account.address)
        gas_price = await w3.eth.gas_price
        
        # Estimativa de gas
        try:
            gas_estimate = await contract.functions[funcao](*args).estimate_gas({
                'from': account.address
            })
            gas = int(gas_estimate * 1.2)
        except Exception as e:
            print(f"⚠️ Aviso: Falha na estimativa de gas. Usando padrão.")
            gas = 500000
        
        txn = await contract.functions[funcao](*args).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': gas,
            'gasPrice': gas_price,
            'chainId': chain_id,
        })
        
        signed_txn = account.sign_transaction(txn)
        tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"📤 TX enviada: {tx_hash.hex()}")
        
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print(f"✅ Sucesso! Gas: {receipt.gasUsed}")
            return {'success': True, 'receipt': receipt}
        else:
            print(f"❌ Transação revertida")
            return {'success': False, 'receipt': receipt}
            
    except ValueError as e:
        # Erro de validação (ex: require falhou)
        print(f"❌ Erro de validação: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        # Erro genérico
        print(f"❌ Erro inesperado: {e}")
        return {'success': False, 'error': str(e)}

# Uso:
result = await executar_transacao_segura(
    w3, contract, account, chain_id,
    'minhaFuncao', param1, param2
)
```

---

## 🐛 Troubleshooting

### **Erro: "AttributeError: 'AsyncWeb3' object has no attribute 'from_wei'"**

**Causa:** Método síncrono em contexto assíncrono.

**Solução:**
```python
# ❌ Errado
balance_eth = await w3.from_wei(balance, 'ether')

# ✅ Correto
balance_eth = w3.from_wei(balance, 'ether')  # Sem await
```

---

### **Erro: "ExtraDataLengthError"**

**Causa:** Middleware POA não injetado.

**Solução:**
```python
from web3.middleware import ExtraDataToPOAMiddleware

w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BESU_RPC_URL))
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)  # ← Adicionar
```

---

### **Erro: "Transaction nonce is too low"**

**Causa:** Nonce desatualizado (transação duplicada).

**Solução:**
```python
# Sempre obter nonce fresco antes de cada transação
nonce = await w3.eth.get_transaction_count(account.address, 'pending')
```

---

### **Erro: "Insufficient funds for gas * price + value"**

**Causa:** Saldo insuficiente na conta.

**Solução:**
```python
# Verificar saldo antes de transacionar
balance = await w3.eth.get_balance(account.address)
print(f"Saldo: {w3.from_wei(balance, 'ether')} ETH")

# Estimar custo total
gas = 500000
gas_price = await w3.eth.gas_price
custo_total = gas * gas_price
print(f"Custo estimado: {w3.from_wei(custo_total, 'ether')} ETH")
```

---

### **Erro: "execution reverted" (sem mensagem)**

**Causa:** Contrato reverteu mas não tem mensagem de erro.

**Solução para debug:**
```python
# 1. Testar com .call() antes de enviar
try:
    result = await contract.functions.minhaFuncao(param).call({
        'from': account.address
    })
    print(f"Simulação OK: {result}")
except Exception as e:
    print(f"❌ Simulação falhou: {e}")
    # Não enviar transação

# 2. Adicionar try-except ao redor de send_raw_transaction
try:
    tx_hash = await w3.eth.send_raw_transaction(signed_txn.raw_transaction)
except ValueError as e:
    print(f"❌ Erro ao enviar: {e}")
    # Analisar mensagem de erro
```

---

## 📊 Checklist de Adaptação

Ao adaptar o script para um novo contrato:

- [ ] **1. Obter informações do deploy:**
  - [ ] Contract Address
  - [ ] ABI completa
  - [ ] Endereço da conta owner

- [ ] **2. Configurar script:**
  - [ ] Atualizar `CONTRACT_ADDRESS`
  - [ ] Colar `CONTRACT_ABI`
  - [ ] Configurar `PRIVATE_KEY`
  - [ ] Verificar `BESU_RPC_URL`

- [ ] **3. Identificar funções do contrato:**
  - [ ] Listar funções `view` (leitura)
  - [ ] Listar funções `nonpayable` (escrita)
  - [ ] Verificar parâmetros de cada função
  - [ ] Identificar eventos emitidos

- [ ] **4. Adaptar interações:**
  - [ ] Criar função para cada operação
  - [ ] Configurar gas adequado
  - [ ] Tratar erros específicos
  - [ ] Adicionar logs/prints

- [ ] **5. Testar:**
  - [ ] Testar funções view primeiro
  - [ ] Testar uma transação simples
  - [ ] Verificar eventos emitidos
  - [ ] Testar edge cases

---

## 🎓 Resumo Executivo

### **Workflow Completo**

```bash
# 1. Deploy do contrato (via API)
POST http://localhost/api/besu/deploy
# → Retorna: contract_address + abi

# 2. Copiar template
cp template_interact.py interact_meucontrato.py

# 3. Editar configurações
# - CONTRACT_ADDRESS
# - CONTRACT_ABI
# - PRIVATE_KEY

# 4. Adicionar suas funções específicas
# - Funções view (leitura)
# - Funções nonpayable (escrita)

# 5. Executar
python3 interact_meucontrato.py
```

---

## 📖 Referências

### **Documentação Oficial**
- [Web3.py Docs](https://web3py.readthedocs.io/)
- [Eth-Account Docs](https://eth-account.readthedocs.io/)
- [AsyncIO Python](https://docs.python.org/3/library/asyncio.html)

### **Exemplos do Projeto**
- Script completo: `/contracts/python/interact_carbon_e2.py`
- Template base: Use este documento como base

### **Ferramentas Úteis**
- [Remix IDE](https://remix.ethereum.org/) - Testar contratos
- [Besu JSON-RPC API](https://besu.hyperledger.org/public-networks/reference/api) - Referência de chamadas RPC

---

**Última atualização:** 09 de Outubro de 2025  
**Versão:** 1.0.0  
**Autor:** Sistema de Deploy Automatizado - Besu Starter

---

## 💡 Dica Final

**Sempre teste suas funções com `.call()` antes de enviar transações reais!**

```python
# ✅ Boa prática: Testar primeiro
try:
    result = await contract.functions.minhaFuncao(param).call()
    print(f"✅ Teste OK: {result}")
    
    # Se teste passou, enviar transação real
    txn = await contract.functions.minhaFuncao(param).build_transaction({...})
    # ... resto do código
except Exception as e:
    print(f"❌ Teste falhou: {e}")
```

Isso economiza gas e evita transações que irão falhar! 💰
