const express = require('express');
const { ethers } = require('ethers');
const cors = require('cors');
const path = require('path');
const multer = require('multer');
const csv = require('csv-parser');
const fs = require('fs');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middlewares
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configurar multer para upload de arquivos
const upload = multer({ dest: 'uploads/' });

// Criar diretório de uploads se não existir
if (!fs.existsSync('uploads')) {
    fs.mkdirSync('uploads');
}

// Configuração da conexão com o blockchain
// Desabilitar ENS para redes privadas
const provider = new ethers.JsonRpcProvider(
    process.env.RPC_URL || 'http://localhost:8545',
    { chainId: 1337, name: 'besu-local', ensAddress: null }
);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

// ABI do contrato (apenas funções necessárias)
const CONTRACT_ABI = [
    "function name() view returns (string)",
    "function symbol() view returns (string)",
    "function totalSupply() view returns (uint256)",
    "function balanceOf(address owner) view returns (uint256)",
    "function ownerOf(uint256 tokenId) view returns (address)",
    "function tokenOfOwnerByIndex(address owner, uint256 index) view returns (uint256)",
    "function getCalculationDetails(uint256 tokenId) view returns (tuple(uint256 tanqueGasoline, uint256 dtEstradaGasolina, uint256 dtEstradaEtanol, uint256 dfEstrada, uint256 dtCidadeGasolina, uint256 dtCidadeEtanol, uint256 dfCidade, uint256 propBonus, uint256 e2Final, uint256 totalDistance))",
    "function getAllTokensWithPrices() view returns (uint256[] tokenIds, uint256[] e2Values, uint256[] pricesBRL, address[] owners, bool[] listed)",
    "function isListed(uint256 tokenId) view returns (bool)",
    "function listingPriceBRL(uint256 tokenId) view returns (uint256)",
    "function listToken(uint256 tokenId, uint256 priceBRL)",
    "function delistToken(uint256 tokenId)",
    "function transferNFT(uint256 tokenId, address buyer)",
    "function authorized(address user) view returns (bool)",
    "function owner() view returns (address)",
    "function getContractBalance() view returns (uint256)",
    "function calculateE2AndTokenize(tuple(uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256) params, address recipient) returns (uint256 tokenId, uint256 e2Value)",
    "event E2Calculated(address indexed user, uint256 indexed tokenId, uint256 e2Value, uint256 totalDistance, uint256 timestamp)",
    "event TokenListed(uint256 indexed tokenId, address indexed seller, uint256 priceInBRL)",
    "event TokenTransferred(uint256 indexed tokenId, address indexed from, address indexed to, uint256 priceBRL)"
];

const contract = new ethers.Contract(process.env.CONTRACT_ADDRESS, CONTRACT_ABI, wallet);

// Testar conectividade no startup
async function testConnection() {
    try {
        console.log('🔍 Testando conexão com blockchain...');
        const network = await provider.getNetwork();
        console.log('✅ Conectado à rede:', network.chainId.toString());

        console.log('🔍 Testando contrato...');
        const code = await provider.getCode(process.env.CONTRACT_ADDRESS);
        if (code === '0x') {
            console.log('⚠️  AVISO: Nenhum código encontrado no endereço do contrato!');
            console.log('   Verifique se o contrato foi deployado em:', process.env.CONTRACT_ADDRESS);
        } else {
            console.log('✅ Contrato encontrado no endereço:', process.env.CONTRACT_ADDRESS);
        }

        // Testar uma chamada simples
        try {
            const name = await contract.name();
            console.log('✅ Contrato acessível! Nome:', name);
        } catch (err) {
            console.log('⚠️  Erro ao chamar função do contrato:', err.message);
        }
    } catch (error) {
        console.error('❌ Erro na conexão:', error.message);
    }
}

// ============================================
// ROTAS DA API
// ============================================

