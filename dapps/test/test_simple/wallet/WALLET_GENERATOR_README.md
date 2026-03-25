# 🔑 Gerador de Carteiras para Testes Multi-Worker

Scripts para criar e financiar carteiras Ethereum para testes de alta concorrência.

## 📋 Pré-requisitos

```bash
pip install web3 eth-account
```

## 🚀 Como Usar

### 1. Gerar Novas Carteiras

#### Gerar 1024 carteiras em novo arquivo:
```bash
cd ~/besu-starter-victor/dapps/test/test_simple
python3 generate_wallets.py 1024 wallets_1024_groups.json
```

#### Adicionar mais 960 carteiras ao arquivo existente (64→1024):
```bash
python3 generate_wallets.py 960 wallets_1024_groups.json
```

#### Gerar diferentes quantidades:
```bash
# Para 128 workers
python3 generate_wallets.py 128 wallets_128_groups.json

# Para 256 workers
python3 generate_wallets.py 256 wallets_256_groups.json

# Para 512 workers
python3 generate_wallets.py 512 wallets_512_groups.json
```

### 2. Transferir Fundos para as Carteiras

**⚠️ IMPORTANTE:** As novas carteiras precisam de ETH para pagar gas (mesmo com zeroBaseFee, precisam de saldo).

#### Financiar todas as carteiras de um arquivo:
```bash
python3 fund_wallets.py wallets_1024_groups.json
```

#### Financiar apenas um range específico (ex: carteiras 65-128):
```bash
python3 fund_wallets.py wallets_1024_groups.json 65 128
```

#### Financiar em lotes (recomendado para > 500 carteiras):
```bash
# Lote 1: carteiras 1-250
python3 fund_wallets.py wallets_1024_groups.json 1 250

# Lote 2: carteiras 251-500
python3 fund_wallets.py wallets_1024_groups.json 251 500

# Lote 3: carteiras 501-750
python3 fund_wallets.py wallets_1024_groups.json 501 750

# Lote 4: carteiras 751-1024
python3 fund_wallets.py wallets_1024_groups.json 751 1024
```

### 3. Atualizar o Código Go

Edite o arquivo `send_simple.go`:

```go
const (
    RPCURL         = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"
    DeploymentJSON = "../simple_counter_deployment.json"
    WalletsJSON    = "./wallets_1024_groups.json"  // ← MUDAR AQUI
    DataCSV        = "./dados_gas.csv"
    NumWorkers     = 128  // ← MUDAR QUANTIDADE DE WORKERS
    MaxRowsToRead  = 100
    TxTimeout      = 120 * time.Second
)
```

### 4. Executar Teste

```bash
go run send_simple.go
```

## 📊 Plano de Testes Recomendado

```bash
# Teste 1: 128 workers (precisa 128 carteiras)
python3 generate_wallets.py 128 wallets_128_groups.json
python3 fund_wallets.py wallets_128_groups.json
# Alterar NumWorkers=128, WalletsJSON="./wallets_128_groups.json"
go run send_simple.go

# Teste 2: 256 workers (precisa 256 carteiras)
python3 generate_wallets.py 256 wallets_256_groups.json
python3 fund_wallets.py wallets_256_groups.json 1 128
python3 fund_wallets.py wallets_256_groups.json 129 256
# Alterar NumWorkers=256, WalletsJSON="./wallets_256_groups.json"
go run send_simple.go

# Teste 3: 512 workers (precisa 512 carteiras)
python3 generate_wallets.py 512 wallets_512_groups.json
python3 fund_wallets.py wallets_512_groups.json 1 256
python3 fund_wallets.py wallets_512_groups.json 257 512
# Alterar NumWorkers=512, WalletsJSON="./wallets_512_groups.json"
go run send_simple.go

# Teste 4: 1024 workers (precisa 1024 carteiras)
python3 generate_wallets.py 1024 wallets_1024_groups.json
python3 fund_wallets.py wallets_1024_groups.json 1 256
python3 fund_wallets.py wallets_1024_groups.json 257 512
python3 fund_wallets.py wallets_1024_groups.json 513 768
python3 fund_wallets.py wallets_1024_groups.json 769 1024
# Alterar NumWorkers=1024, WalletsJSON="./wallets_1024_groups.json"
go run send_simple.go
```

## 🔐 Segurança

- **NÃO versione** os arquivos de wallets no Git (contêm chaves privadas!)
- Adicione ao `.gitignore`:
  ```
  wallets_*_groups.json
  ```

## 💡 Dicas

1. **Saldo Master Insuficiente?**
   - Cada carteira recebe 100 ETH
   - Para 1024 carteiras = 102.400 ETH necessários
   - Verifique saldo do master no QBFTgenesis.json

2. **Testes Graduais:**
   - Comece com 128 workers
   - Se estável, dobre para 256
   - Continue dobrando até encontrar o limite

3. **Monitoramento:**
   - Observe latência e taxa de erro
   - Se erros > 1%, pode ser limite do blockchain

## 📂 Estrutura de Arquivos

```
test_simple/
├── generate_wallets.py          # Script para gerar carteiras
├── fund_wallets.py               # Script para financiar carteiras
├── wallets_64_groups.json        # 64 carteiras (original)
├── wallets_128_groups.json       # 128 carteiras (novo)
├── wallets_256_groups.json       # 256 carteiras (novo)
├── wallets_512_groups.json       # 512 carteiras (novo)
├── wallets_1024_groups.json      # 1024 carteiras (novo)
└── send_simple.go                # Programa de teste
```
