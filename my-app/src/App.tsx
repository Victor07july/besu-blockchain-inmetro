import { useState } from 'react'

import './App.css'
import { MetaMaskSDK } from "@metamask/sdk"
import { ethers } from 'ethers';
function App() {
  const MMSDK = new MetaMaskSDK({
    dappMetadata: {
      name: "Example JavaScript Dapp",
      url: window.location.href,
    },
    preferDesktop: true,
  })

  // Network configurations

  async function connect() {


    const network = {
      chainId: "0x539",
      name: "Besu",
      rpcUrls: ["http://localhost:8545"],
      nativeCurrency: {
        name: "Ethereum",
        symbol: "ETH",
        decimals: 18
      },
    }
    const ethereum = MMSDK.getProvider()

    // Connect to MetaMask
    const accounts = await MMSDK.connect()


    // Make requests
    const result = await ethereum?.request({
      method: "eth_accounts",
      params: []
    })

    try {
      // Try to switch to the network
      await ethereum?.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: network?.chainId }]
      });
    } catch (erro: any) {
      // If the error code is 4902, the network needs to be added
      if (erro.code === 4902) {
        try {
          await ethereum?.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: network.chainId,
              chainName: network.name,
              rpcUrls: network.rpcUrls,
              nativeCurrency: network.nativeCurrency,

            }]
          });

          await ethereum?.request({
            method: "wallet_switchEthereumChain",
            params: [{
              chainId: network.chainId,
              chainName: network.name,
              rpcUrls: network.rpcUrls,
              nativeCurrency: network.nativeCurrency,

            }]
          });
        } catch (addError) {
          console.error("Error adding network:", addError);
        }
      } else {
        console.error("Error switching network:", erro);
      }
    }


  }


  async function receive() {
    const ethereum = MMSDK.getProvider()

    // Connect to MetaMask
    const accounts = await MMSDK.connect()

    const ob = {
      acc: accounts[0],

    }
    fetch('http://localhost:3050/receive', {
      method: "post",
      headers: {
        "Content-Type": "application/json ; charset=UTF-8"
      },
      body: JSON.stringify(ob)
    }).then(response => {
      console.log(response);
    })
      .catch(error => {
        console.log(error);
      });



  }

  // Track transaction status
  function watchTransaction(txHash: any) {
    const ethereum = MMSDK.getProvider()
    return new Promise((resolve, reject) => {
      const checkTransaction = async () => {
        try {

          if (ethereum) {
            const tx: any = await ethereum.request({
              method: "eth_getTransactionReceipt",
              params: [txHash],
            });

            if (tx) {
              if (tx.status === "0x1") {
                resolve(tx);
              } else {
                reject(new Error("Transaction failed"));
              }
            } else {
              setTimeout(checkTransaction, 2000); // Check every 2 seconds
            }
          }
        } catch (error: any) {
          reject(error);
        }
      };

      checkTransaction();
    });
  }


  async function sendTransaction(recipientAddress: any, amount: any) {

    const ethereum = MMSDK.getProvider()


    try {
      if (ethereum) {
        // Get current account
        const accounts: any = await ethereum.request({
          method: "eth_requestAccounts"
        });

        const from = accounts[0];

        // Convert ETH amount to wei (hex)
       // const value = `0x${(amount * 1e18).toString(16)}`;

        // Prepare transaction
        const transaction = {
          from,
          to: recipientAddress,
          value: "0x100",  //amount of eth to transfer
          gasPrice: "0x0", //ETH per unit of gas
          gasLimit: "0x24A22" //max number of gas units the tx is allowed to use
          // Gas fields are optional - MetaMask will estimate
        };

        // Send transaction
        const txHash = await ethereum.request({
          method: "eth_sendTransaction",
          params: [transaction],
        });


        return txHash;

      }
    } catch (error: any) {
      if (error.code === 4001) {
        throw new Error("Transaction rejected by user");
      }
      throw error;
    }
  }


  async function send() {
    const wallet = (document.getElementById("wallet") as HTMLInputElement).value
    const value = (document.getElementById("wallet") as HTMLInputElement).value
    const status = document.getElementById("status");

    try {

      if (status) {
        status.textContent = "Sending transaction...";
        const txHash = await sendTransaction(wallet, value);
        status.textContent = `Transaction sent: ${txHash}`;

        // Watch for confirmation
        status.textContent = "Waiting for confirmation...";
        await watchTransaction(txHash);
        status.textContent = "Transaction confirmed!";
      }

    } catch (error: any) {
      if (status) {
        status.textContent = `Error: ${error.message}`;
      }
    }

  }

  return (
    <>
      <h1>Besu</h1>
      <div className="card">
        <button onClick={connect}>
          Connect
        </button>
        <br />
        <br />
        <button onClick={receive}>
          Receive
        </button>
        <br />
        <br />
        <div>
          <div id="status"></div>
          &nbsp; &nbsp;
          <label>
            Wallet: <input id="wallet" name="wallet" />
          </label>
          &nbsp; &nbsp;
          <label>
            Valor: <input id="value" name="value" />
          </label>
          &nbsp; &nbsp;
          <button onClick={send}>
            Send
          </button>

        </div>
        <br />
        <br />

      </div>
    </>
  )
}

export default App