// Informações básicas do contrato
app.get('/api/contract/info', async (req, res) => {
    try {
        console.log('📊 Requisição: /api/contract/info');

        const [name, symbol, totalSupply, owner, balance] = await Promise.all([
            contract.name(),
            contract.symbol(),
            contract.totalSupply(),
            contract.owner(),
            contract.getContractBalance()
        ]);

        res.json({
            success: true,
            data: {
                address: process.env.CONTRACT_ADDRESS,
                name,
                symbol,
                totalSupply: totalSupply.toString(),
                owner,
                balance: ethers.formatEther(balance)
            }
        });
    } catch (error) {
        console.error('❌ Erro em /api/contract/info:', error.message);
        console.error('Stack:', error.stack);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Listar todos os tokens
app.get('/api/tokens', async (req, res) => {
    try {
        const result = await contract.getAllTokensWithPrices();

        const tokens = [];
        for (let i = 0; i < result.tokenIds.length; i++) {
            tokens.push({
                tokenId: result.tokenIds[i].toString(),
                e2Value: (Number(result.e2Values[i]) / 1e6).toFixed(6),
                priceBRL: result.listed[i] ? (Number(result.pricesBRL[i]) / 1e6).toFixed(6) : null,
                owner: result.owners[i],
                isListed: result.listed[i]
            });
        }

        res.json({ success: true, data: tokens });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Detalhes de um token específico
app.get('/api/tokens/:tokenId', async (req, res) => {
    try {
        const { tokenId } = req.params;

        const [owner, details, isListed, priceBRL] = await Promise.all([
            contract.ownerOf(tokenId),
            contract.getCalculationDetails(tokenId),
            contract.isListed(tokenId),
            contract.listingPriceBRL(tokenId)
        ]);

        res.json({
            success: true,
            data: {
                tokenId,
                owner,
                isListed,
                priceBRL: isListed ? (Number(priceBRL) / 1e6).toFixed(2) : null,
                calculations: {
                    tanqueGasoline: (Number(details.tanqueGasoline) / 1e6).toFixed(2),
                    dfEstrada: (Number(details.dfEstrada) / 1e6).toFixed(6),
                    dfCidade: (Number(details.dfCidade) / 1e6).toFixed(6),
                    propBonus: (Number(details.propBonus) / 1e6).toFixed(6),
                    e2Final: (Number(details.e2Final) / 1e6).toFixed(6),
                    totalDistance: (Number(details.totalDistance) / 1e6).toFixed(2)
                }
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Tokens de um endereço específico
app.get('/api/tokens/owner/:address', async (req, res) => {
    try {
        const { address } = req.params;
        const balance = await contract.balanceOf(address);

        const tokens = [];
        for (let i = 0; i < balance; i++) {
            const tokenId = await contract.tokenOfOwnerByIndex(address, i);
            const details = await contract.getCalculationDetails(tokenId);
            const isListed = await contract.isListed(tokenId);
            const priceBRL = await contract.listingPriceBRL(tokenId);

            tokens.push({
                tokenId: tokenId.toString(),
                e2Value: (Number(details.e2Final) / 1e6).toFixed(6),
                totalDistance: (Number(details.totalDistance) / 1e6).toFixed(2),
                isListed,
                priceBRL: isListed ? (Number(priceBRL) / 1e6).toFixed(2) : null
            });
        }

        res.json({ success: true, data: { address, balance: balance.toString(), tokens } });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Listar token para venda
app.post('/api/tokens/:tokenId/list', async (req, res) => {
    try {
        const { tokenId } = req.params;
        const { priceBRL } = req.body;

        if (!priceBRL || priceBRL <= 0) {
            return res.status(400).json({ success: false, error: 'Preço inválido' });
        }

        // Converter para escala 1e6
        const priceBRLScaled = Math.floor(priceBRL * 1e6);

        const tx = await contract.listToken(tokenId, priceBRLScaled);
        const receipt = await tx.wait();

        res.json({
            success: true,
            data: {
                tokenId,
                priceBRL,
                transactionHash: receipt.hash
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Remover token da venda
app.post('/api/tokens/:tokenId/delist', async (req, res) => {
    try {
        const { tokenId } = req.params;

        const tx = await contract.delistToken(tokenId);
        const receipt = await tx.wait();

        res.json({
            success: true,
            data: {
                tokenId,
                transactionHash: receipt.hash
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Transferir NFT após pagamento off-chain
app.post('/api/tokens/:tokenId/transfer', async (req, res) => {
    try {
        const { tokenId } = req.params;
        const { buyerAddress, sellerPrivateKey } = req.body;

        if (!buyerAddress) {
            return res.status(400).json({ success: false, error: 'Endereço do comprador necessário' });
        }

        if (!sellerPrivateKey) {
            return res.status(400).json({ success: false, error: 'Chave privada do vendedor necessária' });
        }

        // Validar endereço do comprador
        let buyer;
        try {
            buyer = ethers.getAddress(buyerAddress.trim());
        } catch (err) {
            return res.status(400).json({ success: false, error: 'Endereço do comprador inválido' });
        }

        // Criar wallet do vendedor
        const sellerWallet = new ethers.Wallet(sellerPrivateKey, provider);
        const contractAsSeller = contract.connect(sellerWallet);

        const tx = await contractAsSeller.transferNFT(tokenId, buyer);
        const receipt = await tx.wait();

        const priceBRL = await contract.listingPriceBRL(tokenId);

        res.json({
            success: true,
            data: {
                tokenId,
                priceBRL: (Number(priceBRL) / 1e6).toFixed(6),
                buyer,
                seller: sellerWallet.address,
                transactionHash: receipt.hash
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});
// Verificar se endereço está autorizado
app.get('/api/auth/check/:address', async (req, res) => {
    try {
        const { address } = req.params;
        const isAuthorized = await contract.authorized(address);

        res.json({ success: true, data: { address, isAuthorized } });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// === UPLOAD E PROCESSAMENTO DE CSV ===
app.post('/api/upload-csv', upload.single('csvFile'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, error: 'Nenhum arquivo enviado' });
    }

    const { recipient, rowIndex } = req.body;

    console.log('📥 Dados recebidos:', { recipient, rowIndex, type_rowIndex: typeof rowIndex });

    if (!recipient) {
        return res.status(400).json({ success: false, error: 'Endereço destinatário obrigatório' });
    }

    // Validar e normalizar o endereço (evitar resolução ENS)
    // Aceita tanto endereço quanto chave privada
    let recipientAddress;
    try {
        const recipientTrimmed = recipient.trim();

        // Verificar se é uma chave privada (começa com 0x e tem 66 caracteres)
        if (recipientTrimmed.startsWith('0x') && recipientTrimmed.length === 66) {
            // Derivar endereço da chave privada
            const tempWallet = new ethers.Wallet(recipientTrimmed);
            recipientAddress = tempWallet.address;
            console.log('🔑 Chave privada detectada, endereço derivado:', recipientAddress);
        } else {
            // É um endereço, apenas validar
            recipientAddress = ethers.getAddress(recipientTrimmed);
            console.log('✅ Endereço validado:', recipientAddress);
        }
    } catch (error) {
        return res.status(400).json({
            success: false,
            error: `Endereço ou chave privada inválida: ${error.message}`
        });
    }

    const results = [];
    const errors = [];

    // Arrays de eficiências (do código Python original)
    const city_gasoline_array = [10.3, 10.3, 10.3, 10.3, 12.15, 12.15, 12.15, 12.15, 12.6, 12.6, 12.6, 12.6, 11.8, 12.83, 12.83, 12.83, 12.83, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 11.6, 12.0, 12.0];
    const road_gasoline_array = [11.3, 11.3, 11.3, 11.3, 13.65, 13.65, 13.65, 13.65, 13.9, 13.9, 13.9, 13.9, 13.3, 14.44, 14.44, 14.44, 14.44, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.1, 14.4, 14.4];
    const city_ethanol_array = [0, 0, 0, 0, 8.2, 8.2, 8.2, 8.2, 8.9, 8.9, 8.9, 8.9, 8.1, 9.11, 9.11, 9.11, 9.11, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8.3, 8.3];
    const road_ethanol_array = [0, 0, 0, 0, 9.5, 9.5, 9.5, 9.5, 9.8, 9.8, 9.8, 9.8, 9.2, 10.26, 10.26, 10.26, 10.26, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 9.8, 10.0, 10.0];

    try {
        // Ler CSV
        const csvData = [];
        await new Promise((resolve, reject) => {
            fs.createReadStream(req.file.path)
                .pipe(csv())
                .on('data', (row) => csvData.push(row))
                .on('end', resolve)
                .on('error', reject);
        });

        console.log(`📊 CSV carregado: ${csvData.length} registros`);

        // Determinar quais linhas processar
        let linesToProcess = [];
        const rowIndexStr = String(rowIndex).trim();

        if (rowIndexStr && rowIndexStr !== '' && rowIndexStr !== 'undefined' && rowIndexStr !== 'null') {
            const idx = parseInt(rowIndexStr);
            if (!isNaN(idx) && idx >= 0 && idx < csvData.length) {
                linesToProcess = [idx];
                console.log(`📝 Processando apenas linha ${idx + 1} (índice ${idx})`);
            } else {
                fs.unlinkSync(req.file.path);
                return res.status(400).json({
                    success: false,
                    error: `Índice inválido: ${rowIndexStr}. CSV tem ${csvData.length} linhas (índices 0 a ${csvData.length - 1})`
                });
            }
        } else {
            // Processar todas as linhas
            linesToProcess = Array.from({ length: csvData.length }, (_, i) => i);
            console.log(`📝 Processando todas as ${csvData.length} linhas (rowIndex vazio ou não fornecido)`);
        }

        // Processar linhas selecionadas
        for (const idx of linesToProcess) {
            const row = csvData[idx];

            try {
                // Extrair dados do CSV
                const ethanol_percent = parseFloat(row['ethanol (%)'] || 0);
                const highway_distance = parseFloat(row['highway (distance)'] || 0);
                const city_distance = parseFloat(row['city (distance)'] || 0);
                const behavior_cautious = parseFloat(row['behavior_cautious (%)'] || 0);
                const behavior_normal = parseFloat(row['behavior_normal (%)'] || 0);
                const behavior_aggressive = parseFloat(row['behavior_aggressive (%)'] || 0);

                // Aplicar eficiências do array
                let city_gasoline = idx < city_gasoline_array.length ? city_gasoline_array[idx] : 10.3;
                let road_gasoline = idx < road_gasoline_array.length ? road_gasoline_array[idx] : 11.3;
                let city_ethanol = idx < city_ethanol_array.length ? city_ethanol_array[idx] : 8.0;
                let road_ethanol = idx < road_ethanol_array.length ? road_ethanol_array[idx] : 9.5;

                // Valores padrão se for zero
                if (city_gasoline === 0) city_gasoline = 10.3;
                if (road_gasoline === 0) road_gasoline = 11.3;
                if (city_ethanol === 0) city_ethanol = 8.0;
                if (road_ethanol === 0) road_ethanol = 9.5;

                // Criar parâmetros para o contrato (escala 1e6)
                const scaledParams = {
                    highwayDistance: Math.floor(highway_distance * 1e6),
                    cityDistance: Math.floor(city_distance * 1e6),
                    ethanolPercent: Math.floor(ethanol_percent * 1e6),
                    roadGasoline: Math.floor(road_gasoline * 1e6),
                    roadEthanol: Math.floor(road_ethanol * 1e6),
                    cityGasoline: Math.floor(city_gasoline * 1e6),
                    cityEthanol: Math.floor(city_ethanol * 1e6),
                    precoGasolina: 0,
                    precoEtanol: 0,
                    behaviorCautious: Math.floor(behavior_cautious * 1e6),
                    behaviorNormal: Math.floor(behavior_normal * 1e6),
                    behaviorAggressive: Math.floor(behavior_aggressive * 1e6)
                };

                // Enviar transação (usar endereço validado)
                const tx = await contract.calculateE2AndTokenize(
                    Object.values(scaledParams),
                    recipientAddress
                );
                const receipt = await tx.wait();

                // Extrair tokenId do evento
                const event = receipt.logs.find(log => {
                    try {
                        return contract.interface.parseLog(log).name === 'E2Calculated';
                    } catch (e) {
                        return false;
                    }
                });

                if (event) {
                    const parsedEvent = contract.interface.parseLog(event);
                    const tokenId = parsedEvent.args.tokenId.toString();
                    const e2Value = (Number(parsedEvent.args.e2Value) / 1e6).toFixed(6);

                    results.push({
                        index: idx + 1,
                        tokenId,
                        e2Value,
                        vin: row['VIN'],
                        model: row['model'],
                        brand: row['brand'],
                        totalDistance: (highway_distance + city_distance).toFixed(2),
                        transactionHash: receipt.hash
                    });

                    console.log(`✅ NFT criado: Linha ${idx + 1}, Token #${tokenId}, E2=R$ ${e2Value}`);
                }

            } catch (error) {
                console.error(`❌ Erro na linha ${idx + 1}:`, error.message);
                errors.push({
                    index: idx + 1,
                    vin: row['VIN'],
                    error: error.message
                });
            }
        }

        // Limpar arquivo temporário
        fs.unlinkSync(req.file.path);

        res.json({
            success: true,
            data: {
                total: csvData.length,
                processed: linesToProcess.length,
                successful: results.length,
                failed: errors.length,
                results,
                errors
            }
        });

    } catch (error) {
        console.error('❌ Erro ao processar CSV:', error);
        // Limpar arquivo temporário em caso de erro
        if (fs.existsSync(req.file.path)) {
            fs.unlinkSync(req.file.path);
        }
        res.status(500).json({ success: false, error: error.message });
    }
});

// Rota principal - servir o site
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Iniciar servidor
app.listen(PORT, async () => {
    console.log(`🚀 Servidor rodando em http://localhost:${PORT}`);
    console.log(`📄 Contrato: ${process.env.CONTRACT_ADDRESS}`);
    console.log(`🔗 RPC: ${process.env.RPC_URL}`);
    console.log('');

    // Testar conexão após iniciar servidor
    await testConnection();
});
