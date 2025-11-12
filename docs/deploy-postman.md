# 📮 Guia de Deploy de Contratos via Postman

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Configuração Inicial](#configuração-inicial)
- [Endpoint 1: Compilar Contrato](#endpoint-1-compilar-contrato)
- [Endpoint 2: Deploy do Contrato](#endpoint-2-deploy-do-contrato)
- [Testando CarbonCreditNFT_E2](#testando-carboncreditnft_e2)
- [Testando Contratos Simples](#testando-contratos-simples)
- [Troubleshooting](#troubleshooting)
- [Importar Collection Pronta](#importar-collection-pronta)

---

## 🎯 Visão Geral

Este guia ensina como **fazer deploy de contratos Solidity** no Besu usando **Postman** para testar a API FastAPI.

### **Endpoints Disponíveis:**
- `POST https://localhost/api/v1/besu/compile-contract/` - Apenas compila o contrato
- `POST https://localhost/api/v1/besu/deploy-contract/` - Compila + faz deploy na blockchain

**⚠️ IMPORTANTE:** 
- Use **HTTPS** (não HTTP!) - O Nginx redireciona HTTP → HTTPS
- Não esqueça do prefixo `/api` na URL

---

## ✅ Pré-requisitos

### **1️⃣ Serviços em Execução**

```bash
# Verificar se a API está rodando
curl http://localhost/api/health

# Verificar se o Besu está acessível
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

**Resposta esperada:**
```json
{"jsonrpc":"2.0","id":1,"result":"0x539"}  // Número do bloco em hex
```

### **2️⃣ Informações Necessárias**

Tenha em mãos:
- ✅ **Token de autenticação** da API (Bearer token)
- ✅ **Private key** da conta para deploy
- ✅ **Arquivo .sol** do contrato
- ✅ **Parâmetros do construtor** (se houver)

### **3️⃣ Conta com Saldo**

```bash
# Verificar saldo da conta
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"eth_getBalance",
    "params":["0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6", "latest"],
    "id":1
  }'
```

---

## ⚙️ Configuração Inicial

### **1️⃣ Abrir Postman**

1. Abra o **Postman Desktop** ou acesse [Postman Web](https://web.postman.co/)
2. Crie uma nova **Collection** chamada "Besu Contract Deploy"

### **2️⃣ Configurar Variáveis de Ambiente**

No Postman, crie um **Environment** com estas variáveis:

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `base_url` | `https://localhost/api` | URL base da API (**HTTPS!**) |
| `auth_token` | `seu_token_aqui` | Token Bearer de autenticação |
| `private_key` | `60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3` | Chave privada (sem 0x) |
| `account_address` | `0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6` | Endereço da conta |

**⚠️ IMPORTANTE:** Use **HTTPS**, não HTTP! O Nginx redireciona HTTP para HTTPS.

**Como criar Environment:**
1. Canto superior direito → ⚙️ (Settings) → Environments
2. Click em "+" para novo environment
3. Preencha as variáveis acima
4. Salve e selecione o environment

**Desabilitar verificação SSL:**
1. **Postman Settings** (⚙️) → **General**
2. Desative **"SSL certificate verification"**
3. Ou por request: **Settings** → **Enable SSL certificate verification** = OFF

---

## 📝 Endpoint 1: Compilar Contrato

Use este endpoint para **apenas compilar** e verificar se o código está correto, **sem fazer deploy**.

### **Configuração da Request**

**Método:** `POST`  
**URL:** `{{base_url}}/v1/besu/compile-contract/`  
**URL Completa:** `http://localhost/api/v1/besu/compile-contract/`

#### **Headers:**
```
Authorization: Bearer {{auth_token}}
```

#### **Body (form-data):**
| Key | Type | Value |
|-----|------|-------|
| `contract_file` | File | Selecione o arquivo `.sol` |

### **Exemplo Passo a Passo**

1. **Criar nova Request:**
   - Nome: "Compile Contract Only"
   - Método: POST
   - URL: `{{base_url}}/v1/besu/compile-contract/`

2. **Adicionar Headers:**
   - Click na aba **Headers**
   - Adicione: `Authorization` = `Bearer {{auth_token}}`

3. **Configurar Body:**
   - Click na aba **Body**
   - Selecione **form-data**
   - Adicione campo:
     - Key: `contract_file`
     - Type: **File** (altere o dropdown de "Text" para "File")
     - Value: Click em "Select Files" e escolha seu `.sol`

4. **Enviar Request:**
   - Click em **Send**

### **Resposta Esperada (Sucesso):**

```json
{
  "success": true,
  "contract_name": "CarbonCreditNFT_E2Calculator",
  "compilation_output": {
    "abi": [
      {
        "inputs": [],
        "name": "owner",
        "outputs": [
          {
            "internalType": "address",
            "name": "",
            "type": "address"
          }
        ],
        "stateMutability": "view",
        "type": "function"
      }
      // ... mais funções
    ],
    "bytecode": "0x608060405234801561001057600080fd5b50...",
    "solc_version": "0.8.20"
  }
}
```

### **Possíveis Erros:**

#### **Erro: "Unauthorized" (401)**
```json
{
  "detail": "Token de autorização inválido"
}
```
**Solução:** Verifique se o token está correto nas variáveis de ambiente.

#### **Erro: "Compilation failed"**
```json
{
  "success": false,
  "error": "Solidity compilation failed: ...",
  "details": "ParserError: Expected pragma, import directive or contract/interface/library definition."
}
```
**Solução:** Corrija os erros de sintaxe no arquivo `.sol`.

---

## 🚀 Endpoint 2: Deploy do Contrato

Use este endpoint para **compilar E fazer deploy** do contrato na blockchain.

### **Configuração da Request**

**Método:** `POST`  
**URL:** `{{base_url}}/v1/besu/deploy-contract/`  
**URL Completa:** `http://localhost/api/v1/besu/deploy-contract/`

#### **Headers:**
```
Authorization: Bearer {{auth_token}}
```

#### **Body (form-data):**
| Key | Type | Value | Obrigatório |
|-----|------|-------|-------------|
| `contract_file` | File | Arquivo `.sol` | ✅ Sim |
| `private_key` | Text | `{{private_key}}` | ✅ Sim |
| `constructor_params` | Text | `[]` ou JSON com params | ⚠️ Depende do contrato |
| `gas_limit` | Text | `3000000` | ❌ Opcional (padrão: 3M) |
| `gas_price` | Text | vazio = auto | ❌ Opcional |

### **Exemplo Passo a Passo**

1. **Criar nova Request:**
   - Nome: "Deploy Contract"
   - Método: POST
   - URL: `{{base_url}}/v1/besu/deploy-contract/`

2. **Adicionar Headers:**
   - `Authorization` = `Bearer {{auth_token}}`

3. **Configurar Body (form-data):**

| Key | Type | Value |
|-----|------|-------|
| `contract_file` | File | Selecione `CarbonCreditNFT_E2.sol` |
| `private_key` | Text | `{{private_key}}` |
| `constructor_params` | Text | `[]` |
| `gas_limit` | Text | `6000000` |
| `gas_price` | Text | (deixe vazio) |

4. **Enviar Request:**
   - Click em **Send**
   - ⏳ Aguarde ~10-30 segundos (deploy leva tempo)

### **Resposta Esperada (Sucesso):**

```json
{
  "success": true,
  "message": "Contrato deployado com sucesso",
  "contract_address": "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741",
  "transaction_hash": "0xabc123...",
  "block_number": 1234,
  "gas_used": 2847291,
  "deployer_address": "0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6",
  "compilation_output": {
    "contract_name": "CarbonCreditNFT_E2Calculator",
    "abi": [...],
    "bytecode": "0x608060...",
    "solc_version": "0.8.20"
  }
}
```

**🎉 Sucesso! Agora você tem:**
- ✅ `contract_address` - Endereço do contrato deployado
- ✅ `abi` - Interface para interagir com o contrato
- ✅ `transaction_hash` - Hash da transação de deploy

### **Salvar Informações Importantes**

Copie e salve em um arquivo `deployment.json`:

```json
{
  "contract_name": "CarbonCreditNFT_E2Calculator",
  "contract_address": "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741",
  "transaction_hash": "0xabc123...",
  "deployed_at": "2025-10-10T15:30:00Z",
  "deployer": "0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6",
  "network": "besu-local",
  "abi": [...]
}
```

---

## 🌳 Testando CarbonCreditNFT_E2

### **Deploy do CarbonCreditNFT_E2Calculator**

Este contrato **NÃO tem parâmetros no construtor**.

#### **Request Postman:**

**URL:** `{{base_url}}/v1/besu/deploy-contract/`

**Body (form-data):**
```
contract_file: [CarbonCreditNFT_E2.sol]
private_key: {{private_key}}
constructor_params: []
gas_limit: 6000000
```

#### **Exemplo com cURL (para referência):**

```bash
curl -X POST "http://localhost/api/v1/besu/deploy-contract/" \
  -H "Authorization: Bearer seu_token" \
  -F "contract_file=@/path/to/CarbonCreditNFT_E2.sol" \
  -F "private_key=60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3" \
  -F "constructor_params=[]" \
  -F "gas_limit=6000000"
```

### **Resposta Esperada:**

```json
{
  "success": true,
  "contract_address": "0x664D6EbAbbD5cf656eD07A509AFfBC81f9615741",
  "gas_used": 2847291,
  "compilation_output": {
    "contract_name": "CarbonCreditNFT_E2Calculator",
    "abi": [
      {
        "inputs": [
          {
            "components": [
              {"name": "highwayDistance", "type": "uint256"},
              {"name": "cityDistance", "type": "uint256"}
              // ... 12 parâmetros no total
            ],
            "name": "params",
            "type": "tuple"
          },
          {
            "name": "recipient",
            "type": "address"
          }
        ],
        "name": "calculateE2AndTokenize",
        "outputs": [
          {"name": "tokenId", "type": "uint256"},
          {"name": "e2Value", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
      }
      // ... mais funções
    ]
  }
}
```

---

## 📦 Testando Contratos Simples

### **Exemplo 1: SimpleStorage (Com Construtor)**

**Contrato:**
```solidity
// SimpleStorage.sol
pragma solidity ^0.8.19;

contract SimpleStorage {
    uint256 private value;
    
    constructor(uint256 _initialValue) {
        value = _initialValue;
    }
    
    function get() public view returns (uint256) {
        return value;
    }
    
    function set(uint256 _value) public {
        value = _value;
    }
}
```

**Request Postman:**

**Body (form-data):**
```
contract_file: [SimpleStorage.sol]
private_key: {{private_key}}
constructor_params: [42]
gas_limit: 500000
```

**Explicação do `constructor_params`:**
- O construtor espera 1 parâmetro: `uint256 _initialValue`
- Passamos `[42]` para inicializar com o valor 42

### **Exemplo 2: Greeter (Construtor com String)**

**Contrato:**
```solidity
// Greeter.sol
pragma solidity ^0.8.19;

contract Greeter {
    string public greeting;
    
    constructor(string memory _greeting) {
        greeting = _greeting;
    }
    
    function setGreeting(string memory _greeting) public {
        greeting = _greeting;
    }
}
```

**Request Postman:**

**Body (form-data):**
```
contract_file: [Greeter.sol]
private_key: {{private_key}}
constructor_params: ["Hello, Besu!"]
gas_limit: 500000
```

**⚠️ Atenção:** Strings devem estar entre aspas duplas dentro do JSON!

### **Exemplo 3: ERC721 (Múltiplos Parâmetros)**

**Contrato:**
```solidity
// MyNFT.sol
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MyNFT is ERC721 {
    constructor(string memory name, string memory symbol) 
        ERC721(name, symbol) 
    {}
}
```

**Request Postman:**

**Body (form-data):**
```
contract_file: [MyNFT.sol]
private_key: {{private_key}}
constructor_params: ["My Cool NFT", "MNFT"]
gas_limit: 3000000
```

---

## 🐛 Troubleshooting

### **Erro: "405 Method Not Allowed"**

**Causa:** Método HTTP errado ou usando HTTP ao invés de HTTPS.

**Soluções:**

1. **Verificar método HTTP:**
   - ✅ Deve ser **POST**, não GET
   - No Postman: Dropdown no topo deve estar em "POST"

2. **Usar HTTPS ao invés de HTTP:**
   ```bash
   # ❌ ERRADO
   http://localhost/api/v1/besu/deploy-contract/
   
   # ✅ CORRETO
   https://localhost/api/v1/besu/deploy-contract/
   ```

3. **Desabilitar verificação SSL no Postman:**
   - Settings (⚙️) → General → Desative "SSL certificate verification"

4. **Verificar barra final na URL:**
   ```bash
   # Tente ambas:
   https://localhost/api/v1/besu/deploy-contract/   ✅ (com /)
   https://localhost/api/v1/besu/deploy-contract    ⚠️ (sem /)
   ```

---

### **Erro: "Connection refused" / "Failed to fetch"**

**Causa:** API ou Besu não estão rodando.

**Solução:**
```bash
# Verificar containers
docker ps | grep -E "auth|besu"

# Iniciar serviços
cd /home/victor/besu-starter-victor
./run.sh

# Verificar logs
docker logs auth-api
docker logs rpcnode-admin
```

---

### **Erro: "Token de autorização inválido" (401)**

**Causa:** Token JWT expirado ou inválido.

**Solução:**

1. **Fazer login novamente** na API:
```bash
curl -X POST "http://localhost/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "seu_usuario",
    "password": "sua_senha"
  }'
```

2. **Copiar o novo token:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. **Atualizar variável no Postman:**
   - Environment → `auth_token` → Cole o novo token

---

### **Erro: "Insufficient funds for gas * price + value"**

**Causa:** Conta não tem saldo suficiente.

**Solução:**

1. **Verificar saldo:**
```bash
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"eth_getBalance",
    "params":["0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6", "latest"],
    "id":1
  }'
```

2. **Se saldo for 0, usar conta pré-financiada:**
   - Conta: `0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6`
   - Private Key: `60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3`
   - Saldo inicial: 1 bilhão ETH

---

### **Erro: "Compilation failed: Solidity version not found"**

**Causa:** Versão do Solidity no contrato não está instalada no servidor.

**Solução:**

1. **Verificar versão no arquivo `.sol`:**
```solidity
pragma solidity ^0.8.19;  // ← Esta versão
```

2. **Usar versão compatível:**
   - ✅ Suportadas: `0.8.19`, `0.8.20`, `0.8.21`, `0.8.22`, `0.8.23`
   - ❌ Evite versões antigas: `<0.8.0`

3. **Se precisar de versão específica, edite o contrato:**
```solidity
// De:
pragma solidity ^0.8.25;

// Para:
pragma solidity ^0.8.20;
```

---

### **Erro: "Parâmetros do construtor inválidos"**

**Causa:** JSON mal formatado ou tipos incorretos.

**Solução:**

#### **✅ Correto:**
```json
[]                           // Sem parâmetros
[42]                        // 1 uint256
["Hello"]                   // 1 string
[42, "Test", true]          // Múltiplos parâmetros
["0xC9C913c8..."]           // 1 address
```

#### **❌ Incorreto:**
```json
42                          // Faltam os colchetes []
[Hello]                     // String sem aspas
['Hello']                   // Aspas simples não são JSON válido
[[42]]                      // Array duplo desnecessário
```

---

### **Erro: "Gas required exceeds allowance"**

**Causa:** `gas_limit` muito baixo para o contrato.

**Solução:**

1. **Aumentar gas_limit:**
```
Contratos pequenos: 500000 - 1000000
Contratos médios: 1000000 - 3000000
Contratos grandes (com ERC721Enumerable): 6000000 - 8000000
```

2. **Testar compilação primeiro:**
   - Use o endpoint `/compile-contract/` para verificar se compila
   - Isso não gasta gas, só valida o código

---

### **Erro: Deploy demora muito (timeout)**

**Causa:** Contrato muito grande ou rede lenta.

**Solução:**

1. **Aumentar timeout no Postman:**
   - Settings → Request timeout → Aumentar para 120000ms (2 minutos)

2. **Otimizar contrato:**
   - Remover `ERC721Enumerable` se não for necessário
   - Remover funções não utilizadas
   - Usar versão otimizada (ex: `CarbonCreditNFT_E2_Optimized.sol`)

3. **Verificar se deployou:**
```bash
# Verificar últimas transações
curl -X POST http://127.0.0.1:8545 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"eth_getTransactionCount",
    "params":["0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6", "latest"],
    "id":1
  }'
```

---

## 📦 Importar Collection Pronta

Para facilitar, você pode importar a collection Postman pré-configurada:

### **Passo 1: Baixar Collection**

Arquivo: `/home/victor/besu-starter-victor/auth/Besu_Contract_Deploy_Updated.postman_collection.json`

### **Passo 2: Importar no Postman**

1. Abra o Postman
2. Click em **Import** (canto superior esquerdo)
3. Arraste o arquivo `.json` ou click em "Upload Files"
4. Selecione o arquivo `Besu_Contract_Deploy_Updated.postman_collection.json`
5. Click em **Import**

### **Passo 3: Configurar Environment**

A collection já vem com exemplos, mas você precisa criar o Environment:

1. Click em ⚙️ (Settings) → **Environments**
2. Click em **+** para criar novo environment
3. Nome: "Besu Local"
4. Adicione as variáveis:

```
base_url = http://localhost/api
auth_token = seu_token_aqui
private_key = 60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3
account_address = 0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6
```

5. Selecione o environment no dropdown (canto superior direito)

### **Passo 4: Testar**

1. Abra a collection "Besu Contract Deploy Updated"
2. Selecione a request "Deploy CarbonCreditNFT_E2"
3. Atualize o campo `contract_file` com o caminho do seu arquivo
4. Click em **Send**

---

## 📊 Checklist de Teste

Antes de fazer deploy em produção, siga este checklist:

- [ ] **1. Compilação:**
  - [ ] Contrato compila sem erros
  - [ ] Versão do Solidity compatível (0.8.19+)
  - [ ] ABI gerada corretamente

- [ ] **2. Configuração:**
  - [ ] Token de autenticação válido
  - [ ] Private key correta
  - [ ] Conta com saldo suficiente
  - [ ] Parâmetros do construtor corretos

- [ ] **3. Deploy:**
  - [ ] Gas limit adequado (testado)
  - [ ] Deploy bem-sucedido
  - [ ] Contract address recebido
  - [ ] Transaction hash confirmado

- [ ] **4. Validação:**
  - [ ] Contrato aparece no blockchain
  - [ ] Funções view funcionam
  - [ ] Owner está correto
  - [ ] Eventos são emitidos

- [ ] **5. Documentação:**
  - [ ] Contract address salvo
  - [ ] ABI salva em arquivo
  - [ ] Transaction hash documentado
  - [ ] Data e hora do deploy registrados

---

## 🎓 Resumo Executivo

### **Workflow Completo**

```bash
1. Preparar arquivo .sol
   ├─ Verificar pragma solidity
   ├─ Identificar parâmetros do construtor
   └─ Testar compilação local (opcional)

2. Abrir Postman
   ├─ Criar/Selecionar Environment
   ├─ Configurar variáveis (token, private_key)
   └─ Importar collection (opcional)

3. Compilar contrato (opcional)
   ├─ POST /compile-contract/
   ├─ Upload .sol
   └─ Verificar ABI gerada

4. Deploy do contrato
   ├─ POST /deploy-contract/
   ├─ Upload .sol
   ├─ Informar private_key
   ├─ Passar constructor_params (se houver)
   └─ Aguardar resposta (~10-30s)

5. Salvar informações
   ├─ Contract address
   ├─ ABI
   ├─ Transaction hash
   └─ Criar arquivo deployment.json

6. Testar contrato
   ├─ Verificar owner
   ├─ Testar funções view
   └─ Executar primeira transação
```

---

## 📖 Referências

### **Documentação Relacionada**
- [Interação com Contratos via Python](/docs/interacao-python.md) - Como usar o contrato após deploy
- [FastAPI Docs](http://localhost/docs) - Documentação interativa da API
- [Postman Docs](https://learning.postman.com/) - Tutoriais oficiais do Postman

### **Arquivos do Projeto**
- API Routes: `/auth/src/besu/v1/routes.py`
- Schemas: `/auth/src/besu/schemas.py`
- Services: `/auth/src/besu/services.py`
- Collection: `/auth/Besu_Contract_Deploy_Updated.postman_collection.json`

### **Exemplos de Contratos**
- CarbonCreditNFT_E2: `/contracts/monetizaE2/contracts/CarbonCreditNFT_E2.sol`
- SimpleStorage: `/contracts/solidity/SimpleStorage.sol`
- Versão Otimizada: `/contracts/solidity/CarbonCreditNFT_E2_Optimized.sol`

---

## 💡 Dicas Finais

### **✅ Boas Práticas**

1. **Sempre teste compilação primeiro:**
   - Use `/compile-contract/` antes de deploy
   - Economiza tempo e evita erros

2. **Documente seus deploys:**
   - Salve contract_address, ABI e tx_hash
   - Crie arquivo JSON por deployment
   - Versione seus contratos

3. **Use variáveis de ambiente:**
   - Facilita troca entre networks
   - Protege informações sensíveis
   - Reutilize configurações

4. **Teste localmente primeiro:**
   - Deploy em Besu local antes de produção
   - Verifique todas as funções
   - Calcule custos de gas

### **⚠️ Cuidados**

1. **NUNCA compartilhe sua private key:**
   - Use variáveis de ambiente
   - Não versione no Git
   - Revogue se exposta

2. **Valide parâmetros do construtor:**
   - Erros no construtor só aparecem após deploy
   - Teste com valores reais
   - Verifique tipos (uint vs string)

3. **Monitore gas usado:**
   - Contratos grandes custam mais
   - Otimize quando possível
   - Remova código não utilizado

---

**Última atualização:** 10 de Outubro de 2025  
**Versão:** 1.0.0  
**Autor:** Sistema de Deploy Automatizado - Besu Starter

---

## 🎉 Pronto para Deploy!

Agora você tem tudo que precisa para fazer deploy de contratos via Postman! 🚀

**Próximos passos:**
1. 📮 Faça deploy do seu primeiro contrato
2. 📄 Salve as informações de deployment
3. 🐍 Use o [Guia Python](/docs/interacao-python.md) para interagir com o contrato
4. 🎯 Implemente sua lógica de negócio

**Dúvidas?** Consulte a seção de [Troubleshooting](#troubleshooting) ou os logs da API! 📚
