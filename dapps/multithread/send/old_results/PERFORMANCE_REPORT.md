# Relatório de Teste de Desempenho - Blockchain Besu

**Data do Teste:** Fevereiro 2026  
**Aplicação:** Sistema de Transações Multi-Thread para Blockchain  
**Contrato:** CarbonCreditNFT (E2)

---

## 📊 Resumo Executivo

Este relatório apresenta os resultados de testes de desempenho realizados na blockchain Besu, variando o número de workers (threads) de 2 a 64, com cada worker processando 1000 transações.

### Configuração dos Testes

| Parâmetro | Valor |
|-----------|-------|
| **RPC Endpoint** | `ec2-18-218-85-118.us-east-2.compute.amazonaws.com/user/` |
| **Transações por Worker** | 1000 |
| **Timeout por Transação** | 120s |
| **Contrato** | CarbonCreditNFT_E2 |
| **Cenários Testados** | 2, 4, 8, 16, 32, 64 workers |

---

## 📈 Resultados por Cenário

### 1. Teste com 2 Workers
- **Total de Transações:** 2,000
- **Taxa de Sucesso:** 100.0% (2,000/2,000)
- **Duração Total:** ~29,995s (~8.33 horas)
- **Latência Média:** 29,994.85 ms (~30s)
- **Latência Mínima:** 24,970.69 ms
- **Latência Máxima:** 30,839.66 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~0.067 tx/s

### 2. Teste com 4 Workers
- **Total de Transações:** 4,000
- **Taxa de Sucesso:** 100.0% (4,000/4,000)
- **Duração Total:** ~29,987s (~8.33 horas)
- **Latência Média:** 29,986.71 ms (~30s)
- **Latência Mínima:** 16,950.22 ms
- **Latência Máxima:** 30,980.65 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~0.133 tx/s

### 3. Teste com 8 Workers
- **Total de Transações:** 8,000
- **Taxa de Sucesso:** 99.99% (7,999/8,000)
- **Falhas:** 1 transação
- **Duração Total:** ~30,155s (~8.38 horas)
- **Latência Média:** 30,154.91 ms (~30s)
- **Latência Mínima:** 18,900.52 ms
- **Latência Máxima:** 35,529.93 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~0.265 tx/s

### 4. Teste com 16 Workers
- **Total de Transações:** 16,000
- **Taxa de Sucesso:** 100.0% (16,000/16,000)
- **Duração Total:** ~29,981s (~8.33 horas)
- **Latência Média:** 29,980.87 ms (~30s)
- **Latência Mínima:** 10,772.66 ms
- **Latência Máxima:** 31,694.47 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~0.534 tx/s

### 5. Teste com 32 Workers
- **Total de Transações:** 32,000
- **Taxa de Sucesso:** 100.0% (32,000/32,000)
- **Duração Total:** ~29,985s (~8.33 horas)
- **Latência Média:** 29,984.87 ms (~30s)
- **Latência Mínima:** 14,774.10 ms
- **Latência Máxima:** 30,945.51 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~1.067 tx/s

### 6. Teste com 64 Workers
- **Total de Transações:** 64,000
- **Taxa de Sucesso:** 100.0% (64,000/64,000)
- **Duração Total:** ~29,991s (~8.33 horas)
- **Latência Média:** 29,991.06 ms (~30s)
- **Latência Mínima:** 16,542.52 ms
- **Latência Máxima:** 43,806.88 ms
- **Throughput por Worker:** 0.03 tx/s
- **Throughput Total da Rede:** ~2.134 tx/s

---

## 🔍 Análise Comparativa

### Tabela Consolidada

| Workers | Total TXs | Sucesso | Falhas | Duração (s) | Latência Média (ms) | Lat. Mín (ms) | Lat. Máx (ms) | Throughput Total (tx/s) |
|---------|-----------|---------|--------|-------------|---------------------|---------------|---------------|------------------------|
| 2       | 2,000     | 2,000   | 0      | 29,995      | 29,994.85          | 24,970.69     | 30,839.66     | 0.067                  |
| 4       | 4,000     | 4,000   | 0      | 29,987      | 29,986.71          | 16,950.22     | 30,980.65     | 0.133                  |
| 8       | 8,000     | 7,999   | 1      | 30,155      | 30,154.91          | 18,900.52     | 35,529.93     | 0.265                  |
| 16      | 16,000    | 16,000  | 0      | 29,981      | 29,980.87          | 10,772.66     | 31,694.47     | 0.534                  |
| 32      | 32,000    | 32,000  | 0      | 29,985      | 29,984.87          | 14,774.10     | 30,945.51     | 1.067                  |
| 64      | 64,000    | 64,000  | 0      | 29,991      | 29,991.06          | 16,542.52     | 43,806.88     | 2.134                  |

