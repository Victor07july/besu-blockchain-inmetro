# Análise dos Resultados: Impacto do Differential Privacy no Cálculo de E1

## Resumo Executivo

Este relatório apresenta os resultados de um experimento comparativo que avaliou o impacto da aplicação de Differential Privacy (DP) nas distâncias de viagens sobre o cálculo do token E1 em um sistema de monetização de emissões de carbono.

## Metodologia

Foram enviadas 33 viagens reais à blockchain Hyperledger Besu em dois cenários distintos:

1. **COM DP (epsilon = 1.0)**: Distâncias de rodovia e cidade com ruído Laplace aplicado
2. **SEM DP (epsilon = 0)**: Distâncias originais sem qualquer perturbação

A sensibilidade do ruído foi calibrada como 10% da média das distâncias para cada categoria (rodovia e cidade), garantindo que a privacidade fosse preservada sem comprometer excessivamente a utilidade dos dados.

## Resultados Principais

### Valor E1 (Token de Monetização)

| Métrica | COM DP | SEM DP | Diferença |
|---------|--------|--------|-----------|
| **Valor Total** | R$ 2,88 | R$ 2,73 | +R$ 0,15 (+5,41%) |
| **Valor Médio** | R$ 0,0873 | R$ 0,0828 | +R$ 0,0045 (+5,41%) |
| **Valor Mínimo** | -R$ 0,279 | -R$ 0,357 | +R$ 0,078 |
| **Valor Máximo** | R$ 2,752 | R$ 2,757 | -R$ 0,005 |

**Interpretação**: A aplicação de DP resultou em um **aumento de 5,41%** no valor total de E1. Isso ocorre porque o ruído introduzido nas distâncias levou, em média, a distâncias ligeiramente maiores, o que por sua vez resultou em emissões calculadas maiores e, consequentemente, em valores de E1 mais altos.

### Distâncias

| Métrica | COM DP | SEM DP | Diferença |
|---------|--------|--------|-----------|
| **Distância Total** | 411,52 km | 409,21 km | +2,31 km (+0,56%) |
| **Distância Média** | 12,47 km | 12,40 km | +0,07 km (+0,56%) |
| **Erro Introduzido** | 0,649 km | 0 km | 0,649 km |

**Interpretação**: O erro médio introduzido pelo DP foi de apenas **649 metros por viagem** (aproximadamente 5,2% da distância média), o que representa um trade-off aceitável entre privacidade e precisão. A distância total aumentou apenas 0,56%, demonstrando que o DP preserva bem a utilidade dos dados agregados.

### Emissões de CO₂

| Métrica | COM DP | SEM DP | Diferença |
|---------|--------|--------|-----------|
| **Diferença CO₂ Média** | 176,05 g | 166,55 g | +9,51 g (+5,71%) |

**Interpretação**: A diferença média entre emissões calculadas (metaCO₂) e emissões reais aumentou 9,51 gramas de CO₂ por viagem devido ao DP. Isso reflete o impacto do ruído nas distâncias sobre o cálculo das emissões.

### Consumo de Gas (Blockchain)

| Métrica | COM DP | SEM DP | Diferença |
|---------|--------|--------|-----------|
| **Gas Total** | 9.144.963 | 9.011.406 | +133.557 (+1,48%) |
| **Gas Médio** | 277.120 | 273.073 | +4.047 (+1,48%) |

**Interpretação**: O custo computacional (gas) aumentou apenas 1,48% com o uso de DP. Isso ocorre porque as transações com distâncias ligeiramente diferentes podem exigir cálculos marginalmente mais complexos, mas o overhead é mínimo.

## Análise do Trade-off Privacidade vs. Utilidade

### Privacidade Alcançada
- **Epsilon = 1.0**: Garantia formal de privacidade diferencial
- **Ruído médio**: 649 metros por viagem (~5,2% da distância média)
- **Mecanismo**: Laplace com sensibilidade calibrada

### Utilidade Preservada
- **Precisão agregada**: 99,44% (apenas 0,56% de diferença nas distâncias totais)
- **Impacto financeiro**: Apenas R$ 0,15 de diferença no total (5,41%)
- **Valores individuais**: Distribuição similar entre COM DP e SEM DP

## Conclusões

1. **Viabilidade Técnica**: O experimento demonstrou que é tecnicamente viável aplicar Differential Privacy em sistemas de monetização de emissões baseados em blockchain sem comprometer significativamente a utilidade dos dados.

2. **Trade-off Aceitável**: Com epsilon = 1.0, conseguimos:
   - Proteção robusta da privacidade das distâncias individuais
   - Manutenção de 99,44% de precisão nas distâncias agregadas
   - Impacto financeiro de apenas 5,41% nos valores de E1

3. **Escalabilidade**: O overhead de gas (+1,48%) é mínimo, indicando que a solução é escalável para grandes volumes de transações.

4. **Transparência**: A diferença nos valores de E1 é quantificável e pode ser comunicada aos participantes do sistema, mantendo a confiança no mecanismo de monetização.

## Recomendações

1. **Ajuste de Epsilon**: Considerar valores de epsilon entre 0.5 e 2.0 para explorar diferentes pontos no trade-off privacidade-utilidade.

2. **Compensação**: Implementar mecanismos de ajuste ou compensação para mitigar o impacto financeiro do DP nos valores de E1.

3. **Auditoria**: Estabelecer processos de auditoria para monitorar continuamente o impacto do DP na distribuição dos valores de E1.

4. **Evolução para Implementação 3**: Avançar para a próxima fase que incorporará dados GPS com técnicas avançadas de privacidade (e.g., Zero-Knowledge Proofs).

---

**Dados**: 33 viagens reais
**Blockchain**: Hyperledger Besu (QBFT)
**Contrato**: E1Registry (Solidity 0.8.0)
**Epsilon**: 1.0
**Sensibilidade**: 10% da média das distâncias
