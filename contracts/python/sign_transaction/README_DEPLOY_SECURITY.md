# Arquiteturas de Deploy Seguro

Este diretório contém exemplos de diferentes abordagens para fazer deploy de contratos, desde a menos segura (legada) até a mais segura (totalmente local).

## 🔐 Níveis de Segurança

### ❌ Abordagem 1: Deploy com Chave Privada na API (NÃO RECOMENDADO)

**Rota:** `POST /api/v1/besu/deploy-contract/`

**Como funciona:**
- Cliente envia arquivo `.sol` + chave privada para a API
- API compila, assina e faz deploy
- **PROBLEMA:** Chave privada trafega na rede

**Quando usar:**
- Apenas para desenvolvimento/testes locais
- NUNCA em produção
- NUNCA com chaves de contas reais

```bash
# Exemplo de requisição
curl -X POST http://localhost:8000/api/v1/besu/deploy-contract/ \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -F "contract_file=@SimpleStorage.sol" \
  -F "private_key=8f2a5594903..." \
  -F "gas_limit=3000000"
```

---

### ✅ Abordagem 2: Deploy com Transação Assinada (RECOMENDADO)

**Rotas:**
1. `POST /api/v1/besu/compile-contract/` - Compila e retorna bytecode
2. `POST /api/v1/besu/deploy-signed/` - Faz broadcast de transação assinada

**Como funciona:**
1. Cliente envia `.sol` para compilação
2. API retorna `bytecode` + `abi`
3. Cliente monta e assina transação LOCALMENTE
4. Cliente envia transação assinada para a API
5. API faz apenas broadcast para a rede

**Vantagens:**
- ✅ Chave privada NUNCA sai do cliente
- ✅ API não precisa armazenar chaves
- ✅ Compatível com hardware wallets
- ✅ Compatível com MetaMask

**Script de exemplo:** `deploy_secure_example.py`

```python
# Uso
python deploy_secure_example.py
```

**Fluxo:**
```
Cliente                    API                      Besu
  |                         |                         |
  |--[1] .sol file--------->|                         |
  |<-----bytecode + abi-----|                         |
  |                         |                         |
  | [2] Monta transação     |                         |
  | [3] Assina localmente   |                         |
  |                         |                         |
  |--[4] signed_tx--------->|                         |
  |                         |--[5] broadcast--------->|
  |                         |<-------receipt----------|
  |<-----contract_addr------|                         |
```

---

### 🔒 Abordagem 3: Deploy Totalmente Local (MAIS SEGURO)

**Rota usada:**
- `POST /api/v1/besu/compile-contract/` - Apenas para compilação

**Como funciona:**
1. Cliente usa API apenas para compilar contrato
2. Cliente faz TUDO localmente:
   - Monta transação
   - Assina transação
   - Envia DIRETAMENTE ao Besu (sem passar pela API)

**Vantagens:**
- ✅ Chave privada NUNCA sai do cliente
- ✅ Transação vai direto para o Besu
- ✅ Não depende da API para deploy
- ✅ Máxima segurança e controle

**Script de exemplo:** `deploy_fully_local.py`

```python
# Uso
python deploy_fully_local.py
```

**Fluxo:**
```
Cliente                    API                      Besu
  |                         |                         |
  |--[1] .sol file--------->|                         |
  |<-----bytecode + abi-----|                         |
  |                         |                         |
  | [2] Monta transação     |                         |
  | [3] Assina localmente   |                         |
  | [4] Envia diretamente------------------------>|
  |<--------------receipt---------------------------|
```

---

## 📊 Comparação das Abordagens

| Característica | Abordagem 1<br>(Legada) | Abordagem 2<br>(Assinatura) | Abordagem 3<br>(Local) |
|---|:---:|:---:|:---:|
| **Chave privada na rede** | ❌ Sim | ✅ Não | ✅ Não |
| **API armazena chaves** | Possível | ✅ Não | ✅ Não |
| **Compatível com hardware wallet** | ❌ Não | ✅ Sim | ✅ Sim |
| **Compatível com MetaMask** | ❌ Não | ✅ Sim | ✅ Sim |
| **Depende da API para deploy** | Sim | Sim | ✅ Não |
| **Nível de segurança** | 🔴 Baixo | 🟢 Alto | 🟢 Muito Alto |
| **Complexidade** | Baixa | Média | Média |
| **Recomendado para produção** | ❌ Não | ✅ Sim | ✅ Sim |

---

## 🚀 Como Escolher

### Use Abordagem 1 se:
- Está fazendo testes rápidos localmente
- Não importa se a chave vazar (conta de teste)
- Quer simplicidade máxima

### Use Abordagem 2 se:
- Quer segurança em produção
- Precisa centralizar logs de deploy na API
- Quer compatibilidade com carteiras
- Precisa de auditoria/controle via API

### Use Abordagem 3 se:
- Quer máxima segurança
- Não confia 100% na API
- Quer controle total do processo
- Tem acesso direto ao RPC do Besu

---

## 📝 Configuração

### 1. Obter Token JWT

```bash
# Login na API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "seu_usuario", "password": "sua_senha"}'

# Copie o token retornado
export JWT_TOKEN="eyJhbGc..."
```

### 2. Configurar Scripts

Edite as variáveis no início de cada script:

```python
API_BASE_URL = "http://localhost:8000/api/v1/besu"
BESU_RPC_URL = "http://localhost:8547"
JWT_TOKEN = "seu_token_jwt_aqui"
PRIVATE_KEY = "sua_chave_privada"
CONTRACT_FILE = "../solidity/SeuContrato.sol"
```

### 3. Instalar Dependências

```bash
pip install web3 eth-account requests
```

---

## 🔍 Detalhes Técnicos

### Compilação via API

**Request:**
```bash
POST /api/v1/besu/compile-contract/
Content-Type: multipart/form-data
Authorization: Bearer <token>

contract_file: <arquivo.sol>
```

**Response:**
```json
{
  "success": true,
  "abi": [...],
  "bytecode": "0x6080604052..."
}
```

### Deploy com Transação Assinada

**Request:**
```bash
POST /api/v1/besu/deploy-signed/
Content-Type: application/json
Authorization: Bearer <token>

{
  "signed_transaction": "0xf86c808504a817c800825208..."
}
```

**Response:**
```json
{
  "success": true,
  "contract_address": "0x1234...",
  "transaction_hash": "0xabcd...",
  "gas_used": 256789
}
```

---

## ⚠️ Avisos de Segurança

1. **NUNCA** commite chaves privadas no código
2. **NUNCA** use a Abordagem 1 em produção
3. **SEMPRE** use HTTPS em produção (não HTTP)
4. **SEMPRE** valide o certificado SSL
5. **SEMPRE** use contas de teste para desenvolvimento

---

## 🆘 Troubleshooting

### Erro: "Token de autorização inválido"
- Verifique se o JWT está correto
- Token pode ter expirado, faça login novamente

### Erro: "Out of Gas"
- Aumente o `gas_limit` na transação
- Contratos ERC721 podem precisar de 5-15M gas

### Erro: "Nonce too low/high"
- Espere transações anteriores confirmarem
- Sincronize o nonce com `w3.eth.get_transaction_count()`

### Erro: "Insufficient funds"
- Conta não tem saldo suficiente
- Verifique: `w3.eth.get_balance(address)`

---

## 📚 Referências

- [Documentação Web3.py](https://web3py.readthedocs.io/)
- [Ethereum Accounts](https://eth-account.readthedocs.io/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Hyperledger Besu](https://besu.hyperledger.org/)
