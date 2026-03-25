# 📦 Documentação - API de Deploy de Contratos Solidity

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Endpoint de Deploy](#endpoint-de-deploy)
- [Configurações de Ambiente](#configurações-de-ambiente)
- [Compatibilidade de Versões](#compatibilidade-de-versões)
- [Adicionando Bibliotecas Solidity](#adicionando-bibliotecas-solidity)
- [Exemplos de Uso](#exemplos-de-uso)
- [Troubleshooting](#troubleshooting)
- [Referências](#referências)

---

## 🎯 Visão Geral

Esta API permite fazer o **deploy de contratos Solidity** na rede **Hyperledger Besu** de forma automatizada, incluindo:

- ✅ Compilação automática de contratos `.sol`
- ✅ Detecção automática de versão do Solidity
- ✅ Suporte a bibliotecas OpenZeppelin
- ✅ Deploy com assinatura local de transações
- ✅ Estimativa e controle de gas
- ✅ Retorno detalhado de erros

---

## 🚀 Endpoint de Deploy

### **POST /api/besu/deploy**

Compila e faz deploy de um contrato Solidity na blockchain Besu.

#### **Headers:**
```http
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data
```

#### **Body (form-data):**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `contract_file` | File (.sol) | ✅ Sim | Arquivo do contrato Solidity |
| `private_key` | String | ✅ Sim | Chave privada para assinar transação (hex) |
| `gas_limit` | Integer | ❌ Não | Limite de gas (padrão: 3000000) |
| `gas_price` | Integer | ❌ Não | Preço do gas em wei (padrão: automático) |
| `constructor_params` | JSON Array | ❌ Não | Parâmetros do construtor (se necessário) |

#### **Exemplo de Request (Postman/cURL):**

```bash
curl -X POST http://localhost/api/besu/deploy \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -F "contract_file=@CarbonCreditNFT.sol" \
  -F "private_key=8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63" \
  -F "gas_limit=5000000"
```

#### **Exemplo de Response (Sucesso):**

```json
{
    "success": true,
    "contract_address": "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741",
    "transaction_hash": "0xc39696bc0bf5d8e2e3fab076b8562205089a77b2e3985a21aaa8b8d772552d31",
    "gas_used": 3345904,
    "compilation_output": {
        "success": true,
        "abi": [...],
        "bytecode": "0x608060405260016008553480156200001657600080fd5b5...",
        "error_message": null
    },
    "error_message": null
}
```

#### **Exemplo de Response (Erro):**

```json
{
    "success": false,
    "contract_address": null,
    "transaction_hash": null,
    "gas_used": null,
    "compilation_output": {
        "success": false,
        "abi": null,
        "bytecode": null,
        "error_message": "Erro de compilação: Source '@openzeppelin/contracts/...' not found"
    },
    "error_message": "Falha na compilação: ..."
}
```

---

## ⚙️ Configurações de Ambiente

### **Arquitetura do Sistema**

```
┌─────────────────────────────────────────────────────────────┐
│                         Cliente                              │
│              (Postman, Frontend, Python)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP POST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (Porta 80)                          │
│              Proxy reverso + SSL (opcional)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI (auth-service)                      │
│  - Recebe arquivo .sol                                       │
│  - Compila com py-solc-x                                     │
│  - Assina transação localmente                               │
│  - Envia para Besu                                           │
└────────────────────────┬────────────────────────────────────┘
                         │ Web3.py
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Hyperledger Besu (QBFT)                         │
│  - rpcnode-user: 8547 (sem auth)                            │
│  - rpcnode-admin: 8545 (com JWT)                            │
│  - Chain ID: 1337                                            │
│  - Gas Limit por bloco: 100M                                 │
└─────────────────────────────────────────────────────────────┘
```

### **Variáveis de Ambiente**

Arquivo: `/home/inmetro/besu-starter-victor/auth/.env`

```env
# Besu RPC
BESU_RPC_URL=http://rpcnode-user:8547

# JWT (para autenticação da API)
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/dbname
```

---

## 🔧 Compatibilidade de Versões

### **⚠️ IMPORTANTE: Incompatibilidade Solidity 0.8.20+**

O Besu **NÃO suporta** contratos compilados com Solidity **0.8.20 ou superior** devido ao novo opcode `PUSH0` introduzido no Shanghai EVM.

#### **Versões Compatíveis:**

| Solidity | OpenZeppelin | Besu | Status |
|----------|-------------|------|--------|
| **0.8.19** | **v4.9.6** | ✅ Compatível | ✅ **RECOMENDADO** |
| 0.8.20+ | v5.x | ❌ Incompatível | ❌ Causa "Out of Gas" |
| 0.8.0-0.8.18 | v4.x | ✅ Compatível | ⚠️ Versões antigas |
| 0.7.x | v3.x | ✅ Compatível | ⚠️ Legado |

#### **Como o sistema lida com isso:**

O arquivo `/auth/src/besu/services.py` (linhas 35-42) automaticamente **faz downgrade** de versões incompatíveis:

```python
# LIMITAR VERSÃO MÁXIMA: Solidity 0.8.20+ não é compatível com Besu
version_parts = list(map(int, solc_version.split('.')))
if version_parts[0] == 0 and version_parts[1] == 8 and version_parts[2] >= 20:
    solc_version = "0.8.19"  # Downgrade para versão compatível
    print(f"⚠️ Versão {pragma_match.group(1)} não compatível com Besu. Usando 0.8.19")
```

#### **Recomendação para contratos novos:**

```solidity
// ✅ Use esta versão
pragma solidity ^0.8.19;

// ❌ Evite estas versões
pragma solidity ^0.8.20;
pragma solidity ^0.8.21;
```

---

## 📚 Adicionando Bibliotecas Solidity

### **Bibliotecas Instaladas por Padrão**

- **OpenZeppelin v4.9.6** - Contratos padrão (ERC20, ERC721, Ownable, etc.)

### **Como Adicionar Novas Bibliotecas**

#### **1️⃣ Instalar via npm no Dockerfile**

Arquivo: `/home/inmetro/besu-starter-victor/auth/Dockerfile` (linha 9)

```dockerfile
# Instalar bibliotecas Solidity para compilação de contratos
RUN npm install -g @openzeppelin/contracts@4.9.6

# ✅ Adicione mais bibliotecas aqui:
RUN npm install -g \
    @chainlink/contracts@0.8.0 \
    @uniswap/v3-core@1.0.0
```

#### **2️⃣ Configurar Remappings no services.py**

Arquivo: `/auth/src/besu/services.py` (linha 84)

```python
# Configurar remappings para bibliotecas Solidity
import_remappings = [
    '@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts',
    
    # ✅ Adicione novos remappings aqui:
    '@chainlink/contracts=/usr/local/lib/node_modules/@chainlink/contracts',
    '@uniswap/v3-core=/usr/local/lib/node_modules/@uniswap/v3-core',
]
```

#### **3️⃣ Rebuild do Container**

```bash
cd /home/inmetro/besu-starter-victor
docker compose build auth-service
docker compose up -d auth-service
```

#### **4️⃣ Usar no Contrato**

```solidity
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract MeuContrato is ERC721 {
    AggregatorV3Interface internal priceFeed;
    
    constructor() ERC721("MeuNFT", "MNFT") {
        priceFeed = AggregatorV3Interface(0x...);
    }
}
```

### **Testando Biblioteca SEM Rebuild (temporário)**

```bash
# Entrar no container
docker compose exec -u root auth-service bash

# Instalar temporariamente
npm install -g @chainlink/contracts@0.8.0

# Sair
exit

# Testar deploy via API
# Se funcionar, adicionar permanentemente no Dockerfile
```

---

## 💡 Exemplos de Uso

### **Exemplo 1: Contrato Simples (sem bibliotecas)**

**SimpleStorage.sol:**
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

**Deploy via Postman:**
```
POST http://localhost/api/besu/deploy
Form-data:
- contract_file: SimpleStorage.sol
- private_key: 8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63
- gas_limit: 500000
```

---

### **Exemplo 2: ERC721 com OpenZeppelin**

**MyNFT.sol:**
```solidity
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyNFT is ERC721, Ownable {
    uint256 private _tokenIdCounter;
    
    constructor() ERC721("MyNFT", "MNFT") {}
    
    function mint(address to) public onlyOwner {
        _tokenIdCounter++;
        _safeMint(to, _tokenIdCounter);
    }
}
```

**Deploy via Python:**
```python
import requests

url = "http://localhost/api/besu/deploy"
headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

files = {'contract_file': open('MyNFT.sol', 'rb')}
data = {
    'private_key': '8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63',
    'gas_limit': 3000000
}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

---

### **Exemplo 3: Contrato com Construtor**

**Token.sol:**
```solidity
pragma solidity ^0.8.19;

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

**Deploy com parâmetros:**
```json
POST http://localhost/api/besu/deploy

Form-data:
- contract_file: Token.sol
- private_key: 8f2a55...
- gas_limit: 1000000
- constructor_params: ["MeuToken", "MTK", 1000000]
```

---

## 🐛 Troubleshooting

### **Erro: "Out of Gas: usou X/X gas"**

**Causa:** Gas insuficiente para executar o contrato.

**Solução:**
1. Aumente `gas_limit` para o valor sugerido na mensagem de erro
2. Verifique se o contrato não tem loops infinitos
3. Para contratos ERC721: use pelo menos 5M gas

```json
{
    "contract_file": "MeuContrato.sol",
    "gas_limit": 10000000  // ✅ Aumentar este valor
}
```

---

### **Erro: "Source '@openzeppelin/contracts/...' not found"**

**Causa:** Biblioteca não instalada ou remapping não configurado.

**Solução:**
1. Verifique se a biblioteca está no `Dockerfile`:
   ```dockerfile
   RUN npm install -g @openzeppelin/contracts@4.9.6
   ```

2. Adicione remapping no `services.py`:
   ```python
   import_remappings = [
       '@openzeppelin/contracts=/usr/local/lib/node_modules/@openzeppelin/contracts'
   ]
   ```

3. Rebuild do container:
   ```bash
   docker compose build auth-service
   docker compose up -d
   ```

---

### **Erro: "Chave privada inválida"**

**Causa:** Formato incorreto da chave privada.

**Solução:**
- Use chave sem ou com prefixo `0x`: 
  ```
  ✅ 8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63
  ✅ 0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63
  ```

---

### **Erro: "Transação revertida (status=0)"**

**Causa:** Erro na lógica do contrato (ex: construtor falhou).

**Possíveis causas:**
- Parâmetros do construtor incorretos
- `require()` falhando no construtor
- Overflow aritmético
- Endereço zero passado onde não é permitido

**Solução:**
1. Revise a lógica do construtor
2. Teste o contrato em Remix IDE primeiro
3. Adicione logs/eventos para debug

---

### **Erro: "Solidity 0.8.20+ incompatível com Besu"**

**Causa:** Versão do Solidity usa opcode `PUSH0` não suportado pelo Besu.

**Solução Automática:**
O sistema automaticamente faz downgrade para 0.8.19.

**Solução Manual:**
Altere o pragma do contrato:
```solidity
// ❌ Antes
pragma solidity ^0.8.20;

// ✅ Depois
pragma solidity ^0.8.19;
```

---

## 📊 Benchmarks de Gas

| Tipo de Contrato | Gas Estimado | Recomendação |
|-----------------|--------------|--------------|
| SimpleStorage | 300K - 500K | `gas_limit: 1000000` |
| ERC20 básico | 1M - 2M | `gas_limit: 3000000` |
| ERC721 básico | 2M - 3M | `gas_limit: 5000000` |
| ERC721 + Enumerable | 5M - 10M | `gas_limit: 15000000` |
| ERC721 + Lógica complexa | 3M - 5M | `gas_limit: 10000000` |
| Contratos com loops | Variável | Testar em Remix primeiro |

**Exemplo do projeto:**
- **CarbonCreditNFT_E2_Optimized**: 3.3M gas (sem Enumerable)
- **CarbonCreditNFT_E2_Original**: 30M gas (com Enumerable)

---

## 📖 Referências

### **Documentação Oficial**
- [Hyperledger Besu Docs](https://besu.hyperledger.org/)
- [Solidity Docs](https://docs.soliditylang.org/)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts/)
- [Web3.py Docs](https://web3py.readthedocs.io/)

### **Ferramentas de Desenvolvimento**
- [Remix IDE](https://remix.ethereum.org/) - IDE online para Solidity
- [Hardhat](https://hardhat.org/) - Framework de desenvolvimento Ethereum
- [Truffle](https://trufflesuite.com/) - Suite de desenvolvimento

### **Recursos do Projeto**
- Script de interação: `/contracts/interact-python/interact_e2.py`
- Contratos exemplo: `/contracts/solidity/*.sol`
- Configuração Besu: `/config/besu/QBFTgenesis.json`

---

## 🎓 Resumo Executivo

### **✅ Checklist de Deploy**

1. ✅ Usar Solidity **0.8.19** (não 0.8.20+)
2. ✅ OpenZeppelin **v4.9.6** instalado
3. ✅ Remappings configurados no `services.py`
4. ✅ Gas limit adequado (veja benchmarks acima)
5. ✅ Chave privada válida (64 caracteres hex)
6. ✅ Container `auth-service` rodando e saudável
7. ✅ Besu conectado (porta 8547 acessível)

### **🚀 Workflow Completo**

```bash
# 1. Criar contrato Solidity (0.8.19)
# 2. Testar em Remix IDE (opcional)
# 3. Deploy via API:

POST http://localhost/api/besu/deploy
Form-data:
- contract_file: MeuContrato.sol
- private_key: 8f2a55...
- gas_limit: 5000000

# 4. Obter endereço do contrato
# 5. Interagir via Web3.py ou frontend
```

---

**Última atualização:** 09 de Outubro de 2025  
**Versão:** 1.0.0  
**Autor:** Sistema de Deploy Automatizado - Besu Starter