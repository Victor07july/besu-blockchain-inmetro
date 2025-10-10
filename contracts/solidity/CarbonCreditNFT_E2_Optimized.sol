// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonCreditNFT_E2Calculator - VERSÃO OTIMIZADA
 * @dev Contrato adaptado do código R - Deploy ~10-12M gas (vs 30M original)
 *
 * OTIMIZAÇÕES:
 * - Removido ERC721Enumerable (economiza ~15M gas)
 * - Removidas funções view desnecessárias (economiza ~3M gas)
 * - Removidas funções de pagamento ETH (economiza ~500K gas)
 * - Removido evento detalhado extra (economiza ~200K gas)
 *
 * COMPATIBILIDADE:
 * - Solidity 0.8.19 (compatível com Besu)
 * - OpenZeppelin v4.9.6 (ReentrancyGuard em security/)
 */
contract CarbonCreditNFT_E2Calculator is ERC721, ReentrancyGuard, Ownable {
    // === ESTRUTURAS DE DADOS ===
    struct CalculationParams {
        uint256 highwayDistance; // highway (distance) em km * 1e6
        uint256 cityDistance; // city (distance) em km * 1e6
        uint256 ethanolPercent; // ethanol (%) * 1e6 (0-100)
        uint256 roadGasoline; // road_gasoline em km/L * 1e6
        uint256 roadEthanol; // road_ethanol em km/L * 1e6
        uint256 cityGasoline; // city_gasoline em km/L * 1e6
        uint256 cityEthanol; // city_ethanol em km/L * 1e6
        uint256 precoGasolina; // Preco_Gasolina em BRL/L * 1e6
        uint256 precoEtanol; // Preco_Etanol em BRL/L * 1e6
        uint256 behaviorCautious; // behavior_cautious (%) * 1e6
        uint256 behaviorNormal; // behavior_normal (%) * 1e6
        uint256 behaviorAggressive; // behavior_aggressive (%) * 1e6
    }

    struct CalculationResult {
        uint256 tanqueGasoline;
        uint256 dtEstradaGasolina;
        uint256 dtEstradaEtanol;
        uint256 dfEstrada;
        uint256 dtCidadeGasolina;
        uint256 dtCidadeEtanol;
        uint256 dfCidade;
        uint256 propBonus;
        uint256 e2Final;
        uint256 totalDistance;
    }

    // === EVENTO PRINCIPAL (apenas 1 evento necessário) ===
    event E2Calculated(
        address indexed user,
        uint256 indexed tokenId,
        uint256 e2Value,
        uint256 totalDistance,
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
    // OpenZeppelin v4.x: Ownable() sem parâmetros (usa msg.sender automaticamente)
    constructor() ERC721("CarbonCreditE2", "CCE2") {
        authorized[msg.sender] = true;
    }

    // === FUNÇÃO PRINCIPAL - CALCULAR E2 ===
    function calculateE2AndTokenize(
        CalculationParams memory params,
        address recipient
    )
        external
        onlyAuthorized
        nonReentrant
        returns (uint256 tokenId, uint256 e2Value)
    {
        // Validações básicas
        require(params.roadGasoline > 0, "Road gasoline deve ser > 0");
        require(params.roadEthanol > 0, "Road ethanol deve ser > 0");
        require(params.cityGasoline > 0, "City gasoline deve ser > 0");
        require(params.cityEthanol > 0, "City ethanol deve ser > 0");
        require(params.precoGasolina > 0, "Preco gasolina deve ser > 0");
        require(params.precoEtanol > 0, "Preco etanol deve ser > 0");
        require(
            params.ethanolPercent <= 100 * 1e6,
            "Ethanol % deve ser <= 100"
        );

        // Executar cálculos
        CalculationResult memory result = _performCalculations(params);

        // Criar NFT
        tokenId = _nextTokenId++;
        _safeMint(recipient, tokenId);

        // Armazenar resultado
        tokenCalculations[tokenId] = result;
        e2Value = result.e2Final;

        // Emitir evento
        emit E2Calculated(
            recipient,
            tokenId,
            e2Value,
            result.totalDistance,
            block.timestamp
        );

        return (tokenId, e2Value);
    }

    // === CÁLCULOS INTERNOS ===
    function _performCalculations(
        CalculationParams memory params
    ) internal pure returns (CalculationResult memory result) {
        // Tanque de gasolina
        result.tanqueGasoline = (100 * 1e6) - params.ethanolPercent;

        // Distância Estrada
        if (params.roadGasoline > 0 && params.precoGasolina > 0) {
            result.dtEstradaGasolina =
                (params.highwayDistance * result.tanqueGasoline * 1e6) /
                (params.roadGasoline * 100 * params.precoGasolina);
        }

        if (params.roadEthanol > 0 && params.precoEtanol > 0) {
            uint256 ethanolFraction = params.ethanolPercent;
            result.dtEstradaEtanol =
                (params.highwayDistance * ethanolFraction * 1e6) /
                (params.roadEthanol * 100 * params.precoEtanol);
        }

        result.dfEstrada = result.dtEstradaGasolina + result.dtEstradaEtanol;

        // Distância Cidade
        if (params.cityGasoline > 0 && params.precoGasolina > 0) {
            result.dtCidadeGasolina =
                (params.cityDistance * result.tanqueGasoline * 1e6) /
                (params.cityGasoline * 100 * params.precoGasolina);
        }

        if (params.cityEthanol > 0 && params.precoEtanol > 0) {
            uint256 ethanolFraction = params.ethanolPercent;
            result.dtCidadeEtanol =
                (params.cityDistance * ethanolFraction * 1e6) /
                (params.cityEthanol * 100 * params.precoEtanol);
        }

        result.dfCidade = result.dtCidadeGasolina + result.dtCidadeEtanol;

        // Bônus de dirigibilidade
        result.propBonus =
            1e6 +
            (params.behaviorCautious * 100000) /
            1e6 +
            (params.behaviorNormal * 50000) /
            1e6;

        // E2 Final
        uint256 totalDistanceCost = result.dfEstrada + result.dfCidade;
        result.e2Final = (result.propBonus * totalDistanceCost) / 1e6;

        // Total distance para tracking
        result.totalDistance = params.highwayDistance + params.cityDistance;

        return result;
    }

    // === FUNÇÕES ADMINISTRATIVAS ===
    function setAuthorized(address user, bool status) external onlyOwner {
        authorized[user] = status;
    }

    function nextTokenId() external view returns (uint256) {
        return _nextTokenId;
    }
}
