// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonCreditNFT_E2Calculator
 * @dev Contrato adaptado do código R - Parte 2
 *
 * CALCULANDO O VALOR DE E2:
 * 1. Distância Estrada (gasolina + etanol)
 * 2. Distância Cidade (gasolina + etanol)
 * 3. Bônus de dirigibilidade (Prop_Bonus)
 * 4. E2 = Prop_Bonus * (df_estrada + df_cidade)
 */
contract CarbonCreditNFT_E2Calculator is
    ERC721,
    ERC721Enumerable,
    ReentrancyGuard,
    Ownable
{
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
        uint256 tanqueGasoline; // Tanque_gasoline = 100 - ethanol(%)
        uint256 dtEstradaGasolina; // dt_estrada_gasolina
        uint256 dtEstradaEtanol; // dt_estrada_etanol
        uint256 dfEstrada; // df_estrada = sum acima
        uint256 dtCidadeGasolina; // dt_cidade_gasolina
        uint256 dtCidadeEtanol; // dt_cidade_etanol
        uint256 dfCidade; // df_cidade = sum acima
        uint256 propBonus; // Prop_Bonus (multiplicador)
        uint256 e2Final; // E2 = Prop_Bonus * (df_estrada + df_cidade)
        uint256 totalDistance;
    }

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
    constructor() ERC721("CarbonCreditE2", "CCE2") {
        authorized[msg.sender] = true;
    }

    // === PARTE 2: FUNÇÃO PRINCIPAL - CALCULAR E2 ===
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

        // Executar cálculos da PARTE 2
        CalculationResult memory result = _performCalculations(params);

        // Criar NFT
        tokenId = _nextTokenId++;
        _safeMint(recipient, tokenId);

        // Armazenar resultado
        tokenCalculations[tokenId] = result;
        e2Value = result.e2Final;

        return (tokenId, e2Value);
    }

    // === CÁLCULOS INTERNOS (PARTE 2 DO CÓDIGO R) ===
    function _performCalculations(
        CalculationParams memory params
    ) internal pure returns (CalculationResult memory result) {
        // Passo 5 do R: Criando variável da proporção de gasolina no tanque
        // df$Tanque_gasoline <- 100 - (df$`ethanol (%)`)
        result.tanqueGasoline = (100 * 1e6) - params.ethanolPercent;

        // PARTE 2 - Distância Estrada
        // df$dt_estrada_gasolina <- df$`highway (distance)`*((1/df$road_gasoline)*((df$Tanque_gasoline/100)/df$Preco_Gasolina))
        if (params.roadGasoline > 0 && params.precoGasolina > 0) {
            // highway * (1/road_gasoline) * (tanque/100) / preco_gasolina
            // Simplificando: (highway * tanque) / (road_gasoline * 100 * preco_gasolina)
            result.dtEstradaGasolina =
                (params.highwayDistance * result.tanqueGasoline * 1e6) /
                (params.roadGasoline * 100 * params.precoGasolina);
        }

        // df$dt_estrada_etanol <- df$`highway (distance)`*((1/df$road_ethanol)*(1-(df$Tanque_gasoline/100))/df$Preco_Etanol)
        if (params.roadEthanol > 0 && params.precoEtanol > 0) {
            // 1 - (tanque_gasoline/100) = ethanolPercent/100
            uint256 ethanolFraction = params.ethanolPercent; // já está em formato correto
            // highway * (1/road_ethanol) * (ethanol_fraction/100) / preco_etanol
            result.dtEstradaEtanol =
                (params.highwayDistance * ethanolFraction * 1e6) /
                (params.roadEthanol * 100 * params.precoEtanol);
        }

        // df$df_estrada <- df$dt_estrada_gasolina + df$dt_estrada_etanol
        result.dfEstrada = result.dtEstradaGasolina + result.dtEstradaEtanol;

        // PARTE 2 - Distância Cidade
        // df$dt_cidade_gasolina <- df$`city (distance)`*((1/df$city_gasoline)*((df$Tanque_gasoline/100)/df$Preco_Gasolina))
        if (params.cityGasoline > 0 && params.precoGasolina > 0) {
            result.dtCidadeGasolina =
                (params.cityDistance * result.tanqueGasoline * 1e6) /
                (params.cityGasoline * 100 * params.precoGasolina);
        }

        // df$dt_cidade_etanol <- df$`city (distance)`*((1/df$city_ethanol)*(1-(df$Tanque_gasoline/100)/df$Preco_Etanol))
        if (params.cityEthanol > 0 && params.precoEtanol > 0) {
            uint256 ethanolFraction = params.ethanolPercent;
            result.dtCidadeEtanol =
                (params.cityDistance * ethanolFraction * 1e6) /
                (params.cityEthanol * 100 * params.precoEtanol);
        }

        // df$df_cidade <- df$dt_cidade_gasolina + df$dt_cidade_etanol
        result.dfCidade = result.dtCidadeGasolina + result.dtCidadeEtanol;

        // PARTE 2 - Calculando o bônus a receber pela dirigibilidade
        // df$Prop_Bonus <- 1 + ((df$`behavior_cautious (%)`/100)*0.10 + (df$`behavior_normal (%)`/100)*0.05 + (df$`behavior_aggressive (%)`/100)*0)
        result.propBonus =
            1e6 + // 1.0 com escala 1e6
            (params.behaviorCautious * 100000) /
            1e6 + // 0.10 = 100000/1e6
            (params.behaviorNormal * 50000) /
            1e6; // 0.05 = 50000/1e6
        // aggressive * 0 = não adiciona nada

        // PARTE 2 - Calculando o E2
        // df$E2 <- df$Prop_Bonus*(df$df_estrada+df$df_cidade)
        uint256 totalDistanceCost = result.dfEstrada + result.dfCidade;
        result.e2Final = (result.propBonus * totalDistanceCost) / 1e6; // Ajustar escala

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

    // === FUNÇÕES REQUERIDAS PELO ERC721Enumerable ===
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        return super._update(to, tokenId, auth);
    }

    function _increaseBalance(
        address account,
        uint128 value
    ) internal override(ERC721, ERC721Enumerable) {
        super._increaseBalance(account, value);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC721, ERC721Enumerable) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // === FUNÇÃO PARA RECEBER ETH ===
    receive() external payable {}

    function withdraw() external onlyOwner {
        payable(owner()).transfer(address(this).balance);
    }

    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
