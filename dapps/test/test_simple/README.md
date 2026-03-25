# Teste de Performance - Simple Counter

Este diretório contém um contrato simplificado para isolar e testar o tempo de confirmação da blockchain, separando-o do tempo de processamento do algoritmo de monetização.

## 🎯 Objetivo

Determinar se a latência de ~30 segundos observada nos testes é causada por:
- **A blockchain** (block time, consensus, etc.) ← Esperado
- **O algoritmo** (cálculos complexos do contrato)

## 📁 Estrutura

```
dapps/
├── contracts/
│   └── SimpleCounter.sol          # Contrato minimalista
├── test_simple/
│   ├── send_simple.go             # Código de teste (similar ao multithread)
│   └── go.mod                     # Dependências Go
├── deploy_simple_counter.py       # Script de deploy do contrato
├── prepare_test.py                # Copia wallets e CSV necessários
├── simple_counter_deployment.json # Gerado após deploy
└── README.md                      # Este arquivo
```

## 🔄 O que muda?

### Contrato Original (CarbonCreditNFT_E1)
```solidity
function calculateAndRecordE1(...) {
    // 1. Calcula Meta_CO2 (divisões, multiplicações)
    // 2. Calcula percentuais de gasolina/etanol
    // 3. Calcula emissões rodovia e cidade
    // 4. Compara com emissões reais
    // 5. Calcula valor monetário
    // 6. Cria NFT
    // 7. Emite eventos
}
```

### Novo Contrato (SimpleCounter)
```solidity
function calculateAndRecordE1(...) {
    counter++;                      // Apenas incrementa contador
    records[counter] = data;        // Armazena dados
    emit Event(...);                // Emite evento
    return (counter, 1000, 500, 100); // Retorna valores fixos
}
```

## 🚀 Como Executar

### 1. Preparar Ambiente

```bash
cd /home/inmetro/besu-starter-victor/dapps

# Instalar dependências Python (se necessário)
pip3 install web3 py-solc-x requests
```

### 2. Copiar Arquivos Necessários

```bash
python3 prepare_test.py
```

Isso copia:
- `wallets_64_groups.json` (carteiras para os workers)
- `dados_gas.csv` (dados de teste)

### 3. Fazer Deploy do Contrato

```bash
python3 deploy_simple_counter.py
```

**Saída esperada:**
```
📦 Compilando contrato...
✅ Contrato compilado com sucesso!
🚀 Fazendo deploy do contrato...
✅ Contrato deployado em: 0x...
💾 Dados salvos em: simple_counter_deployment.json
```

### 4. Compilar e Executar o Teste Go

```bash
cd test_simple
go mod tidy
go build -o test_simple
./test_simple
```

### 5. Comparar Resultados

Compare os resultados com os testes anteriores:

**Teste Original (CarbonCreditNFT_E1):**
- Latência: ~30 segundos
- Throughput (64 workers): 2.134 tx/s

**Teste Novo (SimpleCounter):**
- Latência: ? segundos ← **Isso é o que queremos descobrir**
- Throughput (64 workers): ? tx/s

## 📊 Interpretação dos Resultados

### Cenário 1: Latências Similares (~30s)
```
✅ A latência é da blockchain (block time)
✅ O algoritmo de monetização não é o gargalo
✅ Para melhorar performance: otimizar blockchain (reduzir block time)
```

### Cenário 2: Latência Muito Menor (<5s)
```
⚠️  O algoritmo está causando overhead significativo
⚠️  Considerar otimizações no contrato de monetização
⚠️  Pode ser necessário simplificar cálculos
```

### Cenário 3: Latência um Pouco Menor (~20-25s)
```
🔄 Parte da latência é da blockchain, parte do algoritmo
🔄 Ambos podem ser otimizados
🔄 Priorizar otimização com maior impacto
```

## 🔧 Configurações

### Python (deploy_simple_counter.py)
```python
RPC_URL = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"
PRIVATE_KEY = "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
```

### Go (test_simple/send_simple.go)
```go
RPCURL = "https://ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/"
DeploymentJSON = "../simple_counter_deployment.json"
WalletsJSON = "../wallets_64_groups.json"
NumWorkers = 64  // Ajuste conforme necessário
MaxRowsToRead = 1000
```

## 📝 Variações de Teste

### Teste Rápido (2 workers, 100 transações)
```go
NumWorkers = 2
MaxRowsToRead = 100
```
Tempo estimado: ~50 minutos

### Teste Médio (16 workers, 500 transações)
```go
NumWorkers = 16
MaxRowsToRead = 500
```
Tempo estimado: ~4 horas

### Teste Completo (64 workers, 1000 transações)
```go
NumWorkers = 64
MaxRowsToRead = 1000
```
Tempo estimado: ~8.3 horas

## 📈 Análise dos Dados

Os resultados serão salvos em:
- `test_simple/results/blockchain_results_Xworkers.csv` - Detalhes de cada transação
- `test_simple/results/worker_statistics_Xworkers.csv` - Estatísticas agregadas

Use os mesmos scripts de análise dos testes anteriores.

## ⚠️ Notas Importantes

1. **Mesmo CSV:** Use o mesmo arquivo `dados_gas.csv` dos testes anteriores
2. **Mesmas Wallets:** Use as mesmas carteiras para comparação justa
3. **Mesmo Número de Workers:** Recomenda-se testar com pelo menos um cenário igual (ex: 64 workers)
4. **Mesmo Horário:** Execute em horário similar ao teste original para evitar variações de carga da rede

## 🐛 Troubleshooting

### Erro: "Contrato não encontrado"
```bash
# Verifique se o deploy foi feito
ls -la simple_counter_deployment.json

# Re-faça o deploy se necessário
python3 deploy_simple_counter.py
```

### Erro: "Wallets não encontrados"
```bash
# Execute o prepare_test.py novamente
python3 prepare_test.py

# Ou copie manualmente
cp multithread/send/wallets_64_groups.json .
cp multithread/send/dados_gas.csv .
```

### Go: "package not found"
```bash
cd test_simple
go mod init test_simple
go mod tidy
```

## 📞 Relatório para o Chefe

Após executar o teste, use este template:

**"Executei o teste com o contrato simplificado que apenas incrementa um contador, sem executar o algoritmo de monetização.**

**Resultados:**
- **Latência Média:** X segundos (Original: 30s)
- **Throughput (64 workers):** X tx/s (Original: 2.134 tx/s)
- **Diferença:** X% mais rápido / similar / mais lento

**Conclusão:**
[Baseado nos cenários acima]"**

---

**Criado por:** GitHub Copilot  
**Data:** Fevereiro 2026  
**Versão:** 1.0
