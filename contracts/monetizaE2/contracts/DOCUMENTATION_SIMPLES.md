# Documentação Simples - CarbonCreditNFT E2

## 📌 O que é este contrato?

Um contrato que calcula o valor **E2** (custo de combustível em reais) baseado em dados de viagem e cria um NFT com esse valor.

---

## 🔧 Funções do Contrato

### 1. calculateE2AndTokenize

**O que faz:**  
Calcula o valor E2 de uma viagem e cria um NFT para o usuário.

**Recebe:**
- `params`: Dados da viagem (distâncias, eficiências, preços, comportamento)
- `recipient`: Endereço de quem vai receber o NFT

**Retorna:**
- `tokenId`: Número do NFT criado
- `e2Value`: Valor E2 calculado em reais (multiplicado por 1000000)

**Quem pode usar:**  
Apenas usuários autorizados pelo dono do contrato.

---

### 2. simulateE2Calculation

**O que faz:**  
Simula o cálculo de E2 sem criar NFT (para testar antes).

**Recebe:**
- `params`: Dados da viagem

**Retorna:**
- Uma estrutura com todos os cálculos intermediários e o E2 final

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 3. getCalculationDetails

**O que faz:**  
Mostra os detalhes de cálculo de um NFT específico.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Todos os dados do cálculo daquele NFT (custos, bônus, E2)

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 4. getBatchCalculations

**O que faz:**  
Pega os detalhes de vários NFTs de uma vez.

**Recebe:**
- Array com vários números de NFTs

**Retorna:**
- Array com os dados de cada NFT

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 5. setAuthorized

**O que faz:**  
Autoriza ou remove autorização de um usuário para criar NFTs.

**Recebe:**
- `user`: Endereço do usuário
- `status`: true para autorizar, false para remover

**Retorna:**  
Nada.

**Quem pode usar:**  
Apenas o dono do contrato.

---

### 6. nextTokenId

**O que faz:**  
Mostra qual será o número do próximo NFT.

**Recebe:**  
Nada.

**Retorna:**
- Número do próximo token

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 7. authorized

**O que faz:**  
Verifica se um endereço está autorizado a criar NFTs.

**Recebe:**
- `address`: Endereço para verificar

**Retorna:**
- true se autorizado, false se não

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 8. tokenCalculations

**O que faz:**  
Acessa diretamente os cálculos armazenados de um NFT.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Estrutura com os cálculos

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 9. owner

**O que faz:**  
Mostra quem é o dono do contrato.

**Recebe:**  
Nada.

**Retorna:**
- Endereço do dono

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 10. balanceOf

**O que faz:**  
Mostra quantos NFTs um endereço possui.

**Recebe:**
- `address`: Endereço para verificar

**Retorna:**
- Quantidade de NFTs

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 11. tokenOfOwnerByIndex

**O que faz:**  
Pega o número de um NFT específico de um dono.

**Recebe:**
- `owner`: Endereço do dono
- `index`: Posição do NFT (0, 1, 2...)

**Retorna:**
- Número do NFT naquela posição

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 12. transferFrom

**O que faz:**  
Transfere um NFT de um endereço para outro.

**Recebe:**
- `from`: Endereço atual do dono
- `to`: Endereço que vai receber
- `tokenId`: Número do NFT

**Retorna:**  
Nada.

**Quem pode usar:**  
O dono do NFT ou alguém que foi aprovado.

---

### 13. safeTransferFrom

**O que faz:**  
Transfere um NFT com verificação de segurança (recomendado usar esta ao invés da transferFrom).

**Recebe:**
- `from`: Endereço atual do dono
- `to`: Endereço que vai receber
- `tokenId`: Número do NFT

**Retorna:**  
Nada.

**Quem pode usar:**  
O dono do NFT ou alguém que foi aprovado.

---

### 14. approve

**O que faz:**  
Aprova outro endereço para poder transferir um NFT específico seu.

**Recebe:**
- `to`: Endereço que você quer aprovar
- `tokenId`: Número do NFT

**Retorna:**  
Nada.

**Quem pode usar:**  
Apenas o dono do NFT.

---

### 15. setApprovalForAll

**O que faz:**  
Aprova ou remove aprovação de um operador para transferir TODOS os seus NFTs.

**Recebe:**
- `operator`: Endereço do operador
- `approved`: true para aprovar, false para remover

**Retorna:**  
Nada.

**Quem pode usar:**  
Qualquer dono de NFTs.

---

### 16. getApproved

**O que faz:**  
Verifica quem está aprovado para transferir um NFT específico.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Endereço aprovado (ou endereço zero se ninguém)

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 17. isApprovedForAll

**O que faz:**  
Verifica se um operador está aprovado para transferir todos os NFTs de um dono.

**Recebe:**
- `owner`: Endereço do dono
- `operator`: Endereço do operador

**Retorna:**
- true se aprovado, false se não

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

## 📊 Dados de Entrada (CalculationParams)

Quando você chama `calculateE2AndTokenize` ou `simulateE2Calculation`, precisa enviar estes dados:

