# Implementação: OBDLink para Blockchain

## Visão Geral do Sistema

Este sistema processa dados brutos de telemetria veicular (arquivo OBDLink.csv) e os transforma em créditos de carbono E1 registrados na blockchain. O processo envolve três etapas principais: processamento dos dados, aplicação de privacidade diferencial, e registro na blockchain através de um contrato inteligente.

---

## 1. O Contrato: E1RegistryTelemetry.sol

### Propósito

O contrato recebe dados agregados de viagens veiculares e calcula automaticamente quanto crédito de carbono (E1) o motorista deve receber. A diferença fundamental para o contrato original é que este trabalha com **telemetria direta** (taxa de combustível em litros/hora) ao invés de dados pré-calculados de autonomia.

### Como Funciona a Monetização

O contrato implementa um cálculo em quatro etapas:

**Etapa 1: Consumo de Combustível**  
O contrato recebe a taxa média de consumo de combustível durante a viagem (em litros por hora) e a duração total da viagem (em segundos). Com esses dois valores, calcula quantos litros foram efetivamente consumidos. Por exemplo, se o veículo consumiu a uma taxa de 4.24 litros/hora durante 300 segundos (5 minutos), isso resulta em 0.353 litros consumidos.

**Etapa 2: Emissão Base de CO2**  
Sabendo quantos litros de combustível foram usados, o contrato multiplica esse valor por uma constante fixa de 1880 gramas de CO2 por litro de etanol. Isso dá a emissão bruta. O contrato então ajusta pela porcentagem de etanol no combustível—quanto mais etanol, melhor, pois é menos poluente que gasolina pura.

**Etapa 3: Fator de Elevação**  
Aqui está uma das inovações: o contrato considera a altitude do percurso. Dirigir em lugares mais altos (montanhas, serras) é mais difícil para o motor devido ao ar rarefeito, resultando em maior consumo relativo e mais emissões. O fator de correção varia de 0% (nível do mar até 100m) até 40% de aumento (acima de 1000m de altitude). Esse ajuste torna o cálculo mais justo—quem dirige em regiões altas recebe mais E1 porque o esforço do motor é maior.

**Etapa 4: Valor Monetário**  
Finalmente, o contrato multiplica a emissão final pelo preço do carbono (em reais por tonelada, mas convertido para wei). Isso transforma gramas de CO2 em um valor em criptomoeda que o motorista pode receber como incentivo.

### Dados de Entrada

O contrato espera receber 12 informações por viagem:

- **Identificação**: VIN do veículo, timestamp da viagem, pseudônimo do motorista (para privacidade)
- **Localização**: Coordenadas de início e fim da viagem (latitude/longitude com ruído aplicado para privacidade)
- **Altitude**: Elevação no início e fim do trajeto em metros
- **Métricas da Viagem**: Velocidade média, porcentagem de etanol, taxa de combustível média, duração total
- **Preço**: Valor do carbono para calcular monetização

Importante notar que as coordenadas chegam com ruído já aplicado—o contrato nunca vê as localizações exatas.

### Tabela de Altitude

O contrato usa uma tabela fixa de cinco faixas:

| Faixa de Altitude | Fator Aplicado | Significado |
|------------------|----------------|-------------|
| 0 a 100 metros | 100% (sem mudança) | Próximo ao nível do mar, condições normais |
| 100 a 300 metros | 105% | Pequena correção, elevações baixas |
| 300 a 600 metros | 115% | Elevação moderada, começam efeitos notáveis |
| 600 a 1000 metros | 125% | Alta altitude, efeito significativo |
| Acima de 1000 metros | 140% | Muito alta, ar bastante rarefeito |

Essa tabela foi calibrada para refletir estudos sobre eficiência de motores em diferentes altitudes.

---

## 2. Processamento Off-Chain: process_obdlink_telemetry.py

### Problema: Dados Brutos Ponto-a-Ponto

O arquivo OBDLink.csv não contém viagens organizadas. Ele é um log contínuo com uma leitura a cada fração de segundo: tempo, coordenadas GPS, velocidade instantânea, taxa de combustível naquele momento, percentual de etanol, etc. Pode haver 15.856 registros representando múltiplas viagens ao longo de dias.

### Solução: Processamento Inteligente

O script Python resolve esse problema em cinco passos:

#### Passo 1: Identificar Viagens

O script varre todo o arquivo procurando "gaps" de tempo. Se há mais de 5 minutos (300 segundos) entre duas leituras consecutivas, o sistema entende que o carro foi desligado e uma nova viagem começou. Além disso, viagens muito curtas (menos de 60 segundos) são descartadas, pois não são significativas.

Resultado: o arquivo de 15 mil registros é dividido em, digamos, 50 viagens distintas.

#### Passo 2: Calcular Distância Real

