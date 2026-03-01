# Fórmula de Monetização E1 com Distância Euclidiana

## Colunas do CSV Utilizadas

Os cálculos dependem das seguintes colunas do arquivo `OBDLink.csv`:

- **`Time (sec)`** - Tempo decorrido desde início da coleta (usado para calcular intervalos Δt)
- **` Latitude (deg)`** - Latitude GPS em graus decimais (usado no cálculo de distância)
- **` Longitude (deg)`** - Longitude GPS em graus decimais (usado no cálculo de distância)
- **` Fuel rate (l/hr)`** - Taxa instantânea de consumo em litros por hora (usado no cálculo de emissão)
- **` Alcohol fuel percentage (%)`** - Percentual de etanol no combustível flex (usado no cálculo de emissão)
- **` Vehicle speed (km/h)`** - Velocidade instantânea (opcional, para validação)

**Nota:** Colunas com espaço no início do nome (` Latitude`) devem ser acessadas considerando esse espaço.

## Cálculo de Distância

A distância euclidiana aproximada converte diferenças angulares (graus de latitude/longitude) em quilômetros usando uma constante de conversão. Um grau de latitude corresponde a aproximadamente 111.32 km em qualquer ponto da Terra. Para longitude, esse valor varia com a latitude devido à convergência dos meridianos nos polos, sendo corrigido pelo cosseno da latitude média entre os dois pontos. A distância total da viagem é obtida somando todos os segmentos calculados entre pontos consecutivos do GPS, resultando na trajetória real percorrida pelo veículo.

**Colunas utilizadas:** ` Latitude (deg)`, ` Longitude (deg)`

### Etapas do Cálculo (Ponto a Ponto)

1. **Passo 1 - Latitude média:** Calcular a latitude média entre os dois pontos para corrigir a distorção de longitude

2. **Passo 2 - Deslocamento horizontal (Δx):** Converter diferença de longitude em quilômetros, ajustando pela latitude

3. **Passo 3 - Deslocamento vertical (Δy):** Converter diferença de latitude em quilômetros (valor fixo de 111.32 km/grau)

4. **Passo 4 - Distância do segmento:** Aplicar Pitágoras (hipotenusa de um triângulo retângulo)

5. **Passo 5 - Distância total:** Somar todos os segmentos da viagem

**Fórmula:**

**Passo 1 - Latitude média:**
$$
\text{lat}_{\text{avg}} = \frac{\text{lat}_1 + \text{lat}_2}{2}
$$

**Passo 2 - Deslocamento horizontal:**
$$
\Delta x = (\text{lon}_2 - \text{lon}_1) \times 111.32 \times \cos(\text{lat}_{\text{avg}}) \quad \text{(km)}
$$

**Passo 3 - Deslocamento vertical:**
$$
\Delta y = (\text{lat}_2 - \text{lat}_1) \times 111.32 \quad \text{(km)}
$$

**Passo 4 - Distância do segmento (Pitágoras):**
$$
d_{\text{segmento}} = \sqrt{(\Delta x)^2 + (\Delta y)^2}
$$

**Passo 5 - Distância total:**
$$
D_{\text{total}} = \sum_{i=1}^{n-1} d_i
$$

## Cálculo de Emissão de CO2

A emissão é calculada ponto-a-ponto usando o sensor OBD que fornece o fuel rate instantâneo em litros por hora. Para cada intervalo entre medições consecutivas, multiplica-se o fuel rate pelo tempo decorrido para obter o combustível consumido naquele segmento. A emissão depende do mix de combustível: gasolina emite 2.31 kg CO2 por litro e etanol emite 1.51 kg CO2 por litro. O percentual de etanol informado pelo sensor determina a proporção de cada combustível, e a emissão total do segmento é a soma ponderada das duas contribuições. Somando todos os segmentos da viagem, obtém-se a emissão total real em kg de CO2.

**Colunas utilizadas:** `Time (sec)`, ` Fuel rate (l/hr)`, ` Alcohol fuel percentage (%)`

### Etapas do Cálculo (Ponto a Ponto)

O cálculo é feito para **cada par de pontos consecutivos** no CSV e depois somado. Por exemplo, se a viagem tem 600 medições, fazemos 599 cálculos e somamos tudo no final:

1. **Passo 1 - Intervalo de tempo:** Calcular quanto tempo passou entre a medição atual e a próxima (ex: 1.2 segundos)

2. **Passo 2 - Combustível consumido:** Converter o fuel rate (litros/hora) para litros consumidos nesse intervalo específico (ex: 8 l/hr × 1.2s / 3600s = 0.00267 litros)

3. **Passo 3 - Mix de combustível:** Determinar quanto é gasolina e quanto é etanol baseado no percentual do sensor (ex: 27% etanol = 73% gasolina)

4. **Passo 4 - CO2 do segmento:** Calcular emissão multiplicando o combustível pelos fatores de emissão de cada tipo (gasolina polui 2.31 kg/l, etanol polui 1.51 kg/l)

5. **Passo 5 - CO2 total:** Somar a emissão de todos os segmentos da viagem para obter o total

