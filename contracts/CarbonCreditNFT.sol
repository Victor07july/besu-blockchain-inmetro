// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

/**
 * @title CarbonCreditNFT
 * @dev Contrato ERC-721 para tokenização de créditos de carbono baseado em economia de CO2 de veículos
 * Baseado no chaincode Fabric original
 */
contract CarbonCreditNFT is ERC721, ERC721URIStorage, Ownable {
    using Counters for Counters.Counter;

    // ==========================================
    // ESTRUTURAS DE DADOS
    // ==========================================

    struct ContractState {
        uint256 carbonPriceEUR; // Preço do carbono em EUR (em wei para precisão)
        uint256 precoCentavosPorG; // Preço em centavos por grama
        uint256 cotacaoEthEmReais; // Cotação ETH em reais (em wei)
        uint256 cotacaoEuroBRL; // Cotação EUR/BRL (em wei)
    }

    struct DadosCarbonizacao {
        uint256 tokenId;
        string vehicleId;
        address condutor;
        uint256 highwayDistance; // Distância na estrada (em metros)
        uint256 cityDistance; // Distância na cidade (em metros)
        uint256 ethanolPercent; // Percentual de etanol (em basis points: 100% = 10000)
        uint256 co2EtanolOriginal; // CO2 original do etanol (em gramas)
        uint256 roadGasoline; // Consumo gasolina estrada (km/L * 1000)
        uint256 roadEthanol; // Consumo etanol estrada (km/L * 1000)
        uint256 cityGasoline; // Consumo gasolina cidade (km/L * 1000)
        uint256 cityEthanol; // Consumo etanol cidade (km/L * 1000)
        uint256 tanqueGasoline; // Percentual gasolina no tanque (basis points)
        uint256 metaCO2; // Meta de CO2 calculada (em gramas)
        uint256 economiaCO2; // Economia de CO2 (em gramas)
        uint256 recompensaEmWei; // Recompensa em wei
        uint256 timestamp; // Timestamp da criação
    }

    struct StatusRecompensa {
        address condutor;
        uint256 tokenId;
        bool sacada;
        uint256 valor;
    }

    // ==========================================
    // VARIÁVEIS DE ESTADO
    // ==========================================

    Counters.Counter private _tokenIdCounter;
    ContractState public contractState;

    // Mapeamentos
    mapping(uint256 => DadosCarbonizacao) public dadosCarbonizacao;
    mapping(uint256 => StatusRecompensa) public statusRecompensa;
    mapping(address => uint256) public saldoCarteira;

    // Constantes para cálculos (baseadas no chaincode original)
    uint256 private constant FATOR_GASOLINA = 1720; // 1.720 kg CO2/L * 1000
    uint256 private constant FATOR_ETANOL = 1510; // 1.510 kg CO2/L * 1000
    uint256 private constant BASIS_POINTS = 10000; // 100% = 10000
    uint256 private constant GRAMS_TO_WEI = 1e18; // Conversão para wei

    // ==========================================
    // EVENTOS
    // ==========================================

    event CarbonCreditTokenized(
        uint256 indexed tokenId,
        address indexed condutor,
        string vehicleId,
        uint256 co2Economy,
        uint256 recompensaWei,
        uint256 timestamp
    );

    event RecompensaSacada(
        uint256 indexed tokenId,
        address indexed condutor,
        uint256 valor
    );

    event ContractStateUpdated(
        uint256 carbonPriceEUR,
        uint256 cotacaoEuroBRL,
        uint256 cotacaoEthEmReais
    );

    // ==========================================
    // CONSTRUCTOR
    // ==========================================

    constructor(
        string memory name,
        string memory symbol,
        uint256 _carbonPriceEUR,
        uint256 _cotacaoEuroBRL,
        uint256 _cotacaoEthEmReais
    ) ERC721(name, symbol) {
        contractState = ContractState({
            carbonPriceEUR: _carbonPriceEUR,
            precoCentavosPorG: 0,
            cotacaoEthEmReais: _cotacaoEthEmReais,
            cotacaoEuroBRL: _cotacaoEuroBRL
        });

        // Começar contador em 1
        _tokenIdCounter.increment();
    }

    // ==========================================
    // FUNÇÕES ADMINISTRATIVAS
    // ==========================================

    /**
     * @dev Atualiza o estado do contrato (apenas owner)
     */
    function updateContractState(
        uint256 _carbonPriceEUR,
        uint256 _cotacaoEuroBRL,
        uint256 _cotacaoEthEmReais
    ) external onlyOwner {
        contractState.carbonPriceEUR = _carbonPriceEUR;
        contractState.cotacaoEuroBRL = _cotacaoEuroBRL;
        contractState.cotacaoEthEmReais = _cotacaoEthEmReais;

        emit ContractStateUpdated(
            _carbonPriceEUR,
            _cotacaoEuroBRL,
            _cotacaoEthEmReais
        );
    }

    /**
     * @dev Permite ao owner adicionar fundos ao contrato para pagamento de recompensas
     */
    function depositFunds() external payable onlyOwner {
        require(msg.value > 0, "Valor deve ser maior que zero");
    }

    /**
     * @dev Permite ao owner sacar fundos do contrato
     */
    function withdrawFunds(uint256 amount) external onlyOwner {
        require(address(this).balance >= amount, "Saldo insuficiente");
        payable(owner()).transfer(amount);
    }

    // ==========================================
    // FUNÇÃO PRINCIPAL: TOKENIZAÇÃO
    // ==========================================

    /**
     * @dev Calcula economia de CO2 e cria NFT de crédito de carbono
     * Baseado na função CalculateE1AndTokenize do chaincode original
     */
    function calculateE1AndTokenize(
        string memory vehicleId,
        uint256 highwayDistance, // em metros
        uint256 cityDistance, // em metros
        uint256 ethanolPercent, // em basis points (5000 = 50%)
        uint256 co2EtanolOriginal, // em gramas
        uint256 roadGasoline, // km/L * 1000 para precisão
        uint256 roadEthanol, // km/L * 1000 para precisão
        uint256 cityGasoline, // km/L * 1000 para precisão
        uint256 cityEthanol, // km/L * 1000 para precisão
        uint256 tanqueGasoline // em basis points (7000 = 70% gasolina)
    ) external returns (uint256) {
        require(
            highwayDistance > 0 || cityDistance > 0,
            "Distancia deve ser maior que zero"
        );
        require(ethanolPercent <= BASIS_POINTS, "Percentual etanol invalido");
        require(tanqueGasoline <= BASIS_POINTS, "Percentual gasolina invalido");

        // ==========================================
        // CÁLCULO DA META DE CO2
        // ==========================================

        // PARTE 1 - Highway calculations
        uint256 parte_1_1 = 0;
        uint256 parte_1_2 = 0;

        if (roadGasoline > 0) {
            parte_1_1 =
                (highwayDistance * tanqueGasoline * FATOR_GASOLINA) /
                (roadGasoline * BASIS_POINTS);
        }

        if (roadEthanol > 0) {
            parte_1_2 =
                (highwayDistance * ethanolPercent * FATOR_ETANOL) /
                (roadEthanol * BASIS_POINTS);
        }

        uint256 parte_1 = parte_1_1 + parte_1_2;

        // PARTE 2 - City calculations
        uint256 parte_2_1 = 0;
        uint256 parte_2_2 = 0;

        if (cityGasoline > 0) {
            parte_2_1 =
                (cityDistance * tanqueGasoline * FATOR_GASOLINA) /
                (cityGasoline * BASIS_POINTS);
        }

        if (cityEthanol > 0) {
            parte_2_2 =
                (cityDistance * ethanolPercent * FATOR_ETANOL) /
                (cityEthanol * BASIS_POINTS);
        }

        uint256 parte_2 = parte_2_1 + parte_2_2;

        // META CO2 total
        uint256 metaCO2 = parte_1 + parte_2;

        // ==========================================
        // CÁLCULO DA ECONOMIA (E1)
        // ==========================================

        // DIFERENÇA (E1) = META CO2 - EMISSÃO REAL
        require(metaCO2 > co2EtanolOriginal, "Nao houve economia de CO2");

        uint256 economiaCO2 = metaCO2 - co2EtanolOriginal;

        // ==========================================
        // CÁLCULO DA RECOMPENSA (E2)
        // ==========================================

        // Calcular valor monetário em wei
        uint256 recompensaEmWei = (economiaCO2 *
            contractState.carbonPriceEUR *
            contractState.cotacaoEuroBRL) / (1e6 * 1e18); // Ajuste para gramas e wei

        require(recompensaEmWei > 0, "Recompensa deve ser maior que zero");

        // ==========================================
        // CRIAR NFT
        // ==========================================

        uint256 tokenId = _tokenIdCounter.current();
        _tokenIdCounter.increment();

        // Criar NFT para o condutor (msg.sender)
        _safeMint(msg.sender, tokenId);

        // Criar metadados JSON
        string memory tokenURI = _createTokenURI(
            vehicleId,
            economiaCO2,
            metaCO2,
            co2EtanolOriginal,
            recompensaEmWei
        );

        _setTokenURI(tokenId, tokenURI);

        // ==========================================
        // SALVAR DADOS
        // ==========================================

        // Salvar dados de carbonização
        dadosCarbonizacao[tokenId] = DadosCarbonizacao({
            tokenId: tokenId,
            vehicleId: vehicleId,
            condutor: msg.sender,
            highwayDistance: highwayDistance,
            cityDistance: cityDistance,
            ethanolPercent: ethanolPercent,
            co2EtanolOriginal: co2EtanolOriginal,
            roadGasoline: roadGasoline,
            roadEthanol: roadEthanol,
            cityGasoline: cityGasoline,
            cityEthanol: cityEthanol,
            tanqueGasoline: tanqueGasoline,
            metaCO2: metaCO2,
            economiaCO2: economiaCO2,
            recompensaEmWei: recompensaEmWei,
            timestamp: block.timestamp
        });

        // Salvar status da recompensa
        statusRecompensa[tokenId] = StatusRecompensa({
            condutor: msg.sender,
            tokenId: tokenId,
            sacada: false,
            valor: recompensaEmWei
        });

        // ==========================================
        // EMITIR EVENTO
        // ==========================================

        emit CarbonCreditTokenized(
            tokenId,
            msg.sender,
            vehicleId,
            economiaCO2,
            recompensaEmWei,
            block.timestamp
        );

        return tokenId;
    }

    // ==========================================
    // FUNÇÕES DE RECOMPENSA
    // ==========================================

    /**
     * @dev Permite ao proprietário do NFT sacar sua recompensa
     */
    function sacarRecompensa(uint256 tokenId) external {
        require(_exists(tokenId), "Token nao existe");
        require(
            ownerOf(tokenId) == msg.sender,
            "Apenas o proprietario pode sacar"
        );

        StatusRecompensa storage recompensa = statusRecompensa[tokenId];
        require(!recompensa.sacada, "Recompensa ja foi sacada");
        require(recompensa.valor > 0, "Nenhuma recompensa disponivel");
        require(
            address(this).balance >= recompensa.valor,
            "Contrato sem saldo suficiente"
        );

        // Marcar como sacada
        recompensa.sacada = true;

        // Adicionar ao saldo da carteira
        saldoCarteira[msg.sender] += recompensa.valor;

        // Transferir ETH
        payable(msg.sender).transfer(recompensa.valor);

        emit RecompensaSacada(tokenId, msg.sender, recompensa.valor);
    }

    /**
     * @dev Verifica se a recompensa foi sacada
     */
    function recompensaFoiSacada(uint256 tokenId) external view returns (bool) {
        require(_exists(tokenId), "Token nao existe");
        return statusRecompensa[tokenId].sacada;
    }

    /**
     * @dev Obtém o valor da recompensa para um token
     */
    function getValorRecompensa(
        uint256 tokenId
    ) external view returns (uint256) {
        require(_exists(tokenId), "Token nao existe");
        return statusRecompensa[tokenId].valor;
    }

    // ==========================================
    // FUNÇÕES DE CONSULTA
    // ==========================================

    /**
     * @dev Obtém dados completos de carbonização de um token
     */
    function getDadosCarbonizacao(
        uint256 tokenId
    ) external view returns (DadosCarbonizacao memory) {
        require(_exists(tokenId), "Token nao existe");
        return dadosCarbonizacao[tokenId];
    }

    /**
     * @dev Obtém saldo da carteira de um condutor
     */
    function getSaldoCarteira(
        address condutor
    ) external view returns (uint256) {
        return saldoCarteira[condutor];
    }

    /**
     * @dev Obtém o próximo token ID que será mintado
     */
    function getNextTokenId() external view returns (uint256) {
        return _tokenIdCounter.current();
    }

    /**
     * @dev Obtém informações do estado do contrato
     */
    function getContractState() external view returns (ContractState memory) {
        return contractState;
    }

    // ==========================================
    // FUNÇÕES INTERNAS
    // ==========================================

    /**
     * @dev Cria URI dos metadados do token
     */
    function _createTokenURI(
        string memory vehicleId,
        uint256 economiaCO2,
        uint256 metaCO2,
        uint256 co2Original,
        uint256 recompensaEmWei
    ) internal view returns (string memory) {
        return
            string(
                abi.encodePacked(
                    '{"vehicleId":"',
                    vehicleId,
                    '",',
                    '"co2Economy":"',
                    _toString(economiaCO2),
                    '",',
                    '"metaCO2":"',
                    _toString(metaCO2),
                    '",',
                    '"originalCO2":"',
                    _toString(co2Original),
                    '",',
                    '"recompensaEmWei":"',
                    _toString(recompensaEmWei),
                    '",',
                    '"carbonPriceEUR":"',
                    _toString(contractState.carbonPriceEUR),
                    '",',
                    '"eurBrlRate":"',
                    _toString(contractState.cotacaoEuroBRL),
                    '"}'
                )
            );
    }

    /**
     * @dev Converte uint256 para string
     */
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

    // ==========================================
    // OVERRIDES NECESSÁRIOS
    // ==========================================

    function _burn(
        uint256 tokenId
    ) internal override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }

    function tokenURI(
        uint256 tokenId
    ) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // ==========================================
    // FUNÇÃO PARA RECEBER ETH
    // ==========================================

    receive() external payable {
        // Permite que o contrato receba ETH
    }
}