Este é um ponto crítico. Cada viagem pode ter centenas de pontos GPS (um a cada segundo ou fração). Não podemos simplesmente calcular a distância em linha reta entre o primeiro e último ponto—isso ignoraria o trajeto real.

A solução: o script percorre TODOS os pontos da viagem e calcula a distância entre cada par consecutivo usando a fórmula de Haversine. Essa fórmula é específica para GPS porque considera que a Terra é esférica, não plana. Para cada segmento (ponto 1→2, ponto 2→3, ..., ponto N-1→N), calcula a distância levando em conta latitude, longitude e curvatura terrestre. Todas essas mini-distâncias são somadas.

Por que isso importa? Porque o trajeto real pode ter curvas, desvios, paradas em semáforos. A soma de todos os segmentos dá a distância verdadeiramente percorrida. Um trajeto de 156 pontos GPS pode ter 2.456 km reais, enquanto a linha reta seria apenas 1.8 km.

#### Passo 3: Aplicar Privacidade Diferencial

Aqui está outra decisão crucial: onde aplicar ruído para proteger privacidade?

A estratégia é aplicar ruído APENAS nas coordenadas do primeiro e do último ponto da viagem. Essas são as informações sensíveis—revelam onde você mora (início) e onde foi (fim). O ruído adicionado é tipicamente de cerca de 200 metros, suficiente para proteger identidade sem destruir utilidade.

Importante: a distância calculada no Passo 2 NÃO recebe ruído. Ela permanece precisa porque é um número abstrato—saber que alguém percorreu 2.5 km não revela onde a pessoa está. Da mesma forma, velocidade média, taxa de combustível e outras métricas não recebem ruído.

#### Passo 4: Obter Elevação

Usando as coordenadas ORIGINAIS (antes de aplicar ruído), o script consulta dados de elevação do projeto SRTM da NASA. Isso retorna a altitude em metros daquele ponto. Como temos coordenadas de início e fim, obtemos duas elevações e calculamos a média.

Por que usar coordenadas originais? Porque precisão é importante aqui. Um erro de 200m na posição horizontal pode mudar a elevação em 50 metros se houver morros próximos, afetando significativamente o cálculo de E1.

#### Passo 5: Agregar Tudo

Para cada viagem identificada, o script calcula:

- **Métricas Temporais**: Duração total em segundos
- **Métricas de Movimento**: Velocidade média calculando média simples de todas as velocidades instantâneas
- **Métricas de Combustível**: Taxa média de l/hr durante a viagem
- **Métricas Ambientais**: Porcentagem média de etanol (geralmente estável em ~94%)
- **Coordenadas Privadas**: Início e fim com ruído aplicado
- **Elevações**: Altitude inicial e final em metros
- **Distância Real**: Soma de todos os segmentos Haversine sem qualquer ruído

### Saída: CSV Pronto para Blockchain

O resultado é um novo arquivo CSV com uma linha por viagem. Cada linha contém todas as 12 informações que o contrato espera, já formatadas e prontas. Por exemplo:

```
VEHICLE_001, viagem #1, início em (-23.031, -44.547) [privado], fim em (-23.031, -44.547) [privado], 
42m de altitude inicial, 45m final, 2.456 km percorridos, 29.5 km/h de média, 
94% etanol, 4.24 l/hr de consumo, 300 segundos de duração, 156 amostras usadas
```

---

## 3. Envio para Blockchain: send_telemetry_to_blockchain.py

### Propósito

Este script é a ponte entre o mundo off-chain (arquivos CSV) e on-chain (blockchain Besu). Ele lê o CSV processado e envia cada viagem como uma transação para o contrato inteligente.

### Conversão de Formatos

Um desafio é que Python trabalha com números decimais (float) enquanto Solidity não tem ponto flutuante. A solução é multiplicar por potências de 10:

- **Coordenadas**: Multiplicadas por 1.000.000 (1e6). Então -23.031020 vira -23031020. No contrato, dividimos por 1e6 quando necessário.
- **Velocidade e Fuel Rate**: Multiplicados por 1.000 (1e3). Então 29.5 km/h vira 29500.
- **Elevação**: Já é inteiro (metros), sem conversão.
- **Preço de Carbono**: Convertido para wei (1 real = 1e18 wei na nossa abstração).

### Processo de Envio

Para cada linha do CSV:

1. **Leitura**: Script lê os valores e valida se estão completos
2. **Conversão**: Aplica as multiplicações acima
3. **Construção da Transação**: Usa Web3.py para criar uma transação chamando `registerTripTelemetry()` no contrato
4. **Estimativa de Gas**: Calcula quanto gas será necessário (geralmente ~500k)
5. **Assinatura**: Usa a chave privada do oracle para assinar criptograficamente
6. **Envio**: Transmite a transação para a rede Besu
7. **Confirmação**: Aguarda a transação ser minerada e incluída em um bloco
8. **Verificação**: Checa se a transação foi bem-sucedida e extrai o evento emitido

