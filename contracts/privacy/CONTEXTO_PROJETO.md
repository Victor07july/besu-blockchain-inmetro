# Contexto do Projeto: Monetização de Carbono com Privacidade

## 📋 Visão Geral

Este projeto implementa um sistema de monetização de créditos de carbono para veículos flex (gasolina/etanol) usando blockchain (Hyperledger Besu) com foco em privacidade.

**Fórmula E1**: Calcula a diferença entre emissão teórica (Meta_CO2) e emissão real, monetizando pelo preço do carbono europeu.

## 🎯 Objetivo Principal

Criar um sistema onde motoristas são pagos por emitirem menos CO2 do que o esperado, preservando privacidade através de:
- **Implementação 1**: Pseudônimos HD (sem GPS) - PRODUÇÃO
- **Implementação 2**: Pseudônimos HD + GPS + Differential Privacy - PESQUISA

## 📂 Estrutura do Projeto

```
dapps/privacy/
├── dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv  # 33 viagens
├── implementacao1/  # Baseline - SEM GPS
│   ├── E1Registry.sol           # Contrato com cálculo on-chain
│   ├── deploy_e1_v2.py          # Deploy com compile + private key
│   ├── send_e1_data_v2.py       # Envia dados + mostra resultados
│   ├── PSEUDONIMOS_EXPLICACAO.md
│   └── CUSTOS_PSEUDONIMOS.md
├── implementacao2/  # Avançada - COM GPS + DP
│   ├── E1RegistryGPS.sol        # Contrato com coordenadas GPS
│   ├── apply_dp.py              # Aplica Differential Privacy
│   ├── send_e1_gps_data.py      # Script de envio com GPS
│   └── deploy_e1_gps.py         # Deploy
└── CONTEXTO_PROJETO.md          # Este arquivo
```

## 🔬 Fórmula E1 (Monetização)

### Cálculo:

```python
# 1. Meta de emissão (baseada em consumo do fabricante)
Meta_CO2 = (highway_dist × highway_emission) + (city_dist × city_emission)

# 2. Diferença
Diff = Meta_CO2 - Emissao_Real

# 3. Monetização
e1 = Diff × Carbon_Price / 1_000_000
```

### Constantes:
- `EMISSAO_GASOLINA = 1.720 kg/L` (1720 g/L)
- `EMISSAO_ETANOL = 1.510 kg/L` (1510 g/L)
- Carbon Price: €67-81/ton × R$6/€ ≈ R$400-500/ton

### Dados de Entrada:
- Distância rodovia/cidade (km)
- % etanol no tanque
- Consumo fabricante (km/L) - gasolina e etanol, rodovia e cidade
- Emissão real medida (g)
- Preço carbono (BRL/ton)

## 🔐 Implementação 1: E1 + Pseudônimos HD

### Objetivo
Sistema de produção sem dados sensíveis. Apenas emissões e consumo.

### Características:
- ✅ **Sem GPS**: Apenas distâncias agregadas
- ✅ **Pseudônimos HD**: Um endereço diferente por viagem (BIP-44)
- ✅ **Cálculo on-chain**: Transparência e auditabilidade
- ✅ **Zero risco de privacidade**: Dados não sensíveis

### Tecnologias:
- **Solidity 0.8.0**: Smart contract
- **eth_account**: Geração de pseudônimos HD
- **web3.py**: Interação blockchain
- **Hyperledger Besu**: Rede privada QBFT

### Pseudônimos HD:
```python
# Mnemonic fixo (teste): "test test test test..."
# Derivação: m/44'/60'/0'/0/{index}
# Resultado: 33 endereços únicos, mas recuperáveis

# Index 0 → 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
# Index 1 → 0x70997970C51812dc3A010C7d01b50e0d17dc79C8
# ...
```

### Compatibilidade MetaMask:
- Importar mnemonic → Mostra Account 1
- Clicar "Create Account" 32 vezes → Recupera todos os pseudônimos
- Ordem sempre a mesma

### Contrato E1Registry.sol:

**Structs:**
```solidity
struct TripParams {
    string vin;
    uint256 timestamp;
    uint256 highwayDistance;
    uint256 cityDistance;
    uint256 ethanolPercent;
    uint256 roadGasoline;      // Consumo fabricante
    uint256 roadEthanol;
    uint256 cityGasoline;
    uint256 cityEthanol;
    uint256 emissaoReal;       // Medido
    uint256 carbonPrice;
    address pseudonimo;
}

struct TripData {
    string vin;
    uint256 timestamp;
    uint256 totalDistance;
    uint256 emissaoReal;
    uint256 metaCO2;           // Calculado
    int256 diff;               // Pode ser negativo
    uint256 realPrice;
    uint256 valorE1;           // Monetização
    address pseudonimo;
    bool pago;
}
```

**Funções principais:**
- `registerTrip(TripParams)`: Recebe dados brutos, calcula E1 internamente
- `_calculateE1(TripParams)`: Função interna com lógica do cálculo
- `getTrip(uint256)`: Retorna TripData
- `getStats()`: Retorna (tripCount, totalPago, mediaValor)

