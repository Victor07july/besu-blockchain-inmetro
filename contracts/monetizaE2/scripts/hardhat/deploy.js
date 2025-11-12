import hre from "hardhat";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Para usar __dirname em ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Script de Deploy do CarbonCreditNFT_E2Calculator para Besu
 * 
 * Uso:
 *   npx hardhat run scripts/hardhat/deploy.js --network besu
 *   npx hardhat run scripts/hardhat/deploy.js --network localhost
 */

async function main() {
  console.log("🚀 Iniciando deploy do CarbonCreditNFT_E2Calculator...\n");

  // === 1. Obter informações da rede e signers ===
  const [deployer] = await hre.ethers.getSigners();
  const network = await hre.ethers.provider.getNetwork();
  
  console.log("📊 Informações da Rede:");
  console.log("  Network Name:", network.name);
  console.log("  Chain ID:", network.chainId.toString());
  console.log("  Deployer:", deployer.address);
  
  // Verificar saldo
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("  Balance:", hre.ethers.formatEther(balance), "ETH\n");

  if (balance === 0n) {
    throw new Error("❌ Deployer não tem saldo suficiente!");
  }

  // === 2. Parâmetros do Construtor ===
  // Constructor: constructor(uint256 maxMintable, uint256 mintInterval, address initialOwner)
  const MAX_MINTABLE = 10;      // Máximo de NFTs que podem ser mintados
  const MINT_INTERVAL = 10;     // Intervalo mínimo entre mints (em segundos)
  const INITIAL_OWNER = deployer.address; // Owner inicial do contrato

  console.log("⚙️  Parâmetros do Construtor:");
  console.log("  Max Mintable:", MAX_MINTABLE);
  console.log("  Mint Interval:", MINT_INTERVAL, "segundos");
  console.log("  Initial Owner:", INITIAL_OWNER, "\n");

  // === 3. Deploy do Contrato ===
  console.log("📝 Compilando contrato...");
  const CarbonCreditNFT = await hre.ethers.getContractFactory("CarbonCreditNFT_E2Calculator");
  
  console.log("🔄 Deploying contrato...");
  const carbonCredit = await CarbonCreditNFT.deploy(
    MAX_MINTABLE,
    MINT_INTERVAL,
    INITIAL_OWNER,
    {
      gasLimit: 5000000 // Gas limit aumentado para contratos complexos
    }
  );

  // Aguardar confirmação
  await carbonCredit.waitForDeployment();
  const contractAddress = await carbonCredit.getAddress();

  console.log("✅ Contrato deployado com sucesso!");
  console.log("  Contract Address:", contractAddress);
  console.log("  Transaction Hash:", carbonCredit.deploymentTransaction()?.hash, "\n");

  // === 4. Verificar Deploy ===
  console.log("🔍 Verificando deploy...");
  const owner = await carbonCredit.owner();
  const name = await carbonCredit.name();
  const symbol = await carbonCredit.symbol();
  
  console.log("  Owner:", owner);
  console.log("  Token Name:", name);
  console.log("  Token Symbol:", symbol);
  console.log("  Max Mintable:", (await carbonCredit.MAX_MINTABLE()).toString());
  console.log("  Mint Interval:", (await carbonCredit.MINT_INTERVAL()).toString(), "segundos\n");

  // === 5. Salvar informações de deploy ===
  const deploymentInfo = {
    network: network.name,
    chainId: network.chainId.toString(),
    contractName: "CarbonCreditNFT_E2Calculator",
    contractAddress: contractAddress,
    deployer: deployer.address,
    transactionHash: carbonCredit.deploymentTransaction()?.hash,
    blockNumber: carbonCredit.deploymentTransaction()?.blockNumber,
    timestamp: new Date().toISOString(),
    constructorArgs: {
      maxMintable: MAX_MINTABLE,
      mintInterval: MINT_INTERVAL,
      initialOwner: INITIAL_OWNER
    },
    contractDetails: {
      owner: owner,
      name: name,
      symbol: symbol
    }
  };

  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }

  const filename = `${network.name}_${contractAddress}.json`;
  const filepath = path.join(deploymentsDir, filename);
  
  fs.writeFileSync(filepath, JSON.stringify(deploymentInfo, null, 2));
  console.log("💾 Deployment info salvo em:", filepath);

  // Também salvar o endereço em um arquivo simples para referência rápida
  const addressFile = path.join(deploymentsDir, "latest.txt");
  fs.writeFileSync(addressFile, contractAddress);
  console.log("📝 Endereço salvo em:", addressFile, "\n");

  // === 6. Instruções pós-deploy ===
  console.log("📋 Próximos Passos:");
  console.log("  1. Verifique o contrato no explorador (se disponível)");
  console.log("  2. Teste mintar um NFT:");
  console.log(`     npx hardhat run scripts/hardhat/mint.js --network ${network.name}`);
  console.log("  3. Interaja com o contrato usando o endereço:", contractAddress, "\n");

  return {
    contract: carbonCredit,
    address: contractAddress,
    deploymentInfo
  };
}

// === Execução ===
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Erro durante o deploy:");
    console.error(error);
    process.exit(1);
  });

export { main };