Se houver erro em qualquer etapa (rede fora, gas insuficiente, validação falhou), o script registra e tenta a próxima viagem para não perder todo o lote.

### O Que Acontece no Contrato

Quando o contrato recebe a transação:

1. Valida que só o oracle pode enviar (segurança)
2. Executa o cálculo em 4 etapas descrito anteriormente
3. Armazena os dados da viagem na blockchain permanentemente
4. Emite um evento `TripRegistered` com todos os detalhes
5. Incrementa o contador de viagens

O evento emitido contém a emissão calculada e o valor E1, permitindo que aplicações externas monitorem e processem pagamentos.

---

## Fluxo Completo Passo-a-Passo

Imagine um motorista que usou o OBDLink durante uma semana:

**Segunda-feira, 8h00**: Motorista liga o carro. OBDLink começa a gravar: latitudes, longitudes, velocidades, fuel rate, tudo a cada segundo. Arquivo cresce com centenas de linhas.

**Segunda-feira, 8h15**: Motorista desliga o carro no trabalho. OBDLink para de gravar (ou grava zeros/valores parados).

**Durante o dia**: Arquivo fica parado. Gap de 8 horas entre registros.

**Segunda-feira, 18h00**: Motorista volta para casa. Novos dados gravados por 20 minutos.

**Final da semana**: Arquivo tem 15.856 linhas representando ~10 viagens distintas.

**Processamento**:

1. Usuário roda `process_obdlink_telemetry.py OBDLink.csv viagens.csv PLACA123 0.5`
2. Script identifica 10 viagens pelos gaps de tempo
3. Para cada viagem: soma todos os km (Haversine), protege coordenadas, busca altitude
4. Gera `viagens.csv` com 10 linhas (uma por viagem)

**Envio**:

1. Usuário roda `send_telemetry_to_blockchain.py viagens.csv --contract 0xABC... --pk 0xDEF...`
2. Script converte cada linha para formato Solidity  
3. Envia 10 transações para o contrato
4. Cada transação calcula E1 e armazena na blockchain
5. Total: 10 viagens registradas, X reais de E1 acumulados para o motorista

---

## Exemplo Numérico Completo

Vamos acompanhar **uma única viagem** do início ao fim:

### Dados Brutos no OBDLink.csv

```
Ponto 1 (t=0s): lat=-23.03084, lon=-44.54698, speed=5 km/h, fuel=2.4 l/hr, ethanol=94%
Ponto 2 (t=1s): lat=-23.03084, lon=-44.54697, speed=10 km/h, fuel=3.1 l/hr, ethanol=94%
Ponto 3 (t=2s): lat=-23.03085, lon=-44.54696, speed=15 km/h, fuel=4.2 l/hr, ethanol=94%
...
[153 pontos intermediários]
...
Ponto 156 (t=300s): lat=-23.03086, lon=-44.54695, speed=8 km/h, fuel=3.8 l/hr, ethanol=94%
```

Total: 156 pontos GPS coletados durante 5 minutos (300 segundos).

### Processamento pelo Script Python

**Identificação**: Script detecta uma viagem contínua de 300s (sem gaps >300s).

**Cálculo de Distância**:
- Haversine(ponto1, ponto2) = 0.011 km
- Haversine(ponto2, ponto3) = 0.013 km
- Haversine(ponto3, ponto4) = 0.012 km
- ... (152 cálculos mais)
- Haversine(ponto155, ponto156) = 0.009 km
- **Soma total: 2.456 km**

**Privacidade**:
- Coordenada início original: (-23.03084, -44.54698)
- Após ruído Laplaciano (ε=0.5): (-23.031020, -44.547120)
- Coordenada fim original: (-23.03086, -44.54695)
- Após ruído: (-23.030910, -44.546880)

**Elevação**:
- Consulta SRTM para (-23.03084, -44.54698): 42 metros
- Consulta SRTM para (-23.03086, -44.54695): 45 metros
- Média: 43.5 metros → arredondado para 43m

**Métricas**:
- Velocidade média: (5+10+15+...+8) / 156 = 29.5 km/h
- Fuel rate média: (2.4+3.1+4.2+...+3.8) / 156 = 4.24 l/hr
- Etanol médio: 94% (quase constante)
- Duração: 300 segundos

### Linha no CSV Processado

```csv
VEHICLE_001,1,-23.031020,-44.547120,-23.030910,-44.546880,42,45,2.456,29.5,94,4.24,300,156
```

### Envio para Blockchain

Script converte:
- Coordenadas: -23.031020 → -23031020 (×1e6)
- Velocidade: 29.5 → 29500 (×1e3)
- Fuel rate: 4.24 → 4240 (×1e3)
- Preço carbono: R$ 50/ton → 50000000000000000000 wei (50e18)

