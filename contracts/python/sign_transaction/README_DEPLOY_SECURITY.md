# Arquiteturas de Deploy Seguro


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
