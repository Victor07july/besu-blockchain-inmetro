# 🔐 Guia Completo: Deploy Seguro de Contratos (Arquitetura de 2 Etapas)

Este guia documenta o fluxo completo para fazer deploy de contratos Solidity de forma segura, onde **a chave privada NUNCA trafega na rede**.

---

## 📋 Índice

1. [Visão Geral do Fluxo](#visão-geral-do-fluxo)
2. [Etapa 1: Compilar Contrato](#etapa-1-compilar-contrato)
3. [Etapa 2: Assinar Transação Localmente](#etapa-2-assinar-transação-localmente)
4. [Etapa 3: Deploy com Transação Assinada](#etapa-3-deploy-com-transação-assinada)
5. [Etapa 4: Interagir com o Contrato](#etapa-4-interagir-com-o-contrato)
6. [Exemplos Completos](#exemplos-completos)
7. [Troubleshooting](#troubleshooting)

---

## 🔄 Visão Geral do Fluxo

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE DEPLOY SEGURO                       │
└─────────────────────────────────────────────────────────────────┘

1️⃣ COMPILAÇÃO (via API)
   Cliente ────[.sol file]────> API
   Cliente <───[bytecode+abi]── API

2️⃣ ASSINATURA (local - chave privada NÃO sai do computador)
   Cliente: Monta transação usando bytecode
   Cliente: Assina com chave privada localmente
   Cliente: Gera signed_transaction (hex)

3️⃣ DEPLOY (via API - apenas broadcast)
   Cliente ────[signed_tx]────> API
   API ────────[broadcast]────> Besu
   API <───────[receipt]─────── Besu
   Cliente <───[contract_addr]─ API

✅ RESULTADO: Contrato deployado SEM expor chave privada!
```

---

## Etapa 1: Compilar Contrato

### 🎯 Objetivo
Enviar o arquivo `.sol` para a API e receber o `bytecode` + `ABI` compilados.

### 📡 Requisição no Postman

#### **Configuração**

| Campo | Valor |
|-------|-------|
| **Método** | `POST` |
| **URL** | `http://localhost:8000/api/v1/besu/compile-contract/` |
| **Headers** | `Authorization: Bearer SEU_TOKEN_JWT` |
| **Body Type** | `form-data` |

#### **Body (form-data)**

| Key | Type | Value |
|-----|------|-------|
| `contract_file` | File | Selecione o arquivo `.sol` |

#### **Exemplo Visual (Postman)**

```
POST http://localhost:8000/api/v1/besu/compile-contract/

Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Body (form-data):
  contract_file: [Selecionar arquivo] SimpleStorage.sol
```

### ✅ Resposta Esperada

```json
{
    "success": true,
    "abi": [
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
            "anonymous": false,
            "inputs": [
                {
                    "indexed": true,
                    "internalType": "address",
                    "name": "sender",
                    "type": "address"
                },
                {
                    "indexed": false,
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
    ],
    "bytecode": "608060405234801561001057600080fd5b506040516102fb3803806102fb833981810160405281019061003291906100c8565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d198260405161007f9190610104565b60405180910390a25061011f565b600080fd5b6000819050919050565b6100a581610092565b81146100b057600080fd5b50565b6000815190506100c28161009c565b92915050565b6000602082840312156100de576100dd61008d565b5b60006100ec848285016100b3565b91505092915050565b6100fe81610092565b82525050565b600060208201905061011960008301846100f5565b92915050565b6101cd8061012e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c80632a1afcd91461004657806360fe47b1146100645780636d4ce63c14610080575b600080fd5b61004e61009e565b60405161005b919061011e565b60405180910390f35b61007e6004803603810190610079919061016a565b6100a4565b005b6100886100fc565b604051610095919061011e565b60405180910390f35b60005481565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d19826040516100f1919061011e565b60405180910390a250565b60008054905090565b6000819050919050565b61011881610105565b82525050565b6000602082019050610133600083018461010f565b92915050565b600080fd5b61014781610105565b811461015257600080fd5b50565b6000813590506101648161013e565b92915050565b6000602082840312156101805761017f610139565b5b600061018e84828501610155565b9150509291505056fea264697066735822122043071242007a81bc30e6ff73e1130c05b04bf48b08c4b2767bd490a8e0e601e964736f6c634300080a0033",
    "error_message": null
}
```

### 📝 O que Fazer com a Resposta

1. **Copie TODO o objeto `abi`** - você vai precisar para assinar a transação
2. **Copie o `bytecode`** - necessário para montar a transação de deploy
3. **Salve esses dados** - você vai usá-los no próximo passo

---

## Etapa 2: Assinar Transação Localmente

### 🎯 Objetivo
Usar o `bytecode` e `abi` recebidos para montar e assinar a transação **localmente**, sem enviar a chave privada pela rede.

### 🐍 Script Python: `sign_transaction.py`

#### **Localização**
```
/contracts/python/sign_transaction.py
```

#### **Configuração do Script**

Edite as seguintes variáveis no início do arquivo:

```python
# ===========================
# CONFIGURAÇÃO
# ===========================

# RPC do Besu
BESU_RPC_URL = "http://localhost:8547"

# Sua chave privada (NUNCA compartilhe!)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# Cole aqui o ABI que você recebeu do /compile-contract/
ABI = [
    # Cole TODO o array do ABI aqui
]

# Cole aqui o BYTECODE que você recebeu do /compile-contract/
BYTECODE = "608060405234801561001057600080fd5b50..."

# Parâmetros do construtor (ajuste conforme seu contrato)
# Para SimpleStorage que recebe _initialValue:
CONSTRUCTOR_PARAMS = [42]  # Valor inicial = 42
# Para contratos sem construtor ou sem parâmetros:
# CONSTRUCTOR_PARAMS = []

# Configurações de gas
GAS_LIMIT = 3000000  # 3 milhões (ajuste se necessário)
```

#### **Como Obter os Valores**

1. **ABI**: Copie do retorno do `/compile-contract/` (etapa anterior)
2. **BYTECODE**: Copie do retorno do `/compile-contract/` (etapa anterior)
3. **CONSTRUCTOR_PARAMS**: 
   - Verifique no código Solidity se o construtor precisa de parâmetros
   - Exemplo: `constructor(uint256 _initialValue)` → `CONSTRUCTOR_PARAMS = [42]`
   - Sem parâmetros: `constructor()` → `CONSTRUCTOR_PARAMS = []`

#### **Executar o Script**

```bash
cd /home/inmetro/besu-starter-victor/contracts/python
source myenv/bin/activate
python3 sign_transaction.py
```

### ✅ Saída Esperada

```
======================================================================
🔐 GERADOR DE TRANSAÇÃO ASSINADA PARA DEPLOY
======================================================================

📡 Conectando ao Besu em http://localhost:8547...
✅ Conectado! Chain ID: 1337

👤 Deployer: 0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73
💰 Saldo: 90000 ETH

🔧 Preparando dados da transação...
   Parâmetros do construtor: [42]

📋 Informações da transação:
   Nonce: 15
   Gas Limit: 3,000,000
   Gas Price: 0 Gwei
   Chain ID: 1337
   Custo estimado (máximo): 0 ETH

🔐 Assinando transação localmente...
✅ Transação assinada com sucesso!
   Hash (previsto): 0xc27c93e15461af21ee9058490dec2d23645712d0c3626ce84148be4848db6301

======================================================================
📋 COPIE OS DADOS ABAIXO PARA O POSTMAN
======================================================================

1️⃣ URL:
POST http://localhost:8000/api/v1/besu/deploy-signed/

2️⃣ Headers:
Authorization: Bearer SEU_TOKEN_JWT
Content-Type: application/json

3️⃣ Body (raw JSON):
{
  "signed_transaction": "f9036b0e80832dc6c08080b9031b608060405234801561001057600080fd5b506040516102fb3803806102fb833981810160405281019061003291906100c8565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d198260405161007f9190610104565b60405180910390a25061011f565b600080fd5b6000819050919050565b6100a581610092565b81146100b057600080fd5b50565b6000815190506100c28161009c565b92915050565b6000602082840312156100de576100dd61008d565b5b60006100ec848285016100b3565b91505092915050565b6100fe81610092565b82525050565b600060208201905061011960008301846100f5565b92915050565b6101cd8061012e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c80632a1afcd91461004657806360fe47b1146100645780636d4ce63c14610080575b600080fd5b61004e61009e565b60405161005b919061011e565b60405180910390f35b61007e6004803603810190610079919061016a565b6100a4565b005b6100886100fc565b604051610095919061011e565b60405180910390f35b60005481565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d19826040516100f1919061011e565b60405180910390a250565b60008054905090565b6000819050919050565b61011881610105565b82525050565b6000602082019050610133600083018461010f565b92915050565b600080fd5b61014781610105565b811461015257600080fd5b50565b6000813590506101648161013e565b92915050565b6000602082840312156101805761017f610139565b5b600061018e84828501610155565b9150509291505056fea264697066735822122043071242007a81bc30e6ff73e1130c05b04bf48b08c4b2767bd490a8e0e601e964736f6c634300080a0033000000000000000000000000000000000000000000000000000000000000002a820a96a0b19d35179dd22665085a948b3c87b3a3e1e1a8cb1b31674345e3d5fa25c3739ea0391cfa9b1b4a20b35f62483a046527b92f6289363cb2946534ba934441005668"
}

======================================================================
📝 APENAS A TRANSAÇÃO ASSINADA (para copiar facilmente):
======================================================================
f9036b0e80832dc6c08080b9031b608060405234801561001057600080fd5b506040516102fb3803806102fb833981810160405281019061003291906100c8565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d198260405161007f9190610104565b60405180910390a25061011f565b600080fd5b6000819050919050565b6100a581610092565b81146100b057600080fd5b50565b6000815190506100c28161009c565b92915050565b6000602082840312156100de576100dd61008d565b5b60006100ec848285016100b3565b91505092915050565b6100fe81610092565b82525050565b600060208201905061011960008301846100f5565b92915050565b6101cd8061012e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c80632a1afcd91461004657806360fe47b1146100645780636d4ce63c14610080575b600080fd5b61004e61009e565b60405161005b919061011e565b60405180910390f35b61007e6004803603810190610079919061016a565b6100a4565b005b6100886100fc565b604051610095919061011e565b60405180910390f35b60005481565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d19826040516100f1919061011e565b60405180910390a250565b60008054905090565b6000819050919050565b61011881610105565b82525050565b6000602082019050610133600083018461010f565b92915050565b600080fd5b61014781610105565b811461015257600080fd5b50565b6000813590506101648161013e565b92915050565b6000602082840312156101805761017f610139565b5b600061018e84828501610155565b9150509291505056fea264697066735822122043071242007a81bc30e6ff73e1130c05b04bf48b08c4b2767bd490a8e0e601e964736f6c634300080a0033000000000000000000000000000000000000000000000000000000000000002a820a96a0b19d35179dd22665085a948b3c87b3a3e1e1a8cb1b31674345e3d5fa25c3739ea0391cfa9b1b4a20b35f62483a046527b92f6289363cb2946534ba934441005668

💾 Dados também salvos em: signed_transaction.json

======================================================================
✨ PRONTO! Use a transação assinada no Postman
======================================================================

🔒 Lembre-se: Sua chave privada NUNCA foi enviada pela rede!
   Você está enviando apenas a transação JÁ ASSINADA.
```

### 📄 Arquivo Gerado: `signed_transaction.json`

O script também salva um arquivo JSON com todos os dados:

```json
{
  "signed_transaction": "f9036b0e80832dc6c08080b9031b6080604052...",
  "transaction_hash_preview": "0xc27c93e15461af21ee9058490dec2d23645712d0c3626ce84148be4848db6301",
  "deployer_address": "0xFE3B557E8Fb62b89F4916B721be55cEb828dBd73",
  "nonce": 15,
  "gas_limit": 3000000,
  "gas_price": 0,
  "chain_id": 1337,
  "constructor_params": [42]
}
```

### 📝 O que Fazer com a Saída

1. **Copie o valor de `signed_transaction`** (a string hexadecimal longa)
2. **Você vai colar isso no Postman** na próxima etapa

---

## Etapa 3: Deploy com Transação Assinada

### 🎯 Objetivo
Enviar a transação **já assinada** para a API fazer apenas o broadcast para a rede Besu.

### 📡 Requisição no Postman

#### **Configuração**

| Campo | Valor |
|-------|-------|
| **Método** | `POST` |
| **URL** | `http://localhost:8000/api/v1/besu/deploy-signed/` |
| **Headers** | `Authorization: Bearer SEU_TOKEN_JWT`<br>`Content-Type: application/json` |
| **Body Type** | `raw` → `JSON` |

#### **Body (raw JSON)**

```json
{
  "signed_transaction": "f9036b0e80832dc6c08080b9031b608060405234801561001057600080fd5b506040516102fb3803806102fb833981810160405281019061003291906100c8565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d198260405161007f9190610104565b60405180910390a25061011f565b600080fd5b6000819050919050565b6100a581610092565b81146100b057600080fd5b50565b6000815190506100c28161009c565b92915050565b6000602082840312156100de576100dd61008d565b5b60006100ec848285016100b3565b91505092915050565b6100fe81610092565b82525050565b600060208201905061011960008301846100f5565b92915050565b6101cd8061012e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c80632a1afcd91461004657806360fe47b1146100645780636d4ce63c14610080575b600080fd5b61004e61009e565b60405161005b919061011e565b60405180910390f35b61007e6004803603810190610079919061016a565b6100a4565b005b6100886100fc565b604051610095919061011e565b60405180910390f35b60005481565b806000819055503373ffffffffffffffffffffffffffffffffffffffff167fe42ab83e51dcfb436887e998d12b1585d6eea49b2900b0b3bcd0591dec7c3d19826040516100f1919061011e565b60405180910390a250565b60008054905090565b6000819050919050565b61011881610105565b82525050565b6000602082019050610133600083018461010f565b92915050565b600080fd5b61014781610105565b811461015257600080fd5b50565b6000813590506101648161013e565b92915050565b6000602082840312156101805761017f610139565b5b600061018e84828501610155565b9150509291505056fea264697066735822122043071242007a81bc30e6ff73e1130c05b04bf48b08c4b2767bd490a8e0e601e964736f6c634300080a0033000000000000000000000000000000000000000000000000000000000000002a820a96a0b19d35179dd22665085a948b3c87b3a3e1e1a8cb1b31674345e3d5fa25c3739ea0391cfa9b1b4a20b35f62483a046527b92f6289363cb2946534ba934441005668"
}
```

#### **Exemplo Visual (Postman)**

```
POST http://localhost:8000/api/v1/besu/deploy-signed/

Headers:
  Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  Content-Type: application/json

Body (raw - JSON):
  {
    "signed_transaction": "f9036b0e80832dc6c08080b9031b6080..."
  }
```

### ⚠️ ATENÇÃO: Tipo de Body

**IMPORTANTE:** A rota `/deploy-signed/` espera **JSON**, não **form-data**!

No Postman:
1. Vá na aba **Body**
2. Selecione **raw**
3. No dropdown à direita, selecione **JSON**
4. Cole o JSON com a `signed_transaction`

### ✅ Resposta Esperada

```json
{
    "success": true,
    "contract_address": "0x4245CF4518CB2C280f5e9c6a03c90C147F80B4d9",
    "transaction_hash": "c27c93e15461af21ee9058490dec2d23645712d0c3626ce84148be4848db6301",
    "gas_used": 180910,
    "error_message": null
}
```

### 📝 O que Fazer com a Resposta

1. **Salve o `contract_address`** - é o endereço do seu contrato deployado
2. **Salve o `transaction_hash`** - para consultar a transação no blockchain
3. **Anote o `gas_used`** - custo real do deploy

---

## Etapa 4: Interagir com o Contrato

Agora que o contrato está deployado, você pode interagir com ele!

### 🐍 Script Python: `interact_simplestorage.py`

#### **Localização**
```
/contracts/python/interact_simplestorage.py
```

#### **Configuração do Script**

Edite as seguintes variáveis:

```python
# Endereço do contrato deployado
CONTRACT_ADDRESS = "0x4245CF4518CB2C280f5e9c6a03c90C147F80B4d9"

# RPC do Besu
BESU_RPC_URL = "http://localhost:8547"

# Sua chave privada (para enviar transações)
PRIVATE_KEY = "8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"

# ABI do SimpleStorage (mesmo da compilação)
ABI = [...]
```

#### **Executar o Script**

```bash
cd /home/inmetro/besu-starter-victor/contracts/python
source myenv/bin/activate
python3 interact_simplestorage.py
```

#### **Funções Disponíveis**

O script demonstra:
- ✅ **Leitura** (não gasta gas): `get()` e `storedData`
- ✅ **Escrita** (gasta gas): `set(newValue)`
- ✅ **Eventos**: Captura de eventos `DataStored`

---

## 📚 Exemplos Completos

### Exemplo 1: SimpleStorage (com construtor)

#### **Contrato Solidity**
```solidity
pragma solidity ^0.8.10;

contract SimpleStorage {
    uint256 public storedData;
    
    event DataStored(address indexed sender, uint256 value);
    
    constructor(uint256 _initialValue) {
        storedData = _initialValue;
        emit DataStored(msg.sender, _initialValue);
    }
    
    function set(uint256 _value) public {
        storedData = _value;
        emit DataStored(msg.sender, _value);
    }
    
    function get() public view returns (uint256) {
        return storedData;
    }
}
```

#### **Configuração do `sign_transaction.py`**
```python
CONSTRUCTOR_PARAMS = [42]  # Valor inicial
```

---

### Exemplo 2: Contrato SEM Construtor

#### **Contrato Solidity**
```solidity
pragma solidity ^0.8.10;

contract HelloWorld {
    string public message = "Hello, World!";
    
    function setMessage(string memory _msg) public {
        message = _msg;
    }
}
```

#### **Configuração do `sign_transaction.py`**
```python
CONSTRUCTOR_PARAMS = []  # Sem parâmetros
```

---

### Exemplo 3: Contrato com Múltiplos Parâmetros

#### **Contrato Solidity**
```solidity
pragma solidity ^0.8.10;

contract Token {
    string public name;
    string public symbol;
    uint256 public totalSupply;
    
    constructor(string memory _name, string memory _symbol, uint256 _supply) {
        name = _name;
        symbol = _symbol;
        totalSupply = _supply;
    }
}
```

#### **Configuração do `sign_transaction.py`**
```python
CONSTRUCTOR_PARAMS = ["MyToken", "MTK", 1000000]
```

---

## 🔍 Troubleshooting

### ❌ Erro: "Input should be a valid dictionary"

**Causa:** Você enviou `form-data` em vez de `JSON` no `/deploy-signed/`

**Solução:**
1. No Postman, selecione **Body** → **raw** → **JSON**
2. Cole o JSON: `{"signed_transaction": "0x..."}`

---

### ❌ Erro: "Nonce too low"

**Causa:** Você tentou assinar duas transações com o mesmo nonce

**Solução:**
1. Execute `sign_transaction.py` novamente (ele pega o nonce atualizado)
2. Ou aguarde a primeira transação confirmar antes de assinar outra

---

### ❌ Erro: "Out of Gas"

**Causa:** `GAS_LIMIT` muito baixo para o contrato

**Solução:**
```python
# No sign_transaction.py, aumente:
GAS_LIMIT = 5000000  # ou mais, conforme necessário
```

**Referências de Gas:**
- SimpleStorage: ~200K
- ERC20: ~1-2M
- ERC721: ~3-5M
- CarbonCredit (complexo): ~3-15M

---

### ❌ Erro: "Insufficient funds"

**Causa:** A conta não tem saldo suficiente

**Solução:**
1. Verifique o saldo: No script, ele mostra o saldo
2. Transfira ETH para a conta antes do deploy

---

### ❌ Erro: "Invalid signature"

**Causa:** Chave privada incorreta ou chain_id errado

**Solução:**
1. Verifique se a `PRIVATE_KEY` está correta
2. Verifique se o `BESU_RPC_URL` está apontando para a rede correta
3. O script mostra o Chain ID - confirme se está correto

---

### ❌ Erro: "Constructor parameters mismatch"

**Causa:** `CONSTRUCTOR_PARAMS` não corresponde ao construtor do contrato

**Solução:**
1. Verifique o construtor no código Solidity
2. Ajuste `CONSTRUCTOR_PARAMS` para corresponder aos tipos e quantidade
3. Exemplo: `constructor(uint, string)` → `[42, "hello"]`

---

## 🔒 Boas Práticas de Segurança

### ✅ SEMPRE

1. **Use variáveis de ambiente** para chaves privadas em produção
2. **Adicione `.env` ao `.gitignore`**
3. **Use HTTPS** em produção (não HTTP)
4. **Valide certificados SSL**
5. **Use contas de teste** para desenvolvimento

### ❌ NUNCA

1. **Commite chaves privadas** no código
2. **Compartilhe chaves privadas** via chat/email
3. **Use chaves de produção** em ambiente de teste
4. **Envie chave privada** pela rede (use apenas transações assinadas)

---

## 📊 Comparação: Deploy Inseguro vs Seguro

| Aspecto | Deploy Inseguro<br>(rota antiga) | Deploy Seguro<br>(2 etapas) |
|---------|----------------------------------|------------------------------|
| **Chave privada trafega na rede** | ❌ Sim | ✅ Não |
| **API armazena chaves** | ⚠️ Possível | ✅ Não |
| **Compatível com hardware wallet** | ❌ Não | ✅ Sim |
| **Compatível com MetaMask** | ❌ Não | ✅ Sim |
| **Auditável** | ⚠️ Difícil | ✅ Fácil |
| **Nível de segurança** | 🔴 Baixo | 🟢 Alto |
| **Recomendado para produção** | ❌ Não | ✅ Sim |

---

## 📖 Resumo do Fluxo

```
1. COMPILE
   Postman → API → recebe ABI + bytecode

2. SIGN (LOCAL)
   Python script + chave privada → gera signed_transaction
   ⚠️ Chave privada NÃO sai do computador!

3. DEPLOY
   Postman → API (envia signed_transaction) → contrato deployado

4. INTERACT
   Python script → usa contract_address para interagir
```

---

## 🎯 Checklist Rápido

- [ ] Compilei o contrato via `/compile-contract/`
- [ ] Copiei `abi` e `bytecode` para `sign_transaction.py`
- [ ] Configurei `CONSTRUCTOR_PARAMS` corretamente
- [ ] Executei `python3 sign_transaction.py`
- [ ] Copiei a `signed_transaction` gerada
- [ ] No Postman, selecionei **Body → raw → JSON**
- [ ] Enviei para `/deploy-signed/` com JSON correto
- [ ] Recebi `contract_address` na resposta
- [ ] Salvei o endereço do contrato
- [ ] Configurei script de interação com o endereço
- [ ] Testei leitura e escrita no contrato

---

## 🆘 Suporte

Se encontrar problemas:

1. **Verifique os logs** do auth-service: `docker compose logs -f auth-service`
2. **Verifique os logs** do Besu: `docker compose logs -f rpcnode-user`
3. **Consulte a documentação** em `/docs/`
4. **Revise este guia** passo a passo

---

## 📚 Arquivos de Referência

- **Compilação:** `/auth/src/besu/routers.py` (rota `/compile-contract/`)
- **Deploy Assinado:** `/auth/src/besu/routers.py` (rota `/deploy-signed/`)
- **Script de Assinatura:** `/contracts/python/sign_transaction.py`
- **Script de Interação:** `/contracts/python/interact_simplestorage.py`
- **Schemas:** `/auth/src/besu/schemas.py`
- **Serviços:** `/auth/src/besu/services.py`

---

**✨ Pronto! Agora você pode fazer deploy de contratos de forma segura!**

🔒 **Lembre-se:** Com essa arquitetura, sua chave privada **NUNCA** trafega na rede. Você envia apenas a transação **JÁ ASSINADA** localmente.
