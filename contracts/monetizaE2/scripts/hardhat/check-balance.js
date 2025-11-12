import hre from "hardhat";

/**
 * Script para verificar saldo e informações da conta
 * 
 * Uso:
 *   npx hardhat run scripts/hardhat/check-balance.js --network besu
 */

async function main() {
  console.log("💰 Verificando saldo da conta...\n");

  // Obter signers
  const signers = await hre.ethers.getSigners();
  const network = await hre.ethers.provider.getNetwork();

  console.log("📊 Informações da Rede:");
  console.log("  Network Name:", network.name);
  console.log("  Chain ID:", network.chainId.toString(), "\n");

  console.log("👥 Contas Disponíveis:\n");

  for (let i = 0; i < signers.length; i++) {
    const signer = signers[i];
    const address = signer.address;
    const balance = await hre.ethers.provider.getBalance(address);
    const balanceInEth = hre.ethers.formatEther(balance);

    console.log(`  Conta ${i + 1}:`);
    console.log(`    Address: ${address}`);
    console.log(`    Balance: ${balanceInEth} ETH`);
    console.log(`    Balance: ${balance.toString()} Wei\n`);
  }

  // Informações adicionais do provider
  try {
    const blockNumber = await hre.ethers.provider.getBlockNumber();
    const gasPrice = await hre.ethers.provider.getFeeData();
    
    console.log("🔗 Informações da Blockchain:");
    console.log("  Block Number:", blockNumber);
    console.log("  Gas Price:", hre.ethers.formatUnits(gasPrice.gasPrice || 0n, "gwei"), "gwei");
    console.log("  Max Fee Per Gas:", gasPrice.maxFeePerGas ? hre.ethers.formatUnits(gasPrice.maxFeePerGas, "gwei") + " gwei" : "N/A");
    console.log("  Max Priority Fee:", gasPrice.maxPriorityFeePerGas ? hre.ethers.formatUnits(gasPrice.maxPriorityFeePerGas, "gwei") + " gwei" : "N/A");
  } catch (error) {
    console.log("⚠️  Não foi possível obter informações adicionais da blockchain");
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error("\n❌ Erro:");
    console.error(error);
    process.exit(1);
  });
