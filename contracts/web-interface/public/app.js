const API_URL = 'http://localhost:3000/api';

// ============================================
// METAMASK CONNECTION
// ============================================

let userAccount = null;
let contractAddress = null;

async function connectMetaMask() {
    if (typeof window.ethereum === 'undefined') {
        showMessage('❌ MetaMask não instalado! Instale em https://metamask.io', 'error');
        return false;
    }

    try {
        // Solicitar contas
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        userAccount = accounts[0];

        // Verificar rede
        const chainId = await window.ethereum.request({ method: 'eth_chainId' });
        if (chainId !== '0x539') { // 1337 em hex
            showMessage('⚠️ Por favor, conecte à rede Besu Local (ChainID 1337)', 'error');

            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: '0x539' }],
                });
            } catch (switchError) {
                // Rede não existe, adicionar
                if (switchError.code === 4902) {
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: '0x539',
                            chainName: 'Besu Local',
                            rpcUrls: ['http://localhost:8545'],
                            nativeCurrency: {
                                name: 'Ether',
                                symbol: 'ETH',
                                decimals: 18
                            }
                        }]
                    });
                }
            }
        }

        updateWalletUI();
        showMessage(`✅ Conectado: ${formatAddress(userAccount)}`, 'success');
        return true;
    } catch (error) {
        console.error('Erro ao conectar MetaMask:', error);
        showMessage('❌ Erro ao conectar MetaMask', 'error');
        return false;
    }
}

function updateWalletUI() {
    const walletAddressEl = document.getElementById('wallet-address');
    const connectBtn = document.getElementById('connect-wallet');
    const submitBtn = document.getElementById('submit-csv-btn');

    if (userAccount) {
        walletAddressEl.textContent = `✅ ${formatAddress(userAccount)}`;
        walletAddressEl.title = userAccount;
        connectBtn.textContent = '✅ Conectado';
        if (submitBtn) submitBtn.disabled = false;
    } else {
        walletAddressEl.textContent = '❌ Nenhuma carteira conectada';
        connectBtn.textContent = '🦊 Conectar MetaMask';
        if (submitBtn) submitBtn.disabled = true;
    }
}

// Detectar mudanças de conta
if (typeof window.ethereum !== 'undefined') {
    // Verificar se já existe conexão ao carregar a página
    window.ethereum.request({ method: 'eth_accounts' })
        .then(accounts => {
            if (accounts.length > 0) {
                userAccount = accounts[0];
                updateWalletUI();
            }
        })
        .catch(err => console.error('Erro ao verificar contas:', err));

    window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length === 0) {
            userAccount = null;
            showMessage('⚠️ MetaMask desconectado', 'error');
        } else {
            userAccount = accounts[0];
            showMessage(`✅ Conta alterada: ${formatAddress(userAccount)}`, 'success');
        }
        updateWalletUI();

        // Recarregar marketplace e tokens para refletir a nova conta
        const sections = document.querySelectorAll('.section');
        sections.forEach(section => {
            const style = window.getComputedStyle(section);
            if (style.display !== 'none') {
                if (section.id === 'marketplace-section') {
                    loadMarketplace();
                } else if (section.id === 'my-tokens-section') {
                    loadMyTokens();
                }
            }
        });
    });

    window.ethereum.on('chainChanged', () => {
        window.location.reload();
    });
}

// ============================================
// UTILIDADES
// ============================================

