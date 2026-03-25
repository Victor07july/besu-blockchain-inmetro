// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonCreditNFT_E1
 * @dev Contrato adaptado do código Python - Cálculo E1 (emissões CO2)
 *
 * CÁLCULO E1 - META DE EMISSÃO CO2:
 * 1. Calcula Meta_CO2 baseado em consumo de combustível (gasolina/etanol)
 * 2. Compara com emissões reais para obter Diff (economia)
 * 3. Calcula valor monetário e1 usando preço do carbono europeu
 *
 * CONSTANTES:
 * - EMISSAO_GASOLINA = 1.720 kg CO2/L
 * - EMISSAO_ETANOL = 1.510 kg CO2/L
 *
 * FÓRMULA:
 * Meta_CO2 = (dist_highway / consumo) * emissão + (dist_city / consumo) * emissão
 * Diff = Meta_CO2 - emissão_real (economia)
 * e1 = Diff * preço_carbono / 1_000_000 (valor em BRL)
 */
contract CarbonCreditNFT_E1 is
    ERC721,
    ERC721Enumerable,
    ReentrancyGuard,
    Ownable
{
    // === ESTRUTURAS DE DADOS ===

    struct CalculationParams {
        uint256 highwayDistance; // Distância rodovia em km * 1e6
        uint256 cityDistance; // Distância cidade em km * 1e6
        uint256 ethanolPercent; // Percentual etanol (0-100) * 1e6
        uint256 roadGasoline; // Consumo rodovia gasolina (km/L) * 1e6
        uint256 roadEthanol; // Consumo rodovia etanol (km/L) * 1e6
        uint256 cityGasoline; // Consumo cidade gasolina (km/L) * 1e6
        uint256 cityEthanol; // Consumo cidade etanol (km/L) * 1e6
        uint256 realCO2Emissions; // Emissões reais medidas (gramas) * 1e6
        uint256 carbonPricePerTon; // Preço carbono (BRL/tonelada) * 1e6
    }

    struct CalculationResult {
        uint256 tanqueGasoline; // Percentual gasolina no tanque
        uint256 parte1; // Emissões rodovia (gramas) * 1e6
        uint256 parte2; // Emissões cidade (gramas) * 1e6
        uint256 metaCO2; // Meta total CO2 (gramas) * 1e6
        uint256 diff; // Economia CO2 (gramas) * 1e6
        uint256 e1Value; // Valor monetário (BRL) * 1e6
        uint256 totalDistance; // Distância total percorrida
    }

    // === EVENTOS ===
    event CarbonCreditCalculated(
        address indexed user,
        uint256 indexed tokenId,
        uint256 metaCO2,
        uint256 diff,
        uint256 e1Value,
        uint256 timestamp
    );

    // === ESTADO DO CONTRATO ===
    uint256 private _nextTokenId = 1;
    mapping(uint256 => CalculationResult) public tokenCalculations;
    mapping(address => bool) public authorized;

    // === MODIFICADORES ===
    modifier onlyAuthorized() {
        require(
            authorized[msg.sender] || msg.sender == owner(),
            "Nao autorizado"
        );
        _;
    }

    // === CONSTRUTOR ===
    constructor() ERC721("CarbonCreditE1", "CCE1") {
        authorized[msg.sender] = true;
    }

    // === FUNÇÃO PRINCIPAL: CALCULAR E1 E CRIAR NFT ===
    function calculateAndMint(
        CalculationParams memory params,
        address recipient
    )
        external
        onlyAuthorized
        nonReentrant
        returns (uint256 tokenId, uint256 e1Value)
    {
        // Validações básicas
        require(params.roadGasoline > 0, "Road gasoline deve ser > 0");
        require(params.roadEthanol > 0, "Road ethanol deve ser > 0");
        require(params.cityGasoline > 0, "City gasoline deve ser > 0");
        require(params.cityEthanol > 0, "City ethanol deve ser > 0");
        require(
            params.ethanolPercent <= 100 * 1e6,
            "Ethanol % deve ser <= 100"
        );
        require(params.carbonPricePerTon > 0, "Carbon price deve ser > 0");

        // Executar cálculos
        CalculationResult memory result = _performCalculations(params);

        // Criar NFT
        tokenId = _nextTokenId++;
        _safeMint(recipient, tokenId);

        // Armazenar resultado
        tokenCalculations[tokenId] = result;
        e1Value = result.e1Value;

        // Emitir evento
        emit CarbonCreditCalculated(
            recipient,
            tokenId,
            result.metaCO2,
            result.diff,
            e1Value,
            block.timestamp
        );

        return (tokenId, e1Value);
    }

    // === CÁLCULOS INTERNOS (BASEADO NO CÓDIGO PYTHON) ===
    function _performCalculations(
        CalculationParams memory params
    ) internal pure returns (CalculationResult memory result) {
        // Constantes de emissão (kg CO2/L convertidos para g/L * 1e6)
        // EMISSAO_GASOLINA = 1.720 kg/L = 1720 g/L
        // EMISSAO_ETANOL = 1.510 kg/L = 1510 g/L
        uint256 EMISSAO_GASOLINA = 1720 * 1e6; // gramas * 1e6
        uint256 EMISSAO_ETANOL = 1510 * 1e6; // gramas * 1e6

        // Passo 1: Tanque de gasolina (%)
        // df["Tanque_gasoline"] = 100 - df["ethanol (%)"]
        result.tanqueGasoline = (100 * 1e6) - params.ethanolPercent;

        // Passo 2: Proporções (já em escala 1e6)
        uint256 p_gas = result.tanqueGasoline; // Já está dividido por 100 implicitamente nas operações
        uint256 p_etanol = params.ethanolPercent;

        // Passo 3: Parte 1 - Emissões Estrada (highway)
        // parte_1_1 = dist_highway * (1/road_gasoline) * (p_gas/100) * EMISSAO_GASOLINA * 1000
        // parte_1_2 = dist_highway * (1/road_ethanol) * (p_etanol/100) * EMISSAO_ETANOL * 1000
        // Multiplicamos por 1000 apenas no final já que EMISSAO já está em gramas

        uint256 parte_1_1 = 0;
        uint256 parte_1_2 = 0;

        if (params.roadGasoline > 0) {
            // (highwayDistance * 1e6) * (EMISSAO_GASOLINA * 1e6) * (p_gas * 1e6) / (roadGasoline * 1e6) / (100 * 1e6)
            // = highwayDistance * EMISSAO_GASOLINA * p_gas / roadGasoline / 100
            parte_1_1 =
                (params.highwayDistance * EMISSAO_GASOLINA * p_gas) /
                (params.roadGasoline * 100 * 1e6);
        }

        if (params.roadEthanol > 0) {
            parte_1_2 =
                (params.highwayDistance * EMISSAO_ETANOL * p_etanol) /
                (params.roadEthanol * 100 * 1e6);
        }

        result.parte1 = parte_1_1 + parte_1_2;

        // Passo 4: Parte 2 - Emissões Cidade (city)
        uint256 parte_2_1 = 0;
        uint256 parte_2_2 = 0;

        if (params.cityGasoline > 0) {
            parte_2_1 =
                (params.cityDistance * EMISSAO_GASOLINA * p_gas) /
                (params.cityGasoline * 100 * 1e6);
        }

        if (params.cityEthanol > 0) {
            parte_2_2 =
                (params.cityDistance * EMISSAO_ETANOL * p_etanol) /
                (params.cityEthanol * 100 * 1e6);
        }

        result.parte2 = parte_2_1 + parte_2_2;

        // Passo 5: Meta_CO2 (gramas)
        result.metaCO2 = result.parte1 + result.parte2;

        // Passo 6: Diff (economia de CO2 em gramas)
        // df["Diff"] = df["Meta_CO2"] - df["co2_etanol_original_gas_1720_flex"]
        if (result.metaCO2 >= params.realCO2Emissions) {
            result.diff = result.metaCO2 - params.realCO2Emissions;
        } else {
            result.diff = 0; // Não houve economia
        }

        // Passo 7: e1 (valor em BRL)
        // df["e1"] = df["Diff"] * df["Real_price"] / 1_000_000.0
        // Diff está em gramas * 1e6, Real_price em BRL/tonelada * 1e6
        // 1 tonelada = 1_000_000 gramas
        // e1 = (Diff_gramas * carbonPrice_BRL_ton) / 1_000_000
        result.e1Value =
            (result.diff * params.carbonPricePerTon) /
            (1_000_000 * 1e6);

        // Para tracking
        result.totalDistance = params.highwayDistance + params.cityDistance;

        return result;
    }

    // === FUNÇÕES DE VISUALIZAÇÃO ===
    function getCalculationDetails(
        uint256 tokenId
    ) external view returns (CalculationResult memory) {
        require(_ownerOf(tokenId) != address(0), "Token nao existe");
        return tokenCalculations[tokenId];
    }

    function getBatchCalculations(
        uint256[] memory tokenIds
    ) external view returns (CalculationResult[] memory) {
        CalculationResult[] memory results = new CalculationResult[](
            tokenIds.length
        );
        for (uint256 i = 0; i < tokenIds.length; i++) {
            require(_ownerOf(tokenIds[i]) != address(0), "Token nao existe");
            results[i] = tokenCalculations[tokenIds[i]];
        }
        return results;
    }

    // === FUNÇÕES ADMINISTRATIVAS ===
    function setAuthorized(address user, bool status) external onlyOwner {
        authorized[user] = status;
    }

    function nextTokenId() external view returns (uint256) {
        return _nextTokenId;
    }

    // === FUNÇÕES REQUERIDAS PELO ERC721Enumerable ===
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override(ERC721, ERC721Enumerable) {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721Enumerable) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // === FUNÇÃO PARA RECEBER ETH ===
    receive() external payable {}

    function withdraw() external onlyOwner {
        payable(msg.sender).transfer(address(this).balance);
    }

    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