**Distâncias:**
- `highwayDistance`: Quantos km rodou em estrada (multiplicar por 1000000)
- `cityDistance`: Quantos km rodou na cidade (multiplicar por 1000000)

**Tanque:**
- `ethanolPercent`: Quanto % de etanol tinha no tanque (multiplicar por 1000000)

**Eficiência do carro (km por litro):**
- `roadGasoline`: Eficiência na estrada com gasolina (multiplicar por 1000000)
- `roadEthanol`: Eficiência na estrada com etanol (multiplicar por 1000000)
- `cityGasoline`: Eficiência na cidade com gasolina (multiplicar por 1000000)
- `cityEthanol`: Eficiência na cidade com etanol (multiplicar por 1000000)

**Preços dos combustíveis (em reais):**
- `precoGasolina`: Preço da gasolina por litro (multiplicar por 1000000)
- `precoEtanol`: Preço do etanol por litro (multiplicar por 1000000)

**Como você dirigiu (%):**
- `behaviorCautious`: Quanto % dirigiu com cautela (multiplicar por 1000000)
- `behaviorNormal`: Quanto % dirigiu normal (multiplicar por 1000000)
- `behaviorAggressive`: Quanto % dirigiu agressivo (multiplicar por 1000000)

**Importante:** Todos os números devem ser multiplicados por 1000000 antes de enviar ao contrato.

**Exemplo:**
- 150 km = enviar 150000000
- R$ 6.47 = enviar 6470000
- 75% = enviar 75000000

---

## 📤 Dados de Saída (CalculationResult)

Quando você recebe o resultado, vem com estes dados:

- `tanqueGasoline`: % de gasolina que tinha no tanque
- `dtEstradaGasolina`: Quanto gastou de gasolina na estrada
- `dtEstradaEtanol`: Quanto gastou de etanol na estrada
- `dfEstrada`: Total gasto na estrada
- `dtCidadeGasolina`: Quanto gastou de gasolina na cidade
- `dtCidadeEtanol`: Quanto gastou de etanol na cidade
- `dfCidade`: Total gasto na cidade
- `propBonus`: Multiplicador de bônus pela forma de dirigir
- `e2Final`: Valor E2 final em reais
- `totalDistance`: Distância total percorrida

**Para ler os valores:** Dividir por 1000000

**Exemplo:**
- Se `e2Final` = 5460000, o valor real é R$ 5.46
- Se `totalDistance` = 230000000, a distância real é 230 km

---

## 🎯 Como Usar

### Passo 1: Preparar os dados

```javascript
const dados = {
    highwayDistance: 150 * 1000000,    // 150 km na estrada
    cityDistance: 80 * 1000000,        // 80 km na cidade
    ethanolPercent: 75 * 1000000,      // 75% etanol
    roadGasoline: 14.1 * 1000000,      // 14.1 km/L
    roadEthanol: 9.8 * 1000000,        // 9.8 km/L
    cityGasoline: 11.6 * 1000000,      // 11.6 km/L
    cityEthanol: 8.0 * 1000000,        // 8.0 km/L
    precoGasolina: 6.47 * 1000000,     // R$ 6.47/L
    precoEtanol: 4.94 * 1000000,       // R$ 4.94/L
    behaviorCautious: 60 * 1000000,    // 60% cauteloso
    behaviorNormal: 30 * 1000000,      // 30% normal
    behaviorAggressive: 10 * 1000000   // 10% agressivo
};
```

### Passo 2: Simular (opcional)

```javascript
const resultado = await contrato.simulateE2Calculation(dados);
const valorE2 = resultado.e2Final / 1000000;
console.log("E2 previsto: R$", valorE2);
```

### Passo 3: Criar NFT

```javascript
const [tokenId, e2Value] = await contrato.calculateE2AndTokenize(
    dados,
    enderecoDoUsuario
);
console.log("NFT criado:", tokenId);
console.log("Valor E2: R$", e2Value / 1000000);
```

### Passo 4: Ver detalhes depois

```javascript
const detalhes = await contrato.getCalculationDetails(tokenId);
console.log("Distância total:", detalhes.totalDistance / 1000000, "km");
console.log("E2:", detalhes.e2Final / 1000000, "reais");
```

---

## ⚠️ Observações

1. **Autorização**: Você precisa ser autorizado pelo dono do contrato antes de criar NFTs
2. **Escala**: Sempre multiplicar por 1000000 na entrada e dividir por 1000000 na saída
3. **Valores zero**: Eficiências e preços não podem ser zero
4. **Percentuais**: A soma de cauteloso + normal + agressivo deve ser 100%
5. **Gas**: Criar NFT custa gas, simular é grátis

---

## 📞 Resumo Rápido

**Para criar NFT:**
1. Prepare os dados com * 1000000
2. Chame `calculateE2AndTokenize`
3. Receba o tokenId e e2Value

**Para apenas consultar:**
- `simulateE2Calculation`: Testa cálculo
- `getCalculationDetails`: Ver dados de um NFT
- `balanceOf`: Ver quantos NFTs alguém tem

**Para administrar:**
- `setAuthorized`: Autorizar usuários (só o dono)

---

**Versão Simplificada**  
**Última atualização:** Outubro 2025