function showMessage(message, type = 'info') {
    // Criar container de toasts se não existir
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    // Criar toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    // Ícone baseado no tipo
    const icons = {
        'success': '✅',
        'error': '❌',
        'info': 'ℹ️',
        'warning': '⚠️'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    toastContainer.appendChild(toast);

    // Animação de entrada
    setTimeout(() => toast.classList.add('toast-show'), 10);

    // Remover automaticamente após 5 segundos
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function showSection(sectionName) {
    document.querySelectorAll('.section').forEach(section => {
        section.style.display = 'none';
    });

    document.getElementById(`${sectionName}-section`).style.display = 'block';

    if (sectionName === 'marketplace') {
        loadMarketplace();
    } else if (sectionName === 'my-tokens' && userAccount) {
        loadMyTokens();
    }
}

function formatAddress(address) {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

// ============================================
// CARREGAR INFORMAÇÕES DO CONTRATO
// ============================================

async function loadContractInfo() {
    try {
        const response = await fetch(`${API_URL}/contract/info`);
        const result = await response.json();

        if (result.success) {
            const { data } = result;
            contractAddress = data.address; // Salvar endereço do contrato
            document.getElementById('contract-address').textContent = formatAddress(data.address);
            document.getElementById('contract-address').title = data.address;
            document.getElementById('contract-name').textContent = `${data.name} (${data.symbol})`;
            document.getElementById('total-supply').textContent = data.totalSupply;
        }
    } catch (error) {
        console.error('Erro ao carregar informações do contrato:', error);
    }
}

// ============================================
// MARKETPLACE
// ============================================

async function loadMarketplace() {
    const grid = document.getElementById('tokens-grid');
    grid.innerHTML = '<p class="loading">Carregando tokens...</p>';

    try {
        const response = await fetch(`${API_URL}/tokens`);
        const result = await response.json();

        if (result.success) {
            const tokens = result.data;

            if (tokens.length === 0) {
                grid.innerHTML = '<p class="info-message">Nenhum token encontrado</p>';
                return;
            }

            grid.innerHTML = '';
            tokens.forEach(token => {
                const tokenCard = createTokenCard(token);
                grid.appendChild(tokenCard);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar marketplace:', error);
        grid.innerHTML = '<p class="error-message">Erro ao carregar tokens</p>';
    }
}

function createTokenCard(token) {
    const card = document.createElement('div');
    card.className = `token-card ${token.isListed ? 'listed' : ''}`;
    card.onclick = () => showTokenDetails(token.tokenId);

    card.innerHTML = `
        <div class="token-header">
            <span class="token-id">Token #${token.tokenId}</span>
            <span class="token-badge ${token.isListed ? 'listed' : 'not-listed'}">
                ${token.isListed ? '🏷️ À Venda' : '🔒 Não Listado'}
            </span>
        </div>
        <div class="token-info">
            <div class="token-info-row">
                <span class="token-info-label">Valor E2:</span>
                <span class="token-info-value">R$ ${token.e2Value}</span>
            </div>
            <div class="token-info-row">
                <span class="token-info-label">Dono:</span>
                <span class="token-info-value">${formatAddress(token.owner)}</span>
            </div>
            ${token.isListed ? `
                <div class="token-info-row">
                    <span class="token-info-label">Preço:</span>
                    <span class="token-price">R$ ${token.priceBRL}</span>
                </div>
            ` : ''}
        </div>
        ${token.isListed && userAccount ? (
            token.owner.toLowerCase() === userAccount.toLowerCase() ? `
            <div class="token-actions">
                <button class="btn btn-success btn-small" onclick="event.stopPropagation(); transferToken('${token.tokenId}', '${token.priceBRL}')">
                    🔄 Transferir Token
                </button>
            </div>
            ` : `
            <div class="token-actions">
                <button class="btn btn-primary btn-small" onclick="event.stopPropagation(); requestPurchase('${token.tokenId}', '${token.priceBRL}', '${token.owner}')">
                    💰 Solicitar Compra
                </button>
            </div>
            `
        ) : ''}
    `;

    return card;
}

async function showTokenDetails(tokenId) {
    const modal = document.getElementById('token-modal');
    const modalBody = document.getElementById('modal-body');
    const modalTokenId = document.getElementById('modal-token-id');

    modalTokenId.textContent = tokenId;
    modalBody.innerHTML = '<p class="loading">Carregando detalhes...</p>';
    modal.style.display = 'block';

    try {
        const response = await fetch(`${API_URL}/tokens/${tokenId}`);
        const result = await response.json();

        if (result.success) {
            const { data } = result;
            modalBody.innerHTML = `
                <div class="modal-section">
                    <h3>📊 Informações Gerais</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="label">Dono</span>
                            <span class="value">${data.owner}</span>
                        </div>
                        <div class="info-item">
                            <span class="label">Status</span>
                            <span class="value">${data.isListed ? '🏷️ À Venda' : '🔒 Não Listado'}</span>
                        </div>
                        ${data.isListed ? `
                            <div class="info-item">
                                <span class="label">Preço</span>
                                <span class="value">R$ ${data.priceBRL}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="modal-section">
                    <h3>🧮 Cálculos E2</h3>
                    <div class="token-info">
                        <div class="token-info-row">
                            <span class="token-info-label">Tanque Gasolina:</span>
                            <span class="token-info-value">${data.calculations.tanqueGasoline}%</span>
                        </div>
                        <div class="token-info-row">
                            <span class="token-info-label">Valores Estrada:</span>
                            <span class="token-info-value">R$ ${data.calculations.dfEstrada}</span>
                        </div>
                        <div class="token-info-row">
                            <span class="token-info-label">Valores Cidade:</span>
                            <span class="token-info-value">R$ ${data.calculations.dfCidade}</span>
                        </div>
                        <div class="token-info-row">
                            <span class="token-info-label">Bônus Comportamento:</span>
                            <span class="token-info-value">${data.calculations.propBonus}</span>
                        </div>
                        <div class="token-info-row">
                            <span class="token-info-label">Distância Total:</span>
                            <span class="token-info-value">${data.calculations.totalDistance} km</span>
                        </div>
                        <div class="token-info-row">
                            <span class="token-info-label"><strong>E2 Final:</strong></span>
                            <span class="token-price">R$ ${data.calculations.e2Final}</span>
                        </div>
                    </div>
                </div>
                
                ${data.isListed && userAccount ? (
                    data.owner.toLowerCase() === userAccount.toLowerCase() ? `
                    <div class="modal-section">
                        <button class="btn btn-success" onclick="transferToken('${tokenId}', '${data.priceBRL}')">
                            🔄 Transferir Token - R$ ${data.priceBRL}
                        </button>
                    </div>
                    ` : `
                    <div class="modal-section">
                        <button class="btn btn-primary" onclick="requestPurchase('${tokenId}', '${data.priceBRL}', '${data.owner}')">
                            💰 Solicitar Compra - R$ ${data.priceBRL}
                        </button>
                    </div>
                    `
                ) : ''}
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar detalhes:', error);
        modalBody.innerHTML = '<p class="error-message">Erro ao carregar detalhes</p>';
    }
}

function closeModal() {
    document.getElementById('token-modal').style.display = 'none';
}

async function requestPurchase(tokenId, priceBRL, sellerAddress) {
    closeModal();

    const message = `
🛒 SOLICITAÇÃO DE COMPRA - NFT #${tokenId}

💰 Preço: R$ ${priceBRL}
👤 Vendedor: ${sellerAddress}

📋 PRÓXIMOS PASSOS:

1️⃣ Faça um PIX de R$ ${priceBRL} para o vendedor
2️⃣ Use a chave PIX do vendedor (contactar off-chain)
3️⃣ Após confirmar o pagamento, o vendedor transferirá o NFT

⚠️ IMPORTANTE: 
- Esta é uma negociação off-chain (fora da blockchain)
- Certifique-se de confiar no vendedor
- Guarde o comprovante do PIX
- Aguarde a transferência do NFT pelo vendedor
    `;

    alert(message);
    showMessage(`📋 Instruções de compra copiadas! Entre em contato com o vendedor.`, 'info');
}

async function transferToken(tokenId, priceBRL) {
    closeModal();

    const buyerAddress = prompt(
        `🔄 TRANSFERIR NFT #${tokenId}\n\n` +
        `💰 Preço: R$ ${priceBRL}\n\n` +
        `Digite o endereço da carteira do comprador:`
    );

    if (!buyerAddress) {
        showMessage('❌ Transferência cancelada', 'error');
        return;
    }

    // Validar endereço
    if (!buyerAddress.startsWith('0x') || buyerAddress.length !== 42) {
        showMessage('❌ Endereço inválido! Use formato: 0x...', 'error');
        return;
    }

    try {
        showMessage('⏳ Processando transferência...', 'info');

        // Verificar se o endereço do contrato foi carregado
        if (!contractAddress) {
            showMessage('❌ Endereço do contrato não disponível. Recarregue a página.', 'error');
            return;
        }

        // Codificar a chamada da função transferNFT(uint256 tokenId, address buyer)
        // Function selector: keccak256("transferNFT(uint256,address)") = 0x2c8be814...
        const functionSelector = '0x2c8be814';

        // Codificar parâmetros (tokenId e buyerAddress)
        const tokenIdHex = parseInt(tokenId).toString(16).padStart(64, '0');
        const buyerAddressHex = buyerAddress.substring(2).padStart(64, '0');

        const data = functionSelector + tokenIdHex + buyerAddressHex;

        // Enviar transação via MetaMask
        const transactionParameters = {
            from: userAccount,
            to: contractAddress, // Usar endereço dinâmico do backend
            data: data,
        };

        const txHash = await window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [transactionParameters],
        });

        showMessage('⏳ Aguardando confirmação da transação...', 'info');

        // Aguardar confirmação da transação
        let receipt = null;
        let attempts = 0;
        while (!receipt && attempts < 30) {
            try {
                receipt = await window.ethereum.request({
                    method: 'eth_getTransactionReceipt',
                    params: [txHash],
                });
            } catch (e) {
                // Ignorar erro
            }
            if (!receipt) {
                await new Promise(resolve => setTimeout(resolve, 1000));
                attempts++;
            }
        }

        if (receipt && receipt.status === '0x1') {
            showMessage(`✅ Token #${tokenId} transferido com sucesso! Recarregando página...`, 'success');

            // Recarregar a página após 2 segundos para garantir que os dados estejam atualizados
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else if (receipt && receipt.status === '0x0') {
            showMessage('❌ Transação falhou. Verifique se você é o dono e o token está à venda.', 'error');
        } else {
            showMessage('⏳ Transação enviada. Recarregue a página manualmente em alguns segundos.', 'info');
        }

    } catch (error) {
        console.error('Erro ao transferir token:', error);

        if (error.code === 4001) {
            showMessage('❌ Transferência rejeitada pelo usuário', 'error');
        } else {
            showMessage('❌ Erro ao transferir token: ' + error.message, 'error');
        }
    }
}

// ============================================
// CRIAR NFT
// ============================================

document.getElementById('create-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(e.target);
    const params = {
        highwayDistance: parseFloat(formData.get('highwayDistance')),
        cityDistance: parseFloat(formData.get('cityDistance')),
        ethanolPercent: parseFloat(formData.get('ethanolPercent')),
        roadGasoline: parseFloat(formData.get('roadGasoline')),
        roadEthanol: parseFloat(formData.get('roadEthanol')),
        cityGasoline: parseFloat(formData.get('cityGasoline')),
        cityEthanol: parseFloat(formData.get('cityEthanol')),
        behaviorCautious: parseFloat(formData.get('behaviorCautious')),
        behaviorNormal: parseFloat(formData.get('behaviorNormal')),
        behaviorAggressive: parseFloat(formData.get('behaviorAggressive'))
    };

    const recipient = formData.get('recipient');

    // Validar que comportamentos somam 100%
    const totalBehavior = params.behaviorCautious + params.behaviorNormal + params.behaviorAggressive;
    if (Math.abs(totalBehavior - 100) > 0.01) {
        showMessage('❌ A soma dos comportamentos deve ser 100%', 'error');
        return;
    }

    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Criando...';

    try {
        const response = await fetch(`${API_URL}/tokens/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ params, recipient })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(`✅ NFT #${result.data.tokenId} criado! E2: R$ ${result.data.e2Value}`, 'success');
            e.target.reset();
            loadContractInfo();
        } else {
            showMessage(`❌ Erro: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Erro ao criar NFT:', error);
        showMessage('❌ Erro ao criar NFT', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🎨 Criar NFT';
    }
});

// === UPLOAD CSV ===

document.getElementById('upload-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Verificar se MetaMask está conectado
    if (!userAccount) {
        showMessage('❌ Conecte sua carteira MetaMask primeiro!', 'error');
        return;
    }

    const fileInput = document.getElementById('csv-file');
    const progressDiv = document.getElementById('upload-progress');
    const resultsDiv = document.getElementById('upload-results');
    const submitBtn = e.target.querySelector('button[type="submit"]');

    if (!fileInput.files[0]) {
        showMessage('❌ Selecione um arquivo CSV', 'error');
        return;
    }

    // Obter rowIndex (se fornecido)
    const rowIndexInput = document.getElementById('row-index');
    const rowIndex = rowIndexInput.value.trim();

    // Preparar FormData
    const formData = new FormData();
    formData.append('csvFile', fileInput.files[0]);
    formData.append('recipient', userAccount); // Usar endereço do MetaMask
    if (rowIndex !== '') {
        formData.append('rowIndex', rowIndex);
        console.log('📝 Enviando rowIndex:', rowIndex);
    } else {
        console.log('📝 Nenhum rowIndex fornecido - processará todas as linhas');
    }

    // Mostrar progresso
    progressDiv.style.display = 'block';
    resultsDiv.style.display = 'none';
    submitBtn.disabled = true;

    document.getElementById('progress-text').textContent = 'Enviando arquivo...';
    document.getElementById('progress-fill').style.width = '30%';

    try {
        const response = await fetch(`${API_URL}/upload-csv`, {
            method: 'POST',
            body: formData
        });

        document.getElementById('progress-fill').style.width = '60%';
        document.getElementById('progress-text').textContent = 'Processando dados...';

        const result = await response.json();

        document.getElementById('progress-fill').style.width = '100%';
        document.getElementById('progress-text').textContent = 'Concluído!';

        if (result.success) {
            setTimeout(() => {
                progressDiv.style.display = 'none';
                displayUploadResults(result.data);
                showMessage(`✅ ${result.data.successful} NFTs criados com sucesso!`, 'success');
                e.target.reset();
                loadContractInfo(); // Atualizar info do contrato
            }, 1000);
        } else {
            showMessage(`❌ Erro: ${result.error}`, 'error');
            progressDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('Erro no upload:', error);
        showMessage('❌ Erro ao processar CSV', 'error');
        progressDiv.style.display = 'none';
    } finally {
        submitBtn.disabled = false;
    }
});

function displayUploadResults(data) {
    const resultsDiv = document.getElementById('upload-results');

    let html = `
        <h3>📊 Resultados do Processamento</h3>
        <div class="result-summary">
            <div class="result-stat">
                <div class="number">${data.total}</div>
                <div class="label">Total de Registros</div>
            </div>
            <div class="result-stat success">
                <div class="number">${data.successful}</div>
                <div class="label">✅ Sucesso</div>
            </div>
            <div class="result-stat error">
                <div class="number">${data.failed}</div>
                <div class="label">❌ Erros</div>
            </div>
        </div>
    `;

    if (data.results.length > 0) {
        html += `
            <div class="results-table">
                <h4>NFTs Criados</h4>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Token ID</th>
                            <th>VIN</th>
                            <th>Modelo</th>
                            <th>E2 (R$)</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.results.map(r => `
                            <tr>
                                <td>${r.index}</td>
                                <td><strong>#${r.tokenId}</strong></td>
                                <td>${r.vin}</td>
                                <td>${r.model}</td>
                                <td>R$ ${r.e2Value}</td>
                                <td><span class="status-badge success">✅ Criado</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    if (data.errors.length > 0) {
        html += `
            <div class="results-table" style="margin-top: 2rem;">
                <h4>Erros</h4>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>VIN</th>
                            <th>Erro</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.errors.map(e => `
                            <tr>
                                <td>${e.index}</td>
                                <td>${e.vin || 'N/A'}</td>
                                <td><span class="status-badge error">${e.error}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
}

// === MEUS TOKENS ===

async function loadMyTokens() {
    // Verificar se MetaMask está conectado
    if (!userAccount) {
        showMessage('❌ Conecte sua carteira MetaMask primeiro!', 'error');
        return;
    }

    const grid = document.getElementById('my-tokens-grid');
    grid.innerHTML = '<p class="loading">Carregando seus tokens...</p>';

    try {
        const response = await fetch(`${API_URL}/tokens/owner/${userAccount}`);
        const result = await response.json();

        if (result.success) {
            const { data } = result;

            if (data.tokens.length === 0) {
                grid.innerHTML = '<p class="info-message">Você não possui tokens</p>';
                return;
            }

            grid.innerHTML = '';
            data.tokens.forEach(token => {
                const tokenCard = createMyTokenCard(token, userAccount);
                grid.appendChild(tokenCard);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar tokens:', error);
        grid.innerHTML = '<p class="error-message">Erro ao carregar tokens</p>';
    }
}

function createMyTokenCard(token, ownerAddress) {
    const card = document.createElement('div');
    card.className = `token-card ${token.isListed ? 'listed' : ''}`;

    card.innerHTML = `
        <div class="token-header">
            <span class="token-id">Token #${token.tokenId}</span>
            <span class="token-badge ${token.isListed ? 'listed' : 'not-listed'}">
                ${token.isListed ? '🏷️ À Venda' : '🔒 Não Listado'}
            </span>
        </div>
        <div class="token-info">
            <div class="token-info-row">
                <span class="token-info-label">Valor E2:</span>
                <span class="token-info-value">R$ ${token.e2Value}</span>
            </div>
            <div class="token-info-row">
                <span class="token-info-label">Distância:</span>
                <span class="token-info-value">${token.totalDistance} km</span>
            </div>
            ${token.isListed ? `
                <div class="token-info-row">
                    <span class="token-info-label">Preço:</span>
                    <span class="token-price">R$ ${token.priceBRL}</span>
                </div>
            ` : ''}
        </div>
        <div class="token-actions">
            ${!token.isListed ? `
                <button class="btn btn-primary btn-small" onclick="listToken('${token.tokenId}')">
                    🏷️ Listar
                </button>
            ` : `
                <button class="btn btn-danger btn-small" onclick="delistToken('${token.tokenId}')">
                    ❌ Remover
                </button>
            `}
            <button class="btn btn-secondary btn-small" onclick="showTokenDetails('${token.tokenId}')">
                👁️ Detalhes
            </button>
        </div>
    `;

    return card;
}

async function listToken(tokenId) {
    const price = prompt('Digite o preço em BRL:');
    if (!price || isNaN(price) || parseFloat(price) <= 0) {
        showMessage('❌ Preço inválido', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/tokens/${tokenId}/list`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ priceBRL: parseFloat(price) })
        });

        const result = await response.json();

        if (result.success) {
            showMessage('✅ Token listado com sucesso!', 'success');
            loadMyTokens();
        } else {
            showMessage(`❌ Erro: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Erro ao listar token:', error);
        showMessage('❌ Erro ao listar token', 'error');
    }
}

async function delistToken(tokenId) {
    if (!confirm('Deseja remover este token da venda?')) return;

    try {
        const response = await fetch(`${API_URL}/tokens/${tokenId}/delist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.success) {
            showMessage('✅ Token removido da venda!', 'success');
            loadMyTokens();
        } else {
            showMessage(`❌ Erro: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Erro ao remover token:', error);
        showMessage('❌ Erro ao remover token', 'error');
    }
}

// ============================================
// INICIALIZAÇÃO
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadContractInfo();
    loadMarketplace();

    // Fechar modal ao clicar fora
    window.onclick = (event) => {
        const modal = document.getElementById('token-modal');
        if (event.target === modal) {
            closeModal();
        }
    };
});
