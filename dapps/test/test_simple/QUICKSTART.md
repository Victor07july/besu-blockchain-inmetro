# Quick Start - Teste Simple Counter

## 🎯 Objetivo Rápido

Testar se a latência de 30s é da blockchain ou do algoritmo de monetização.

## ⚡ Execução Rápida (Recomendado)

```bash
cd /home/inmetro/besu-starter-victor/dapps
chmod +x run_test.sh
./run_test.sh
```

Este script faz TUDO automaticamente:
1. ✅ Copia wallets e CSV
2. ✅ Faz deploy do SimpleCounter
3. ✅ Compila o código Go
4. ✅ Executa o teste

## 📊 Teste Rápido vs Completo

### Configuração Atual (Teste Rápido)
**Arquivo:** `test_simple/send_simple.go`
```go
NumWorkers = 2       // 2 workers
MaxRowsToRead = 100  // 100 transações
```
**Tempo estimado:** ~50 minutos

### Para Teste Completo
Edite `test_simple/send_simple.go`:
```go
NumWorkers = 64      // 64 workers
MaxRowsToRead = 1000 // 1000 transações
```
**Tempo estimado:** ~8.3 horas

## 📈 Resultados Esperados

Após o teste, você verá algo como:

```
📊 RESUMO FINAL
======================================================================
Workers:             2
Total transações:    200
Bem-sucedidas:       200
Falhas:              0
Taxa de sucesso:     100.00%

Duração total:       XXXX segundos
Latência média:      XX.XX segundos  ← COMPARE COM 30s
Latência mínima:     XX.XX segundos
Latência máxima:     XX.XX segundos

Throughput total:    X.XXX tx/s      ← COMPARE COM 0.067 tx/s (2 workers)
======================================================================
```

## 🔍 Interpretação

### Se latência ≈ 30s
✅ **Blockchain é o gargalo**
- Block time da Besu causa a latência
- Algoritmo não é o problema
- Solução: Otimizar configuração da blockchain

### Se latência < 10s
⚠️ **Algoritmo estava causando overhead**
- Cálculos complexos aumentam tempo
- Considerar otimizar contrato original
- Possível usar cálculos off-chain

## 🐛 Problemas Comuns

### Erro: Arquivo não encontrado
```bash
python3 prepare_test.py
```

### Erro: Contrato não deployado
```bash
python3 deploy_simple_counter.py
```

### Erro: Go modules
```bash
cd test_simple
go mod tidy
```

## 📞 Relatório para o Chefe

"Executei teste com contrato simplificado (apenas contador, sem cálculos).

**Resultado:**
- Latência: XX.XX segundos (Original: 30s)
- Throughput: X.XX tx/s (Original: Y.YY tx/s com mesmo número de workers)

**Conclusão:** [Baseado na interpretação acima]"

---

**Documentação completa:** Ver [README.md](README.md)
