# Documentação Simples - CarbonCreditNFT E2

## 📌 O que é este contrato?

Um contrato que calcula o valor **E2** (custo de combustível em reais) baseado em dados de viagem e cria um NFT com esse valor. O contrato também possui um **marketplace integrado** onde os NFTs podem ser comprados e vendidos usando **ETH** (Ethereum).

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

## 💰 MARKETPLACE - Compra e Venda de NFTs

### 5. setBrlPerEth

**O que faz:**  
Ajusta a taxa de conversão BRL/ETH (quantos reais vale 1 ETH).

**Recebe:**
- `newRate`: Nova taxa em BRL multiplicado por 1000000 (ex: 15.000 BRL = 15000000000)

**Retorna:**  
Nada.

**Quem pode usar:**  
Apenas o dono do contrato.

---

### 6. convertBRLtoETH

**O que faz:**  
Converte um valor em BRL para ETH usando a taxa atual.

**Recebe:**
- `brlAmount`: Valor em BRL multiplicado por 1000000

**Retorna:**
- Valor equivalente em wei (1 ETH = 10^18 wei)

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 7. listToken

**O que faz:**  
Coloca seu NFT à venda no marketplace por um preço em BRL.

**Recebe:**
- `tokenId`: Número do NFT
- `priceBRL`: Preço desejado em BRL multiplicado por 1000000

**Retorna:**  
Nada.

**Quem pode usar:**  
Apenas o dono do NFT.

---

### 8. delistToken

**O que faz:**  
Remove seu NFT da venda.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**  
Nada.

**Quem pode usar:**  
Apenas o dono do NFT que está listado.

---

### 9. buyToken

**O que faz:**  
Compra um NFT que está à venda, pagando em ETH. O ETH é transferido automaticamente do comprador para o vendedor.

**Recebe:**
- `tokenId`: Número do NFT

**Recebe também (via transação):**
- `msg.value`: Quantidade de ETH enviada (deve ser >= preço do NFT)

**Retorna:**  
Nada.

**Quem pode usar:**  
Qualquer pessoa (exceto o próprio dono do NFT).

**Observações:**
- Reembolsa automaticamente se você enviar ETH a mais
- Remove o NFT da venda após compra
- Transfere o NFT para o comprador

---

### 10. getAllTokensWithPrices

**O que faz:**  
Lista TODOS os NFTs existentes com seus valores E2, preços (BRL e ETH), donos e status de venda.

**Recebe:**  
Nada.

**Retorna:**
- `tokenIds`: Array com números dos NFTs
- `e2Values`: Array com valores E2 de cada NFT
- `pricesBRL`: Array com preços em BRL (0 se não está à venda)
- `pricesETH`: Array com preços em ETH (0 se não está à venda)
- `owners`: Array com endereços dos donos
- `listed`: Array com true/false indicando se está à venda

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 11. isListed

**O que faz:**  
Verifica se um NFT está à venda.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- true se está à venda, false se não

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 12. listingPriceBRL

**O que faz:**  
Mostra o preço de venda de um NFT em BRL.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Preço em BRL multiplicado por 1000000 (0 se não está à venda)

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 13. brlPerEth

**O que faz:**  
Mostra a taxa de conversão atual (quantos BRL vale 1 ETH).

**Recebe:**  
Nada.

**Retorna:**
- Taxa em BRL multiplicado por 1000000

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

## 🔧 FUNÇÕES ADMINISTRATIVAS

### 14. setAuthorized

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

### 15. nextTokenId

**O que faz:**  
Mostra qual será o número do próximo NFT.

**Recebe:**  
Nada.

**Retorna:**
- Número do próximo token

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

## 📋 FUNÇÕES DE CONSULTA

### 16. authorized

**O que faz:**  
Verifica se um endereço está autorizado a criar NFTs.

**Recebe:**
- `address`: Endereço para verificar

**Retorna:**
- true se autorizado, false se não

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 17. tokenCalculations

**O que faz:**  
Acessa diretamente os cálculos armazenados de um NFT.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Estrutura com os cálculos

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 18. owner

**O que faz:**  
Mostra quem é o dono do contrato.

**Recebe:**  
Nada.

**Retorna:**
- Endereço do dono

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 19. balanceOf

**O que faz:**  
Mostra quantos NFTs um endereço possui.

**Recebe:**
- `address`: Endereço para verificar

**Retorna:**
- Quantidade de NFTs

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 20. tokenOfOwnerByIndex

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

### 21. transferFrom

**O que faz:**  
~~Transfere um NFT de um endereço para outro.~~

**⚠️ BLOQUEADO:** Esta função não pode mais ser usada diretamente. Para negociar NFTs, use a função `buyToken()` do marketplace.

**Recebe:**
- `from`: Endereço atual do dono
- `to`: Endereço que vai receber
- `tokenId`: Número do NFT

