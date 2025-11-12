import hre from "hardhat";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Para usar __dirname em ES Modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Script para Mintar NFT do CarbonCreditNFT_E2Calculator
 * 
 * Uso:
 *   npx hardhat run scripts/hardhat/mint.js --network besu
 */

async function main() {
  console.log("🎨 Iniciando mint de CarbonCredit NFT...\n");

  // === 1. Carregar endereço do contrato deployado ===
  const deploymentsDir = path.join(__dirname, "../deployments");
  const addressFile = path.join(deploymentsDir, "latest.txt");
  
  let contractAddress;
  if (fs.existsSync(addressFile)) {
    contractAddress = fs.readFileSync(addressFile, "utf8").trim();
    console.log("📄 Contrato carregado de:", addressFile);
  } else {
    // Se não encontrar, pedir ao usuário
    console.log("⚠️  Arquivo latest.txt não encontrado.");
    console.log("Por favor, forneça o endereço do contrato:");
    // Em produção, você pode usar readline ou argv para pegar o endereço
    throw new Error("Endereço do contrato não encontrado. Execute primeiro o deploy.js");
  }

  console.log("  Contract Address:", contractAddress, "\n");

  // === 2. Conectar ao contrato ===
  const [signer] = await hre.ethers.getSigners();
  console.log("👤 Signer:", signer.address);
  
  const CarbonCreditNFT = await hre.ethers.getContractFactory("CarbonCreditNFT_E2Calculator");
  const carbonCredit = CarbonCreditNFT.attach(contractAddress);

  // === 3. Dados de exemplo para cálculo E2 ===
  // Estes valores devem ser multiplicados por 1e6 conforme o contrato espera
  const calculationParams = {
    highwayDistance: BigInt(100 * 1e6),      // 100 km
    cityDistance: BigInt(50 * 1e6),          // 50 km
    ethanolPercent: BigInt(27 * 1e6),        // 27%
    roadGasoline: BigInt(15 * 1e6),          // 15 km/L
    roadEthanol: BigInt(10 * 1e6),           // 10 km/L
    cityGasoline: BigInt(12 * 1e6),          // 12 km/L
    cityEthanol: BigInt(8 * 1e6),            // 8 km/L
    priceGasoline: BigInt(6 * 1e6),          // R$ 6,00
    priceEthanol: BigInt(4 * 1e6),           // R$ 4,00
    co2Gasoline: BigInt(2300 * 1e6),         // 2300 g/L
    co2Ethanol: BigInt(1500 * 1e6)           // 1500 g/L
  };

  const vehicleData = {
    vehicleId: "ABC1234",
    vehicleType: "Sedan",
    year: 2023
  };

  console.log("📊 Parâmetros de Cálculo:");
  console.log("  Highway Distance:", Number(calculationParams.highwayDistance) / 1e6, "km");
  console.log("  City Distance:", Number(calculationParams.cityDistance) / 1e6, "km");
  console.log("  Ethanol %:", Number(calculationParams.ethanolPercent) / 1e6, "%");
  console.log("  Vehicle ID:", vehicleData.vehicleId);
  console.log("  Vehicle Type:", vehicleData.vehicleType, "\n");

  // === 4. Mintar NFT ===
  console.log("🔄 Mintando NFT...");
  
  try {
    const tx = await carbonCredit.mintE2NFT(
      calculationParams,
      vehicleData,
      {
        gasLimit: 3000000
      }
    );

    console.log("  Transaction Hash:", tx.hash);
    console.log("  Aguardando confirmação...");
    
    const receipt = await tx.wait();
    console.log("✅ NFT mintado com sucesso!");
    console.log("  Block Number:", receipt.blockNumber);
    console.log("  Gas Used:", receipt.gasUsed.toString(), "\n");

    // === 5. Buscar informações do NFT ===
    const totalSupply = await carbonCredit.totalSupply();
    const tokenId = totalSupply - 1n; // Último token mintado
    
    console.log("🎫 Informações do NFT:");
    console.log("  Token ID:", tokenId.toString());
    console.log("  Total Supply:", totalSupply.toString());
    
    // Buscar dados do NFT
    const nftData = await carbonCredit.getNFTData(tokenId);
    console.log("  E2 Value:", nftData.e2Value.toString());
    console.log("  Mint Timestamp:", new Date(Number(nftData.mintTimestamp) * 1000).toISOString());
    console.log("  Vehicle ID:", nftData.vehicleId);
    console.log("  Vehicle Type:", nftData.vehicleType, "\n");

    // === 6. Salvar informações do mint ===
    const mintInfo = {
      network: (await hre.ethers.provider.getNetwork()).name,
      contractAddress: contractAddress,
      tokenId: tokenId.toString(),
      transactionHash: tx.hash,
      blockNumber: receipt.blockNumber,
      gasUsed: receipt.gasUsed.toString(),
      minter: signer.address,
      timestamp: new Date().toISOString(),
      nftData: {
        e2Value: nftData.e2Value.toString(),
        vehicleId: nftData.vehicleId,
        vehicleType: nftData.vehicleType,
        vehicleYear: nftData.vehicleYear.toString()
      },
      calculationParams: {
        highwayDistance: Number(calculationParams.highwayDistance) / 1e6 + " km",
        cityDistance: Number(calculationParams.cityDistance) / 1e6 + " km",
        ethanolPercent: Number(calculationParams.ethanolPercent) / 1e6 + "%"
      }
    };

    const mintsDir = path.join(deploymentsDir, "mints");
    if (!fs.existsSync(mintsDir)) {
      fs.mkdirSync(mintsDir, { recursive: true });
    }

    const mintFilename = `mint_${tokenId}_${tx.hash.substring(0, 10)}.json`;
    const mintFilepath = path.join(mintsDir, mintFilename);
    
    fs.writeFileSync(mintFilepath, JSON.stringify(mintInfo, null, 2));
    console.log("💾 Mint info salvo em:", mintFilepath, "\n");

    console.log("🎉 Processo concluído com sucesso!");

  } catch (error) {
    if (error.message.includes("Too soon to mint")) {
      console.error("❌ Erro: Intervalo mínimo entre mints não foi respeitado.");
      console.error("   Aguarde alguns segundos e tente novamente.");
    } else if (error.message.includes("Max mintable reached")) {
      console.error("❌ Erro: Limite máximo de NFTs atingido.");
    } else {
      throw error;
    }
  }
}

// === Execução ===
main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Erro durante o mint:");
    console.error(error);
    process.exit(1);
  });

export { main };