**Precisão:**
- Todos os valores × 1e6 para evitar decimais em Solidity
- Exemplo: 5.72 km → 5_720_000

### Scripts Python:

**deploy_e1_v2.py:**
- Compila E1Registry.sol com solcx
- Deploy usando private key (não eth_sendTransaction)
- Middleware POA para Besu/QBFT
- Salva address/ABI em JSON

**send_e1_data_v2.py:**
- Processa CSV
- Gera pseudônimo HD por viagem
- Envia TripParams ao contrato
- Contrato calcula Meta_CO2, Diff, e1
- Mostra resultados calculados on-chain
- Salva JSON com pseudônimos e TxHashes

### Trade-offs:

**Privacidade:**
- ✅ Pagamento desvinculado de identidade
- ✅ Cada viagem = endereço diferente
- ✅ Dificulta linkage de viagens

**Custo:**
- ✅ Besu (privado): custo zero
- ⚠️ Ethereum mainnet: $1-5 × 33 transferências para consolidar
- ✅ Polygon/L2: $0.01-0.10 × 33

**Solução de consolidação:**
- Contrato apenas registra valores (não paga automaticamente)
- Pagamento posterior pelo oracle/governo
- Usuário pode deixar acumulado e consolidar quando quiser

## 🌍 Implementação 2: E1 + GPS + Differential Privacy

### Objetivo
Proof-of-concept para pesquisa. Adiciona GPS (dados sensíveis) protegidos por DP.

### Características:
- ✅ **Pseudônimos HD**: Mantém da implementação 1
- ✅ **GPS**: Coordenadas start/end da viagem
- ✅ **Differential Privacy (DP)**: Ruído matemático nas coordenadas
- ✅ **Fator de mobilidade**: Cálculo baseado em distância real GPS
- ⚠️ **Pesquisa**: Não para produção

### Differential Privacy:

**Conceito:**
Adiciona ruído Laplace às coordenadas GPS para proteger localização exata.

**Parâmetro epsilon (ε):**
- ε = 0.1 → Máxima privacidade (±1-2 km erro)
- ε = 1.0 → Privacidade moderada (±100-200 m)
- ε = 10.0 → Privacidade mínima (±10-20 m)

**Fórmula:**
```python
noise = np.random.laplace(loc=0, scale=sensitivity/epsilon)
privatized_value = original_value + noise
```

**Propriedades matemáticas:**
- Garantia formal de privacidade
- Indistinguibilidade de vizinhos
- Mantém utilidade estatística

### Dados GPS sensíveis:
- `start_lat`, `start_lon`: Pode revelar residência
- `end_lat`, `end_lon`: Pode revelar trabalho/escola
- Padrões de movimento: Rotinas diárias

### Contrato E1RegistryGPS.sol:

Estende E1Registry.sol adicionando:
```solidity
struct GPSLocation {
    int256 latitude;   // × 1e6 (ex: -5.7945° → -5794500)
    int256 longitude;  // × 1e6
}

struct TripGPSParams {
    // ... campos do TripParams ...
    GPSLocation startLocation;  // Com DP aplicado
    GPSLocation endLocation;    // Com DP aplicado
}
```

### Workflow Implementação 2:

```
1. CSV com coordenadas originais
   ↓
2. apply_dp.py (epsilon = 1.0)
   ↓
3. Coordenadas com ruído (privatizadas)
   ↓
4. send_e1_gps_data.py
   ↓
5. E1RegistryGPS.sol (armazena GPS + DP)
```

### Próximos passos (futuro):

**Fase 3: DP + ZKP (Zero-Knowledge Proofs)**
- ZKP prova distância sem revelar coordenadas
- DP protege coordenadas armazenadas
- Máxima privacidade + verificabilidade

**Ferramentas ZKP:**
- Circom/SnarkJS
- Noir (Aztec)
- ZoKrates

## 📊 Dados do CSV

**Arquivo:** `dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv`

**33 viagens** com colunas:
- `VIN`: Identificador do veículo
- `start_time`: Timestamp ISO
- `highway (distance)`: km em rodovia
- `city (distance)`: km em cidade
- `ethanol (%)`: Percentual de etanol no tanque
- `co2_etanol_original_gas_1720_flex`: Emissão real medida (g)

**Dados adicionados via arrays Python:**
- Consumo fabricante (city/road, gasoline/ethanol) - km/L
- Carbon_Price_European (€/ton)
- Euro_price (BRL/€)

## 🔧 Stack Técnico

### Blockchain:
- **Hyperledger Besu 23.4.1**: Cliente Ethereum
- **Consensus**: QBFT (Byzantine Fault Tolerant)
- **Network**: Rede privada local
- **Nodes**: rpcnode (8545), member1 (20000), validators

### Smart Contracts:
- **Solidity**: 0.8.0
- **Compiler**: solcx (py-solc-x)
- **Deployer**: Private key (não eth_accounts)