**Retorna:**  
Erro: "Use buyToken() para negociar"

**Quem pode usar:**  
Ninguém (função bloqueada para segurança do marketplace).

---

### 22. safeTransferFrom

**O que faz:**  
~~Transfere um NFT com verificação de segurança.~~

**⚠️ BLOQUEADO:** Esta função não pode mais ser usada diretamente. Para negociar NFTs, use a função `buyToken()` do marketplace.

**Recebe:**
- `from`: Endereço atual do dono
- `to`: Endereço que vai receber
- `tokenId`: Número do NFT

**Retorna:**  
Erro: "Use buyToken() para negociar"

**Quem pode usar:**  
Ninguém (função bloqueada para segurança do marketplace).

---

### 23. approve

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

### 24. setApprovalForAll

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

### 25. getApproved

**O que faz:**  
Verifica quem está aprovado para transferir um NFT específico.

**Recebe:**
- `tokenId`: Número do NFT

**Retorna:**
- Endereço aprovado (ou endereço zero se ninguém)

**Quem pode usar:**  
Qualquer pessoa (é grátis, só consulta).

---

### 26. isApprovedForAll

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

## 💰 Como Usar o Marketplace

### Passo 1: Listar NFT à venda

```javascript
// Listar por R$ 100
const precoBRL = 100 * 1000000;
await contrato.listToken(tokenId, precoBRL);
console.log("NFT listado à venda!");
```

### Passo 2: Ver NFTs disponíveis

```javascript
const resultado = await contrato.getAllTokensWithPrices();

for (let i = 0; i < resultado.tokenIds.length; i++) {
    if (resultado.listed[i]) {
        console.log("Token ID:", resultado.tokenIds[i].toString());
        console.log("Dono:", resultado.owners[i]);
        console.log("Preço BRL:", resultado.pricesBRL[i] / 1000000);
        console.log("Preço ETH:", ethers.formatEther(resultado.pricesETH[i]));
        console.log("---");
    }
}
```

### Passo 3: Comprar NFT com ETH

```javascript
// Verificar preço
const priceBRL = await contrato.listingPriceBRL(tokenId);
const priceETH = await contrato.convertBRLtoETH(priceBRL);

// Comprar enviando ETH
await contrato.buyToken(tokenId, { value: priceETH });
console.log("NFT comprado!");
```

### Passo 4: Remover da venda

```javascript
await contrato.delistToken(tokenId);
console.log("NFT removido da venda");
```

### Passo 5: Ajustar taxa BRL/ETH (apenas owner)

```javascript
// Definir 1 ETH = 15.000 BRL
const taxa = 15000 * 1000000;
await contrato.setBrlPerEth(taxa);
console.log("Taxa atualizada!");
```

---

## ⚠️ Observações

1. **Autorização**: Você precisa ser autorizado pelo dono do contrato antes de criar NFTs
2. **Escala**: Sempre multiplicar por 1000000 na entrada e dividir por 1000000 na saída
3. **Valores zero**: Eficiências e preços não podem ser zero
4. **Percentuais**: A soma de cauteloso + normal + agressivo deve ser 100%
5. **Gas**: Criar NFT custa gas, simular é grátis
6. **Transferências bloqueadas**: Não é possível transferir NFTs diretamente. Use o marketplace (`buyToken()`) para negociar
7. **Preços em ETH**: O preço de venda é definido em BRL mas a compra é feita em ETH (conversão automática)
8. **Taxa de conversão**: O owner do contrato controla a taxa BRL/ETH usada nas transações
9. **Reembolso automático**: Se você enviar mais ETH que o necessário, o excesso é devolvido automaticamente

---

## 📞 Resumo Rápido

**Para criar NFT:**
1. Prepare os dados com * 1000000
2. Chame `calculateE2AndTokenize`
3. Receba o tokenId e e2Value

**Para vender NFT:**
1. Chame `listToken(tokenId, precoBRL)`
2. Aguarde comprador
3. Receba ETH automaticamente na compra

**Para comprar NFT:**
1. Veja NFTs disponíveis com `getAllTokensWithPrices()`
2. Chame `buyToken(tokenId)` enviando ETH suficiente
3. Receba o NFT automaticamente

**Para apenas consultar:**
- `simulateE2Calculation`: Testa cálculo
- `getCalculationDetails`: Ver dados de um NFT
- `getAllTokensWithPrices`: Ver todos NFTs e preços
- `balanceOf`: Ver quantos NFTs alguém tem
- `isListed`: Verificar se NFT está à venda

**Para administrar:**
- `setAuthorized`: Autorizar usuários (só o dono)
- `setBrlPerEth`: Ajustar taxa de conversão (só o dono)

---

**Versão Simplificada com Marketplace**  
**Última atualização:** Novembro 2025


<!--Ultimas alteração: lista de tokens, transferencia de carteira por carteira, subtraindo valor da carteira>