### Cálculo no Contrato

**Etapa 1 - Consumo**:
```
fuelConsumed = 4.24 l/hr × 300 s / 3600 s/hr
             = 1272 / 3600
             = 0.353 litros
```

**Etapa 2 - Emissão Base**:
```
emissaoBase = 0.353 L × 1880 gCO2/L × 94%
            = 0.353 × 1880 × 0.94
            = 624 gramas de CO2
```

**Etapa 3 - Fator de Elevação**:
```
Elevação média = 43 metros
Faixa: 0-100m → fator 100%
emissaoFinal = 624 × 100 / 100 = 624 gCO2
```
(Neste caso não houve ajuste, mas se fosse a 700m seria 624 × 125% = 780 gCO2)

**Etapa 4 - Valor E1**:
```
valorE1 = 624 gCO2 × (50 R$/ton) / 1000 g/kg / 1000 kg/ton
        = 624 × 50 / 1.000.000
        = 0.0312 reais
        = 31.200.000.000.000.000 wei (31.2 finney)
```

### Evento Emitido

O contrato grava permanentemente na blockchain:
- VIN: VEHICLE_001
- Timestamp: 1740344400
- Pseudônimo: User_VEHICLE_001
- Emissão Final: 624 gCO2
- Valor E1: 31.2 finney
- Elevação Média: 43m

Este evento pode ser capturado por sistemas de pagamento para creditar o motorista.

---

## Decisões Técnicas Importantes

### Por Que Haversine e Não Euclidiana?

A Terra não é plana. A fórmula euclidiana simples (√[(x2-x1)² + (y2-y1)²]) funcionaria se estivéssemos em um mapa 2D, mas no GPS real isso causa erros de 5% a 15%, especialmente em distâncias maiores ou em latitudes mais altas. Haversine considera a esfericidade da Terra, resultando em precisão de <0.5%.

### Por Que DP Apenas nas Extremidades?

Aplicar ruído em todos os 156 pontos seria:
- **Computacionalmente caro**: 156 operações criptográficas vs 4 (início/fim, lat/lon)
- **Acúmulo de erro**: Ruído em cada ponto se propagaria, destruindo a distância calculada
- **Desnecessário**: Proteger início e fim já garante que não sabemos o endereço exato

A distância total (2.456 km) não revela localização—poderia ser qualquer trajeto dessa extensão.

### Por Que Elevação Importa?

Estudos automotivos mostram que altitude afeta significativamente a eficiência do motor:
- Ar rarefeito reduz oxigênio disponível para combustão
- Motor precisa trabalhar mais para manter potência
- Consumo aumenta 5-10% a cada 500m de elevação

Ignorar isso seria injusto: dois motoristas fazendo 10 km, um no litoral e outro em Campos do Jordão, teriam emissões muito diferentes. A correção de altitude torna o sistema equitativo.

### Por Que Processar Off-Chain?

Fazer loops em Solidity (156 iterações para calcular distância) custaria milhões em gas. Processar em Python é gratuito e rápido, e a distância resultante pode ser verificada—qualquer um pode baixar o CSV original e re-processar para comprovar a honestidade.

---

## Limitações e Considerações

**Confiança no Oracle**: O sistema assume que quem envia dados processou corretamente o CSV. Para mitigar, o CSV original pode ser armazenado em IPFS e o hash incluído na transação, permitindo auditoria posterior.

**Privacidade vs Verificação**: DP nas coordenadas impede verificação exata do trajeto. Este é um trade-off consciente—priorizamos privacidade do motorista sobre auditabilidade total da rota.

**Elevação de Terceiros**: Dependemos de dados SRTM. Embora sejam públicos e confiáveis (~30m de precisão vertical), há uma dependência externa. Alternativa seria sensores barométricos no próprio veículo.

**Preço de Carbono**: Atualmente informado por transação. Um sistema mais robusto teria um oráculo de preço on-chain atualizado periodicamente.

---

## Resumo Executivo

Este sistema transforma **dados brutos de telemetria veicular** em **créditos de carbono monetizados** através de:

1. **Processamento Inteligente**: Identifica viagens, calcula distâncias reais (Haversine), preserva métricas precisas
2. **Privacidade Estratégica**: Aplica ruído apenas onde necessário (coordenadas extremas), mantém utilidade dos dados
3. **Cálculo Justo**: Considera altitude e realidade física do motor para emissões equitativas
4. **Eficiência Blockchain**: Uma transação por viagem (não por ponto GPS), custos controlados
5. **Auditabilidade**: Dados processados off-chain podem ser verificados independentemente

O resultado é um balanço prático entre **privacidade pessoal**, **precisão técnica** e **viabilidade econômica** para monetização de emissões veiculares.
