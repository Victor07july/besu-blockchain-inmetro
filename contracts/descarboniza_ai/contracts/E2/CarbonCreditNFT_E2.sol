// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CarbonCreditNFT_E2Calculator
 * @dev Contrato adaptado do código Python - Cálculo E2 baseado em conversão de energia
 *
 * PARTE 2 - CALCULANDO O VALOR DE E2:
 * 1. Conversão de combustível para energia elétrica equivalente (MJ -> kWh)
 * 2. Cálculo do custo energético por distância (estrada + cidade)
 * 3. Aplicação de bônus por comportamento de direção
 * 4. E2 = Prop_Bonus * (Valores_Estrada + Valores_Cidade)
 *
 * CONSTANTES:
 * - MJ_kWh = 0.2778 (conversão Megajoule para kWh)
 * - gasoline_MJ = 29.5 (energia por litro de gasolina)
 * - etanol_MJ = 21.3 (energia por litro de etanol)
 * - preco_tarifa_convencional = 0.774 R$/kWh
 *
 * PARTE 3 - EVENTOS PARA TRACKING:
 * Eventos emitidos para permitir análise off-chain dos valores E2
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
        uint256 totalDistance; // total_distance para tracking
    }

    // === EVENTOS (Parte 3 - para tracking e análise) ===
    event E2Calculated(
        address indexed user,
        uint256 indexed tokenId,
        uint256 e2Value,
        uint256 totalDistance,
        uint256 timestamp
    );

    event E2DetailedCalculation(
        uint256 indexed tokenId,
        uint256 dfEstrada,
        uint256 dfCidade,
        uint256 propBonus,
        uint256 tanqueGasoline
    );

    // === EVENTOS DE MARKETPLACE ===
    event TokenListed(
        uint256 indexed tokenId,
        address indexed seller,
        uint256 priceInBRL
    );

    event TokenDelisted(uint256 indexed tokenId);

    event TokenTransferred(
        uint256 indexed tokenId,
        address indexed from,
        address indexed to,
        uint256 priceBRL
    );

    // === ESTADO DO CONTRATO ===
    uint256 private _nextTokenId = 1;
    mapping(uint256 => CalculationResult) public tokenCalculations;
    mapping(address => bool) public authorized;

    // === MARKETPLACE STATE ===
    mapping(uint256 => bool) public isListed; // Token está à venda?
    mapping(uint256 => uint256) public listingPriceBRL; // Preço em BRL * 1e6

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
        // precoGasolina e precoEtanol não são mais usados - constantes hardcoded no cálculo
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

        // Listar automaticamente para venda com preço = E2 (em BRL)
        isListed[tokenId] = true;
        listingPriceBRL[tokenId] = e2Value;

        // PARTE 3: Emitir eventos para tracking
        emit E2Calculated(
            recipient,
            tokenId,
            e2Value,
            result.totalDistance,
            block.timestamp
        );
        emit E2DetailedCalculation(
            tokenId,
            result.dfEstrada,
            result.dfCidade,
            result.propBonus,
            result.tanqueGasoline
        );

        // Emitir evento de listagem
        emit TokenListed(tokenId, recipient, e2Value);

        return (tokenId, e2Value);
    }

    // === CÁLCULOS INTERNOS (BASEADO NO CÓDIGO PYTHON) ===
    function _performCalculations(
        CalculationParams memory params
    ) internal pure returns (CalculationResult memory result) {
        // Constantes para conversão de energia (valores * 1e6 para precisão)
        // MJ_kWh = 0.2778, gasoline_MJ = 29.5, etanol_MJ = 21.3
        // preco_tarifa_convencional = 0.774 R$/kWh

        // Passo 1: Tanque de gasolina (%)
        // df["Tanque_gasoline"] = 100 - df["ethanol (%)"]
        result.tanqueGasoline = (100 * 1e6) - params.ethanolPercent;

        // Passo 2: Conversões de energia para preço
        // convert_gasoline = (MJ_kWh * gasoline_MJ * preco_tarifa * (Tanque_gasoline/100))
        // convert_gasoline = (0.2778 * 29.5 * 0.774) * (tanque/100)
        // convert_gasoline = 6.339906 * (tanque/100)
        // tanqueGasoline já está em *1e6, então dividir por (100 * 1e6)
        uint256 convertGasoline = (result.tanqueGasoline * 6339906) /
            (100 * 1e6);

        // convert_etanol = (MJ_kWh * etanol_MJ * preco_tarifa * (1 - Tanque_gasoline/100))
        // convert_etanol = (0.2778 * 21.3 * 0.774) * (ethanol_percent/100)
        // convert_etanol = 4.579794 * (ethanol/100)
        // ethanolPercent já está em *1e6, então dividir por (100 * 1e6)
        uint256 convertEtanol = (params.ethanolPercent * 4579794) / (100 * 1e6);

        // Passo 3: Valores Estrada (R$)
        // valores_estrada = ((convert_gasoline/road_gasoline) + (convert_etanol/road_ethanol)) * highway_distance
        if (params.roadGasoline > 0) {
            result.dtEstradaGasolina =
                (convertGasoline * params.highwayDistance) /
                params.roadGasoline;
        }
        if (params.roadEthanol > 0) {
            result.dtEstradaEtanol =
                (convertEtanol * params.highwayDistance) /
                params.roadEthanol;
        }
        result.dfEstrada = result.dtEstradaGasolina + result.dtEstradaEtanol;

        // Passo 4: Valores Cidade (R$)
        // valores_cidade = ((convert_gasoline/city_gasoline) + (convert_etanol/city_ethanol)) * highway_distance
        // IMPORTANTE: No Python original, Valores_cidade TAMBÉM multiplica por highway_distance!
        if (params.cityGasoline > 0) {
            result.dtCidadeGasolina =
                (convertGasoline * params.highwayDistance) /
                params.cityGasoline;
        }
        if (params.cityEthanol > 0) {
            result.dtCidadeEtanol =
                (convertEtanol * params.highwayDistance) /
                params.cityEthanol;
        }
        result.dfCidade = result.dtCidadeGasolina + result.dtCidadeEtanol;

        // Passo 5: Prop_Bonus (bônus de comportamento)
        // prop_bonus = (cautious/100)*0.05 + (normal/100)*0.02 + (aggressive/100)*0.005
        // Como params já estão em *1e6, precisamos calcular:
        // (x * 1e6 / 100) * 0.05 = (x * 1e6 * 0.05) / 100 = (x * 50000) / 100
        // Mas queremos resultado em escala 1e6, então: (x * 50000) / (100 * 1e6) * 1e6 = (x * 50000) / 100
        result.propBonus =
            (params.behaviorCautious * 50000) /
            (100 * 1e6) + // (x*1e6/100) * 0.05 = x * 50000 / (100 * 1e6)
            (params.behaviorNormal * 20000) /
            (100 * 1e6) + // (x*1e6/100) * 0.02 = x * 20000 / (100 * 1e6)
            (params.behaviorAggressive * 5000) /
            (100 * 1e6); // (x*1e6/100) * 0.005 = x * 5000 / (100 * 1e6)

        // Passo 6: E2 Final (R$)
        // e2 = prop_bonus * (valores_estrada + valores_cidade)
        uint256 totalDistanceCost = result.dfEstrada + result.dfCidade;
        result.e2Final = (result.propBonus * totalDistanceCost) / 1e6; // Ajustar escala

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

    function simulateE2Calculation(
        CalculationParams memory params
    ) external pure returns (CalculationResult memory) {
        return _performCalculations(params);
    }

    // Função para obter múltiplos cálculos (útil para análise como na Parte 3)
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

    // === MARKETPLACE: LISTAR TOKEN À VENDA ===
    function listToken(uint256 tokenId, uint256 priceBRL) external {
        require(_ownerOf(tokenId) == msg.sender, "Nao e o dono");
        require(priceBRL > 0, "Preco deve ser > 0");

        isListed[tokenId] = true;
        listingPriceBRL[tokenId] = priceBRL;

        emit TokenListed(tokenId, msg.sender, priceBRL);
    }

    // === MARKETPLACE: REMOVER DA VENDA ===
    function delistToken(uint256 tokenId) external {
        require(_ownerOf(tokenId) == msg.sender, "Nao e o dono");
        require(isListed[tokenId], "Token nao esta listado");

        isListed[tokenId] = false;
        listingPriceBRL[tokenId] = 0;

        emit TokenDelisted(tokenId);
    }

    // === MARKETPLACE: TRANSFERIR NFT APÓS PAGAMENTO OFF-CHAIN ===
    function transferNFT(uint256 tokenId, address buyer) external nonReentrant {
        require(isListed[tokenId], "Token nao esta a venda");

        address seller = _ownerOf(tokenId);
        require(seller == msg.sender, "Apenas o dono pode transferir");
        require(buyer != address(0), "Comprador invalido");
        require(buyer != seller, "Nao pode transferir para si mesmo");

        uint256 priceBRL = listingPriceBRL[tokenId];

        // Remover da venda
        isListed[tokenId] = false;
        listingPriceBRL[tokenId] = 0;

        // Transferir NFT
        _transfer(seller, buyer, tokenId);

        emit TokenTransferred(tokenId, seller, buyer, priceBRL);
    }

    // === MARKETPLACE: LISTAR TODOS OS TOKENS DISPONÍVEIS ===
    function getAllTokensWithPrices()
        external
        view
        returns (
            uint256[] memory tokenIds,
            uint256[] memory e2Values,
            uint256[] memory pricesBRL,
            address[] memory owners,
            bool[] memory listed
        )
    {
        uint256 total = totalSupply();

        tokenIds = new uint256[](total);
        e2Values = new uint256[](total);
        pricesBRL = new uint256[](total);
        owners = new address[](total);
        listed = new bool[](total);

        for (uint256 i = 0; i < total; i++) {
            uint256 tokenId = tokenByIndex(i);
            tokenIds[i] = tokenId;
            e2Values[i] = tokenCalculations[tokenId].e2Final;
            pricesBRL[i] = isListed[tokenId] ? listingPriceBRL[tokenId] : 0;
            owners[i] = _ownerOf(tokenId);
            listed[i] = isListed[tokenId];
        }

        return (tokenIds, e2Values, pricesBRL, owners, listed);
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