### Python:
- **web3.py**: 7.x - Interação blockchain
- **eth_account**: 0.13.x - HD wallets BIP-44
- **pandas**: Processamento CSV
- **numpy**: Cálculos + DP (ruído Laplace)
- **solcx**: Compilação Solidity

### Middlewares:
- **ExtraDataToPOAMiddleware**: Para QBFT/POA chains

## 🚀 Como Executar

### Implementação 1 (Baseline):

```bash
cd dapps/privacy/implementacao1

# 1. Deploy
source ../../monetiza_co2/scripts/myenv/bin/activate
python3 deploy_e1_v2.py

# 2. Enviar dados
python3 send_e1_data_v2.py

# 3. Ver resultados
cat e1_send_results.json
```

### Implementação 2 (GPS + DP):

```bash
cd dapps/privacy/implementacao2

# 1. Aplicar DP (gera CSV com coordenadas privatizadas)
python3 apply_dp.py --epsilon 1.0

# 2. Deploy contrato GPS
python3 deploy_e1_gps.py

# 3. Enviar dados com GPS
python3 send_e1_gps_data.py
```

## 📝 Arquivos de Referência

### Implementação 1:
- **E1Registry.sol**: Contrato principal
- **deploy_e1_v2.py**: Script de deploy completo
- **send_e1_data_v2.py**: Script de envio com feedback
- **PSEUDONIMOS_EXPLICACAO.md**: Como funcionam pseudônimos HD
- **CUSTOS_PSEUDONIMOS.md**: Trade-offs de custo

### Implementação 2:
- **E1RegistryGPS.sol**: Contrato com GPS
- **apply_dp.py**: Aplica Differential Privacy
- **send_e1_gps_data.py**: Envia com GPS privatizado
- **README_DP.md**: Explicação de DP

### Referências externas:
- `dapps/monetiza_co2/contracts/E1/CarbonCreditNFT_E1.sol`: Contrato original de referência
- `dapps/monetiza_co2/contracts/E1/carbonCreditE1.py`: Cálculo Python original

## 🔑 Chaves e Configurações

### Oracle Account (Deployer):
```
Private Key: 0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3
Address: 0xC9C913c8c3C1Cd416d80A0abF475db2062F161f6
```

### Mnemonic HD (Teste - NÃO usar em produção):
```
test test test test test test test test test test test junk
```

### RPC URLs:
- RPC Node: `http://localhost:8545`
- Member 1: `http://localhost:20000`

## 📚 Conceitos Importantes

### HD Wallets (BIP-44):
- Hierarchical Deterministic wallets
- Path: `m/44'/60'/0'/0/{index}` (Ethereum padrão)
- Mesmo mnemonic sempre gera mesmos endereços
- Recuperável via MetaMask/qualquer wallet BIP-44

### Differential Privacy:
- Garantia matemática de privacidade
- Ruído Laplace proporcional a sensitivity/epsilon
- Trade-off precisão × privacidade
- Propriedade de composição

### Zero-Knowledge Proofs (futuro):
- Prova matemática sem revelar dados
- "Provador" convence "Verificador"
- Aplicação: Provar distância sem revelar coordenadas

## ⚠️ Avisos Importantes

1. **Mnemonic de teste**: Trocar em produção
2. **Private key hardcoded**: Só para desenvolvimento local
3. **Implementação 2**: Apenas research/PoC
4. **Besu local**: Sem persistência entre restarts
5. **Gas zero**: Apenas em rede privada

## 🎓 Para Continuar o Projeto

### Próximas tarefas sugeridas:

**Curto prazo:**
- [ ] Testar Implementação 2 com diferentes valores de epsilon
- [ ] Comparar utilidade dos dados (GPS original vs DP)
- [ ] Implementar função de pagamento no contrato
- [ ] Gerar mnemonic seguro para produção

**Médio prazo:**
- [ ] Adicionar ZKP para provas de distância
- [ ] Implementar batched payments eficiente
- [ ] Criar interface web para visualização
- [ ] Testes com mais viagens (escala)

**Longo prazo:**
- [ ] Deploy em testnet pública (Sepolia/Goerli)
- [ ] Integração com oráculos externos
- [ ] Sistema de auditoria e compliance
- [ ] Paper acadêmico sobre DP+ZKP em mobilidade

## 📞 Estado Atual do Projeto

**✅ Completo:**
- Implementação 1: Contrato + deploy + envio funcionando
- Pseudônimos HD implementados e testados
- Cálculo E1 on-chain verificado
- Documentação básica criada

**🚧 Em progresso:**
- Implementação 2: Estrutura criada, aguardando código

**⏳ Planejado:**
- Testes de epsilon diferentes
- Implementação ZKP (Fase 3)
- Interface web

---

**Data da última atualização**: Janeiro 2026

**Versão do Claude**: Claude Sonnet 4.5

**Contexto preservado para continuidade**: Este documento contém toda a informação necessária para que outra instância do Claude possa continuar o desenvolvimento do projeto sem perda de contexto.