### Gráfico de Throughput Total vs Workers

```
Throughput (tx/s)
    |
2.5 |                                                    ● (64 workers)
    |
2.0 |
    |
1.5 |
    |
1.0 |                              ● (32 workers)
    |
0.5 |              ● (16 workers)
    |    ● (8w)
    | ●(4w)
0.0 |●(2w)
    +----+----+----+----+----+----+----+----+----+----+----+----+
    0    8   16   24   32   40   48   56   64
                        Número de Workers
```

---

## 💡 Insights e Conclusões

### 1. **Escalabilidade Linear**
- O throughput total da rede escala **linearmente** com o número de workers
- Aumentar de 2 para 64 workers (32x) resulta em ~31.9x mais throughput
- Cada worker mantém consistentemente ~0.03 tx/s independente do número total de workers

### 2. **Consistência Temporal**
- A duração total permanece **praticamente constante** (~30,000s ou ~8.33 horas)
- Isso indica que o sistema mantém o mesmo tempo de processamento independente da carga
- A latência média por transação se mantém estável em ~30 segundos

### 3. **Confiabilidade**
- Taxa de sucesso geral: **99.998%** (63,999 de 64,000 transações)
- Apenas **1 falha** registrada em todo o teste (no cenário de 8 workers)
- Sistema demonstra alta confiabilidade mesmo sob carga crescente

### 4. **Padrões de Latência**
- **Latência Mínima:** Diminui com mais workers (24.9s → 10.7s no teste de 16 workers)
  - Indica melhor aproveitamento de "janelas" de processamento da blockchain
- **Latência Máxima:** Aumenta ligeiramente com mais workers (30.8s → 43.8s)
  - Esperado devido à maior contenção de recursos
- **Latência Média:** Permanece estável em ~30 segundos

### 5. **Gargalo Identificado**
- O throughput por worker de **0.03 tx/s** (1 transação a cada ~33 segundos) sugere:
  - **Limitação no tempo de confirmação de blocos** da blockchain Besu
  - Possível configuração de block time em torno de 30 segundos
  - O sistema está limitado pela velocidade da blockchain, não pela aplicação

### 6. **Capacidade de Processamento**
- Com 64 workers simultâneos, o sistema alcançou:
  - **2.134 tx/s** de throughput sustentado
  - **64,000 transações** em ~8.33 horas
  - **~7,680 tx/hora** ou **~184,320 tx/dia** (em operação contínua)

---

## 🎯 Recomendações

### Para Melhorar o Desempenho:

1. **Otimizar Configuração da Blockchain:**
   - Reduzir o block time da rede Besu (atualmente parece estar em ~30s)
   - Avaliar configuração de gas limit por bloco
   - Considerar ajustes no consensus mechanism (QBFT/IBFT2)

2. **Escalar Horizontalmente:**
   - O sistema demonstrou escalabilidade linear
   - Adicionar mais workers pode aumentar proporcionalmente o throughput
   - Considerar até 128 ou 256 workers em testes futuros

3. **Otimização de Código:**
   - Implementar batch transactions quando possível
   - Avaliar uso de EIP-1559 para melhor estimativa de gas price
   - Considerar técnicas de transaction pooling

4. **Monitoramento:**
   - Implementar métricas em tempo real de throughput
   - Adicionar alertas para falhas de transação
   - Monitorar uso de recursos (CPU, memória, rede)

5. **Testes Adicionais:**
   - Testar com diferentes tamanhos de payload
   - Avaliar desempenho em horários de pico
   - Realizar testes de stress com carga variável

---

## 📝 Notas Técnicas

### Ambiente de Teste
- **Blockchain:** Hyperledger Besu (QBFT Consensus)
- **Região AWS:** us-east-2 (Ohio)
- **Linguagem:** Go 1.x
- **Biblioteca:** go-ethereum (geth)
- **Protocolo:** HTTPS com TLS

### Limitações Conhecidas
- Testes realizados em ambiente de desenvolvimento/homologação
- Uma única instância de RPC node (possível ponto de contenção)
- Não foram testados cenários de falha/recuperação
- Métricas de uso de recursos do servidor não foram coletadas

---

## 📊 Arquivos de Dados

Os dados completos dos testes estão disponíveis em:
- `worker_statistics_2workers.csv`
- `worker_statistics_4workers.csv`
- `worker_statistics_8workers.csv`
- `worker_statistics_16workers.csv`
- `worker_statistics32_workers.csv`
- `worker_statistics_64workers.csv`

---

**Relatório gerado automaticamente a partir dos dados de teste de desempenho da blockchain Besu.**
