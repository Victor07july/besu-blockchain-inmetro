import "@nomicfoundation/hardhat-toolbox";
import dotenv from "dotenv";

dotenv.config();

/** @type import('hardhat/config').HardhatUserConfig */
export default {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      },
      viaIR: true  // Ativar para resolver "Stack too deep"
    }
  },
  networks: {
    // Rede local Besu
    besu: {
      url: process.env.BESU_RPC_URL || "http://localhost:8545",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 1337,
      gas: "auto",
      gasPrice: "auto"
    },
    // Localhost para testes
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337
    },
    // Hardhat network para testes
    hardhat: {
      chainId: 31337,
      accounts: {
        count: 10,
        initialBalance: "10000000000000000000000" // 10000 ETH
      }
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  gasReporter: {
    enabled: process.env.REPORT_GAS !== undefined,
    currency: "USD"
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  }
};