**Fórmula:**

**Passo 1 - Intervalo de tempo:**
$$
\Delta t_i = t_{i+1} - t_i \quad \text{(segundos)}
$$

**Passo 2 - Combustível consumido:**
$$
\text{combustível}_i = \text{fuel\_rate}_i \times \frac{\Delta t_i}{3600} \quad \text{(litros)}
$$

**Passo 3 - Mix de combustível:**
$$
\%_{\text{etanol}} = \frac{\text{alcohol\_percentage}_i}{100}, \quad \%_{\text{gasolina}} = 1 - \%_{\text{etanol}}
$$

**Passo 4 - CO2 do segmento:**
$$
\text{CO2}_{\text{segmento}} = \text{combustível}_i \times (\%_{\text{gasolina}} \times 2.31 + \%_{\text{etanol}} \times 1.51) \quad \text{(kg)}
$$

**Passo 5 - CO2 total da viagem:**
$$
\text{CO2}_{\text{total}} = \sum_{i=1}^{n-1} \text{CO2}_i
$$

## Monetização - Opção Simples

A monetização direta precifica a emissão absoluta de CO2 multiplicando o total emitido pelo preço de mercado do carbono. Se uma viagem emitiu 15 kg de CO2 e o preço está em 50 reais por tonelada, o valor resultante é 0.75 reais (15 dividido por 1000 toneladas vezes 50). Esta abordagem funciona como uma taxa ambiental proporcional ao impacto climático da viagem, onde maiores emissões resultam em maiores pagamentos. É simples e transparente, mas não incentiva comportamento eficiente pois não há comparação com uma meta.

**Dados necessários:**
- Emissão total calculada (do CSV)
- Preço do carbono (R$/ton) - dado de mercado

**Fórmula:**

$$
\text{Valor}_{\text{E1}} = \frac{\text{CO2}_{\text{total}}}{1000} \times P_{\text{carbono}} \quad \text{(R\$)}
$$

Onde $P_{\text{carbono}}$ é o preço do carbono em R$/tonelada.

## Monetização - Opção Comparativa (Recomendada)

A fórmula E1 original compara a emissão real com uma meta calculada baseada nas especificações do fabricante do veículo. A meta assume que o motorista dirigiria conforme os parâmetros de laboratório (consumo urbano do fabricante, por exemplo 12 km/l), aplicados à distância realmente percorrida. Calcula-se quanto combustível seria consumido nesse cenário ideal e converte-se em emissão usando os mesmos fatores de carbono. A diferença entre emissão real e meta determina o resultado financeiro: se o motorista emitiu menos que a meta, recebe créditos de carbono como recompensa; se emitiu mais, paga uma penalidade proporcional ao excesso. Um motorista que economizou 2 kg de CO2 em relação à meta recebe 0.10 reais de crédito (2 dividido por 1000 vezes 50). Este modelo incentiva direção eficiente, frenagens suaves, acelerações moderadas e manutenção adequada do veículo.

**Dados necessários:**
- Distância total calculada (do CSV)
- Consumo do fabricante (km/l) - dado externo do manual do veículo
- Percentual médio de etanol da viagem (do CSV: ` Alcohol fuel percentage (%)`)
- Preço do carbono (R$/ton) - dado de mercado

**Fórmula:**

$$
\text{Combustível}_{\text{meta}} = \frac{D_{\text{total}}}{C_{\text{fabricante}}} \quad \text{(litros)}
$$

$$
\text{CO2}_{\text{meta}} = \text{Combustível}_{\text{meta}} \times (\%_{\text{gasolina}} \times 2.31 + \%_{\text{etanol}} \times 1.51) \quad \text{(kg)}
$$

$$
\Delta \text{CO2} = \text{CO2}_{\text{meta}} - \text{CO2}_{\text{real}} \quad \text{(kg)}
$$

$$
\text{Valor}_{\text{E1}} = \frac{\Delta \text{CO2}}{1000} \times P_{\text{carbono}} \quad \text{(R\$)}
$$

Onde:
- $C_{\text{fabricante}}$ é o consumo declarado pelo fabricante (km/l)
- $\Delta \text{CO2} > 0$ (economizou) → crédito positivo
- $\Delta \text{CO2} < 0$ (desperdiçou) → penalidade negativa

## Processamento e Armazenamento

Todo o processamento matemático pesado ocorre em Python antes de enviar dados à blockchain: cálculo de centenas de distâncias euclidianas entre pontos GPS, soma de fuel rates ao longo do tempo, conversões de unidades e aplicação de privacidade diferencial nas coordenadas. O contrato Solidity recebe apenas dados agregados já calculados: distância total, combustível consumido, emissão real, emissão meta e valor E1 final. Isso otimiza custos de gas mantendo a blockchain como camada de armazenamento imutável e auditável, enquanto os cálculos complexos ficam fora da rede. As coordenadas GPS de início e fim são armazenadas após aplicação de privacidade diferencial, protegendo a localização exata do usuário mas preservando informação suficiente para validação externa e detecção de fraudes.
