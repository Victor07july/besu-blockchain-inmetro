# 🚀 Deploy do CarbonCreditNFT_E2 com Hardhat

Scripts para deploy e interação com o contrato CarbonCreditNFT_E2Calculator usando Hardhat no Besu.

## 📋 Pré-requisitos

```bash
# 1. Instalar dependências
npm install

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 🔧 Configuração

### Arquivo `.env`

```bash
# Chave privada da conta que fará o deploy
PRIVATE_KEY=0x60bbe10a196a4e71451c0f6e9ec9beab454c2a5ac0542aa5b8b733ff5719fec3

# URL do RPC do Besu
BESU_RPC_URL=http://127.0.0.1:8545
```

### Verificar Configuração

```bash
# Ver redes configuradas
npx hardhat config

# Ver contas disponíveis
npx hardhat accounts --network besu
```

## 📦 Deploy do Contrato

### Deploy na rede Besu

```bash
# Deploy básico
npx hardhat run scripts/hardhat/deploy.js --network besu

# Com mais verbosidade
DEBUG=* npx hardhat run scripts/hardhat/deploy.js --network besu
```

### Deploy em localhost (Hardhat Network)

```bash
# Primeiro, iniciar o node local
npx hardhat node

# Em outro terminal, fazer o deploy
npx hardhat run scripts/hardhat/deploy.js --network localhost
```

## 🎨 Mintar NFTs

### Após o deploy bem-sucedido:

```bash
# Mintar um NFT com dados de exemplo
npx hardhat run scripts/hardhat/mint.js --network besu
```

### Mintar com dados customizados:

Edite o arquivo `scripts/hardhat/mint.js` e modifique os valores em `calculationParams`:

```javascript
const calculationParams = {
  highwayDistance: BigInt(150 * 1e6),      // 150 km
  cityDistance: BigInt(75 * 1e6),          // 75 km
  ethanolPercent: BigInt(30 * 1e6),        // 30%
  // ... outros parâmetros
};
```

## 📊 Informações Salvas

Os scripts salvam automaticamente informações sobre deploy e mints:

```
scripts/
  deployments/
    latest.txt                           # Endereço do último contrato deployado
    besu_0x1234....json                 # Info completa do deploy
    mints/
      mint_0_0xabc....json              # Info de cada NFT mintado
```

## 🔍 Verificar Contrato

### Usando Hardhat Console

```bash
# Abrir console interativo
npx hardhat console --network besu

# Dentro do console:
const CarbonCredit = await ethers.getContractFactory("CarbonCreditNFT_E2Calculator");
const carbon = CarbonCredit.attach("ENDEREÇO_DO_CONTRATO");

// Ver informações
await carbon.name();
await carbon.symbol();
await carbon.totalSupply();
await carbon.owner();
```

### Verificar NFT específico

```javascript
// No console do Hardhat
const tokenId = 0;
const nftData = await carbon.getNFTData(tokenId);
console.log({
  e2Value: nftData.e2Value.toString(),
  vehicleId: nftData.vehicleId,
  vehicleType: nftData.vehicleType,
  mintTimestamp: new Date(Number(nftData.mintTimestamp) * 1000).toISOString()
});
```

## 🧪 Testes

### Rodar testes do contrato

```bash
# Todos os testes
npx hardhat test

# Testes específicos
npx hardhat test test/CarbonCreditNFT.test.js

# Com coverage
npx hardhat coverage
```

## 🐛 Troubleshooting

### Erro: "Insufficient funds"

A conta precisa ter ETH para pagar o gas. Verifique o saldo:

```bash
npx hardhat run scripts/check-balance.js --network besu
```

### Erro: "Nonce too high"

Resete o nonce da conta:

```bash
npx hardhat clean
```

### Erro: "Contract not deployed"

Verifique se o endereço em `deployments/latest.txt` está correto e se o contrato foi realmente deployado.

### Conexão com Besu recusada

Verifique se:
1. O Besu está rodando: `docker ps | grep besu`
2. A porta 8545 está acessível: `curl http://127.0.0.1:8545`
3. A URL no `.env` está correta

## 📝 Estrutura de Parâmetros

### Constructor do Contrato

```solidity
constructor(
  uint256 maxMintable,    // Máximo de NFTs que podem ser mintados
  uint256 mintInterval,   // Intervalo mínimo entre mints (segundos)
  address initialOwner    // Dono inicial do contrato
)
```

### Função mintE2NFT

```solidity
struct CalculationParams {
  uint256 highwayDistance;    // km * 1e6
  uint256 cityDistance;       // km * 1e6
  uint256 ethanolPercent;     // % * 1e6
  uint256 roadGasoline;       // km/L * 1e6
  uint256 roadEthanol;        // km/L * 1e6
  uint256 cityGasoline;       // km/L * 1e6
  uint256 cityEthanol;        // km/L * 1e6
  uint256 priceGasoline;      // R$ * 1e6
  uint256 priceEthanol;       // R$ * 1e6
  uint256 co2Gasoline;        // g/L * 1e6
  uint256 co2Ethanol;         // g/L * 1e6
}

struct VehicleData {
  string vehicleId;
  string vehicleType;
  uint256 year;
}
```

**Nota:** Todos os valores numéricos devem ser multiplicados por `1e6` (1 milhão) para manter 6 casas decimais de precisão.

## 🔗 Links Úteis

- [Documentação Hardhat](https://hardhat.org/docs)
- [Documentação Besu](https://besu.hyperledger.org/)
- [Documentação OpenZeppelin](https://docs.openzeppelin.com/)

## 💡 Exemplos de Uso

### Deploy + Mint completo

```bash
# 1. Deploy
npx hardhat run scripts/hardhat/deploy.js --network besu

# 2. Anotar o endereço do contrato (será mostrado no output)

# 3. Mintar NFT
npx hardhat run scripts/hardhat/mint.js --network besu

# 4. Verificar
npx hardhat console --network besu
# No console:
const addr = "SEU_ENDERECO_AQUI";
const CarbonCredit = await ethers.getContractFactory("CarbonCreditNFT_E2Calculator");
const carbon = CarbonCredit.attach(addr);
console.log("Total Supply:", (await carbon.totalSupply()).toString());
```

## 📞 Suporte

Se encontrar problemas, verifique:
1. Logs do Besu: `docker logs rpcnode-admin`
2. Status dos containers: `docker ps`
3. Configurações de rede no `hardhat.config.js`
