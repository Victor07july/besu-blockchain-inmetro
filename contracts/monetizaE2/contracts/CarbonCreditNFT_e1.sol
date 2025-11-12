// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonCreditNFT_FabricEquivalent
 * @dev Contrato Solidity equivalente ao chaincode Fabric para tokenização de créditos de carbono
 * 
 * FUNCIONAMENTO:
 * 1. Calcula CO2 meta baseado em dados de combustível e distâncias
 * 2. Compara com CO2 real para determinar economia (E1)
 * 3. Converte economia em valor monetário (E2) usando cotações
 * 4. Cria NFT com recompensa em wei proporcional à economia
 * 
 * AUTORIZAÇÃO:
 * - Apenas endereços autorizados (equivalente ao INMETROMSP) podem tokenizar
 */
contract CarbonCreditNFT_FabricEquivalent is ERC721, ReentrancyGuard, Ownable {
    
    // === ESTADO DO CONTRATO ===
    struct ContractState {
        uint256 nextTokenId;
        uint256 carbonPriceEUR;    // Preço carbono em EUR (6 decimais)
        uint256 cotacaoEuroBRL;    // Cotação EUR/BRL (6 decimais)
        bool initialized;
    }
    
    // === DADOS DE CARBONIZAÇÃO ===
    struct DadosCarbonizacao {
        string tokenId;
        string vehicleId;
        string condutor;
        uint256 highwayDistance;   // km * 1e6
        uint256 cityDistance;      // km * 1e6
        uint256 ethanolPercent;    // % * 1e6
        uint256 co2EtanolOriginal; // g * 1e6
        uint256 roadGasoline;      // km/L * 1e6
        uint256 roadEthanol;       // km/L * 1e6
        uint256 cityGasoline;      // km/L * 1e6
        uint256 cityEthanol;       // km/L * 1e6
        uint256 tanqueGasoline;    // % * 1e6
        uint256 realPrice;         // BRL * 1e6
        uint256 metaCO2;          // g * 1e6
        uint256 diff;             // economia g * 1e6
        uint256 tokenValue;       // valor E2 * 1e6
        uint256 recompensaEmWei;  // wei
        string timestamp;
    }
    
    // === STATUS DE RECOMPENSA ===
    struct StatusRecompensa {
        string condutor;
        string tokenId;
        bool sacada;
        uint256 valor;  // wei
    }
    
    // === ESTADO ===
    ContractState public contractState;
    mapping(uint256 => DadosCarbonizacao) public dadosCarbonizacao;
    mapping(uint256 => StatusRecompensa) public statusRecompensa;
    mapping(address => bool) public authorized; // Equivalente ao INMETROMSP
    
    // === EVENTOS ===
    event CarbonTokenized(
        uint256 indexed tokenId,
        address indexed condutor,
        string vehicleId,
        uint256 co2Economy,
        uint256 metaCO2,
        uint256 originalCO2,
        uint256 recompensaWei
    );
    
    event RecompensaWithdrawn(
        uint256 indexed tokenId,
        address indexed condutor,
        uint256 valor
    );
    
    event ContractInitialized(
        uint256 carbonPriceEUR,
        uint256 cotacaoEuroBRL
    );
    
    event AuthorizedChanged(address indexed account, bool authorized);
    
    // === MODIFICADORES ===
    modifier onlyAuthorized() {
        require(authorized[msg.sender], "Client is not authorized to tokenize carbon credits");
        _;
    }
    
    modifier contractInitialized() {
        require(contractState.initialized, "Contract not initialized");
        _;
    }
    
    // === CONSTRUTOR ===
    constructor() ERC721("CarbonCreditNFT", "CCNFT") Ownable(_msgSender()) {
        contractState.nextTokenId = 1;
        contractState.initialized = false;
    }
    
    // === INICIALIZAÇÃO ===
    function initializeContract(
        uint256 _carbonPriceEUR,
        uint256 _cotacaoEuroBRL
    ) external onlyOwner {
        require(!contractState.initialized, "Contract already initialized");
        require(_carbonPriceEUR > 0, "Invalid carbon price");
        require(_cotacaoEuroBRL > 0, "Invalid EUR/BRL rate");
        
        contractState.carbonPriceEUR = _carbonPriceEUR;
        contractState.cotacaoEuroBRL = _cotacaoEuroBRL;
        contractState.initialized = true;
        
        emit ContractInitialized(_carbonPriceEUR, _cotacaoEuroBRL);
    }
    
    // === AUTORIZAÇÃO ===
    function setAuthorized(address account, bool _authorized) external onlyOwner {
        authorized[account] = _authorized;
        emit AuthorizedChanged(account, _authorized);
    }
    
    // === FUNÇÃO PRINCIPAL: CALCULAR E1 E TOKENIZAR ===
    function calculateE1AndTokenize(
        string memory vehicleId,
        address condutor,
        uint256 highwayDistance,    // km * 1e6
        uint256 cityDistance,       // km * 1e6
        uint256 ethanolPercent,     // % * 1e6
        uint256 co2EtanolOriginal,  // g * 1e6
        uint256 roadGasoline,       // km/L * 1e6
        uint256 roadEthanol,        // km/L * 1e6
        uint256 cityGasoline,       // km/L * 1e6
        uint256 cityEthanol,        // km/L * 1e6
        uint256 tanqueGasoline,     // % * 1e6
        string memory timestamp
    ) external onlyAuthorized contractInitialized returns (uint256 tokenId) {
        
        // Calcular CO2 Meta
        uint256 metaCO2 = _calculateMetaCO2(
            highwayDistance,
            cityDistance,
            ethanolPercent,
            roadGasoline,
            roadEthanol,
            cityGasoline,
            cityEthanol,
            tanqueGasoline
        );
        
        // Calcular diferença (E1) = META CO2 - EMISSÃO REAL
        require(metaCO2 > co2EtanolOriginal, "No carbon savings detected");
        uint256 diff = metaCO2 - co2EtanolOriginal;
        
        // Calcular valor monetário em BRL (E2)
        uint256 realPrice = (contractState.carbonPriceEUR * contractState.cotacaoEuroBRL) / 1e6;
        uint256 tokenValue = (diff * realPrice) / 1e12; // Converter de gramas para toneladas
        
        // Calcular recompensa em wei (assumindo 1 BRL = 1e18 wei para simplificação)
        uint256 recompensaEmWei = tokenValue * 1e12; // Ajustar conversão conforme necessário
        
        // Gerar token ID
        tokenId = contractState.nextTokenId;
        contractState.nextTokenId++;
        
        // Verificar se token já existe
        require(_ownerOf(tokenId) == address(0), "Token already minted");
        
        // Criar NFT
        _mint(condutor, tokenId);
        
        // Salvar dados de carbonização
        dadosCarbonizacao[tokenId] = DadosCarbonizacao({
            tokenId: _toString(tokenId),
            vehicleId: vehicleId,
            condutor: _addressToString(condutor),
            highwayDistance: highwayDistance,
            cityDistance: cityDistance,
            ethanolPercent: ethanolPercent,
            co2EtanolOriginal: co2EtanolOriginal,
            roadGasoline: roadGasoline,
            roadEthanol: roadEthanol,
            cityGasoline: cityGasoline,
            cityEthanol: cityEthanol,
            tanqueGasoline: tanqueGasoline,
            realPrice: realPrice,
            metaCO2: metaCO2,
            diff: diff,
            tokenValue: tokenValue,
            recompensaEmWei: recompensaEmWei,
            timestamp: timestamp
        });
        
        // Salvar status da recompensa
        statusRecompensa[tokenId] = StatusRecompensa({
            condutor: _addressToString(condutor),
            tokenId: _toString(tokenId),
            sacada: false,
            valor: recompensaEmWei
        });
        
        emit CarbonTokenized(
            tokenId,
            condutor,
            vehicleId,
            diff,
            metaCO2,
            co2EtanolOriginal,
            recompensaEmWei
        );
    }
    
    // === CÁLCULO DE CO2 META ===
    function _calculateMetaCO2(
        uint256 hwDistance,
        uint256 ctDistance,
        uint256 ethPercent,
        uint256 roadGas,
        uint256 roadEth,
        uint256 cityGas,
        uint256 cityEth,
        uint256 tanqueGas
    ) internal pure returns (uint256 metaCO2) {
        
        // Constantes de emissão (ajustadas para 6 decimais)
        uint256 FATOR_GASOLINA = 1720000; // 1.720 * 1e6
        uint256 FATOR_ETANOL = 1510000;   // 1.510 * 1e6
        uint256 MULTIPLICADOR = 1000;      // 1000
        
        // Evitar divisão por zero
        if (roadGas == 0) roadGas = 1;
        if (roadEth == 0) roadEth = 1;
        if (cityGas == 0) cityGas = 1;
        if (cityEth == 0) cityEth = 1;
        
        // PARTE 1 - Highway calculations
        // hwDistance * ((1/roadGas) * (tanqueGas/100) * 1.720) * 1000
        uint256 parte1_1 = (hwDistance * tanqueGas * FATOR_GASOLINA * MULTIPLICADOR) / 
                           (roadGas * 100 * 1e6);
        
        // hwDistance * ((1/roadEth) * (ethPercent/100) * 1.510) * 1000
        uint256 parte1_2 = (hwDistance * ethPercent * FATOR_ETANOL * MULTIPLICADOR) / 
                           (roadEth * 100 * 1e6);
        
        uint256 parte1 = parte1_1 + parte1_2;
        
        // PARTE 2 - City calculations
        uint256 parte2_1 = (ctDistance * tanqueGas * FATOR_GASOLINA * MULTIPLICADOR) / 
                           (cityGas * 100 * 1e6);
        
        uint256 parte2_2 = (ctDistance * ethPercent * FATOR_ETANOL * MULTIPLICADOR) / 
                           (cityEth * 100 * 1e6);
        
        uint256 parte2 = parte2_1 + parte2_2;
        
        metaCO2 = parte1 + parte2;
    }
    
    // === SAQUE DE RECOMPENSA ===
    function sacarRecompensa(uint256 tokenId) external nonReentrant {
        require(ownerOf(tokenId) == msg.sender, "Not authorized");
        require(!statusRecompensa[tokenId].sacada, "Reward already withdrawn");
        
        uint256 valor = statusRecompensa[tokenId].valor;
        require(valor > 0, "No reward available");
        require(address(this).balance >= valor, "Insufficient contract balance");
        
        statusRecompensa[tokenId].sacada = true;
        
        (bool success, ) = msg.sender.call{value: valor}("");
        require(success, "Transfer failed");
        
        emit RecompensaWithdrawn(tokenId, msg.sender, valor);
    }
    
    // === FUNÇÕES DE CONSULTA ===
    function getDadosCarbonizacao(uint256 tokenId) external view returns (DadosCarbonizacao memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return dadosCarbonizacao[tokenId];
    }
    
    function getStatusRecompensa(uint256 tokenId) external view returns (StatusRecompensa memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return statusRecompensa[tokenId];
    }
    
    function getContractState() external view returns (ContractState memory) {
        return contractState;
    }
    
    function saldoContrato() external view returns (uint256) {
        return address(this).balance;
    }
    
    // === ATUALIZAÇÃO DE COTAÇÕES ===
    function updateCotacoes(
        uint256 _carbonPriceEUR,
        uint256 _cotacaoEuroBRL
    ) external onlyOwner {
        require(_carbonPriceEUR > 0, "Invalid carbon price");
        require(_cotacaoEuroBRL > 0, "Invalid EUR/BRL rate");
        
        contractState.carbonPriceEUR = _carbonPriceEUR;
        contractState.cotacaoEuroBRL = _cotacaoEuroBRL;
    }
    
    // === FUNÇÕES UTILITÁRIAS ===
    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) {
            return "0";
        }
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
    
    function _addressToString(address addr) internal pure returns (string memory) {
        bytes32 value = bytes32(uint256(uint160(addr)));
        bytes memory alphabet = "0123456789abcdef";
        
        bytes memory str = new bytes(42);
        str[0] = '0';
        str[1] = 'x';
        for (uint256 i = 0; i < 20; i++) {
            str[2+i*2] = alphabet[uint8(value[i + 12] >> 4)];
            str[3+i*2] = alphabet[uint8(value[i + 12] & 0x0f)];
        }
        return string(str);
    }
    
    // === RECEBER ETH ===
    receive() external payable {}
    
    // === RETIRADA DE EMERGÊNCIA ===
    function emergencyWithdraw() external onlyOwner {
        (bool success, ) = owner().call{value: address(this).balance}("");
        require(success, "Emergency withdrawal failed");
    }
}