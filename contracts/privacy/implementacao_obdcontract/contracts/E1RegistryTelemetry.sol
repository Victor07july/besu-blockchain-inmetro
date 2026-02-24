// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title E1RegistryTelemetry
 * @dev Contrato simplificado para dados de telemetria OBD em tempo real
 * Compatível com formato OBDLink.csv após aplicação de Differential Privacy
 *
 * Diferenças vs E1RegistryGPS:
 * - Não requer agregação highway/city
 * - Calcula emissão diretamente de fuel rate
 * - Aceita velocidade média ao invés de distâncias
 * - Estrutura de dados mais simples
 */
contract E1RegistryTelemetry {
    struct GPSLocation {
        int256 latitude; // × 1e6
        int256 longitude; // × 1e6
    }

    struct TelemetryParams {
        string vin;
        uint256 timestamp; // Unix timestamp
        GPSLocation startLocation; // Coordenada inicial (com DP)
        GPSLocation endLocation; // Coordenada final (com DP)
        uint16 startElevation; // Elevação inicial (metros)
        uint16 endElevation; // Elevação final (metros)
        uint256 avgSpeed; // Velocidade média (km/h × 1e3)
        uint256 ethanolPercent; // % etanol × 1e3 (ex: 32.5% = 32500)
        uint256 fuelRateAvg; // Fuel rate médio (l/hr × 1e3)
        uint256 tripDuration; // Duração da viagem (segundos)
        uint256 carbonPrice; // Preço do carbono (R$/ton × 1e6)
        address pseudonimo;
    }

    struct TelemetryData {
        string vin;
        uint256 timestamp;
        GPSLocation startLocation;
        GPSLocation endLocation;
        uint16 startElevation;
        uint256 avgSpeed;
        uint256 ethanolPercent;
        uint256 fuelConsumed; // Combustível consumido (l × 1e6)
        uint256 emissaoCalculada; // Emissão calculada (gCO2 × 1e6)
        int256 valorE1; // Valor E1 (R$ × 1e6)
        address pseudonimo;
        bool pago;
    }

    address public owner;
    address public oracle;

    mapping(uint256 => TelemetryData) public trips;
    mapping(string => uint256[]) public vinToTrips;

    uint256 public tripCount;
    uint256 public totalPago;

    // Fatores de emissão (gCO2/litro × 1e6)
    uint256 constant EMISSAO_GASOLINA = 2310 * 1e6; // 2310 gCO2/l
    uint256 constant EMISSAO_ETANOL = 1510 * 1e6; // 1510 gCO2/l

    event TripRegistered(
        uint256 indexed tripId,
        string vin,
        uint256 emissao,
        int256 valorE1,
        address pseudonimo
    );

    event PaymentProcessed(
        uint256 indexed tripId,
        address indexed pseudonimo,
        int256 valor
    );

    event OracleUpdated(address indexed oldOracle, address indexed newOracle);

    modifier onlyOwner() {
        require(msg.sender == owner, "Apenas owner");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == oracle, "Apenas oracle");
        _;
    }

    constructor() {
        owner = msg.sender;
        oracle = msg.sender;
    }

    /**
     * @dev Registra viagem baseada em dados de telemetria OBD
     */
    function registerTrip(
        TelemetryParams memory params
    ) external onlyOracle returns (uint256) {
        require(params.pseudonimo != address(0), "Pseudonimo invalido");
        require(params.fuelRateAvg > 0, "Fuel rate deve ser > 0");
        require(params.tripDuration > 0, "Duracao deve ser > 0");
        require(params.carbonPrice > 0, "Carbon price > 0");
        require(params.ethanolPercent <= 100 * 1e3, "Ethanol <= 100%");

        // Calcular consumo de combustível
        // fuelRate (l/hr × 1e3) × duration (s) / 3600 / 1e3 = litros
        uint256 fuelConsumed = (params.fuelRateAvg * params.tripDuration) /
            3600;

        // Calcular emissão baseada no mix de combustível
        uint256 emissao = _calculateEmission(
            fuelConsumed,
            params.ethanolPercent,
            params.startElevation
        );

        // Calcular valor E1
        // Para simplificar: valorE1 = emissão × carbonPrice
        // (emissão em gCO2 × 1e6) × (price em R$/ton × 1e6) / (1e6 × 1e6 × 1000) = R$ × 1e6
        int256 valorE1 = (int256(emissao) * int256(params.carbonPrice)) /
            int256(1_000_000 * 1e6);

        uint256 tripId = tripCount++;

        trips[tripId] = TelemetryData({
            vin: params.vin,
            timestamp: params.timestamp,
            startLocation: params.startLocation,
            endLocation: params.endLocation,
            startElevation: params.startElevation,
            avgSpeed: params.avgSpeed,
            ethanolPercent: params.ethanolPercent,
            fuelConsumed: fuelConsumed,
            emissaoCalculada: emissao,
            valorE1: valorE1,
            pseudonimo: params.pseudonimo,
            pago: false
        });

        vinToTrips[params.vin].push(tripId);

        emit TripRegistered(
            tripId,
            params.vin,
            emissao,
            valorE1,
            params.pseudonimo
        );

        return tripId;
    }

    /**
     * @dev Calcula emissão baseada em combustível consumido e mix gasolina/etanol
     * Aplica correção de elevação
     */
    function _calculateEmission(
        uint256 fuelConsumed, // litros × 1e3
        uint256 ethanolPercent, // % × 1e3
        uint16 elevation // metros
    ) internal pure returns (uint256) {
        // Proporção de cada combustível
        uint256 ethanolRatio = ethanolPercent; // já em × 1e3
        uint256 gasolineRatio = (100 * 1e3) - ethanolPercent;

        // Emissão base (gCO2 × 1e6)
        // fuelConsumed (l × 1e3) × emissao (gCO2/l × 1e6) × ratio / (100 × 1e3) / 1e3
        uint256 emissaoGasolina = (fuelConsumed *
            EMISSAO_GASOLINA *
            gasolineRatio) / (100 * 1e3 * 1e3);
        uint256 emissaoEtanol = (fuelConsumed * EMISSAO_ETANOL * ethanolRatio) /
            (100 * 1e3 * 1e3);

        uint256 emissaoBase = emissaoGasolina + emissaoEtanol;

        // Aplicar fator de elevação
        uint256 elevationFactor = _getElevationFactor(elevation);
        uint256 emissaoFinal = (emissaoBase * elevationFactor) / 100;

        return emissaoFinal;
    }

    /**
     * @dev Retorna fator de correção baseado em elevação
     */
    function _getElevationFactor(
        uint16 elevation
    ) internal pure returns (uint256) {
        if (elevation <= 100) {
            return 100; // 0-100m: Plano
        } else if (elevation <= 300) {
            return 105; // 100-300m: Ondulado (+5%)
        } else if (elevation <= 600) {
            return 115; // 300-600m: Montanhoso (+15%)
        } else if (elevation <= 1000) {
            return 125; // 600-1000m: Muito montanhoso (+25%)
        } else {
            return 140; // > 1000m: Extremamente montanhoso (+40%)
        }
    }

    /**
     * @dev Processar pagamento de crédito E1
     */
    function processPayment(uint256 _tripId) external onlyOwner {
        TelemetryData storage trip = trips[_tripId];

        require(!trip.pago, "Ja foi pago");
        require(trip.valorE1 > 0, "Valor deve ser positivo");

        trip.pago = true;
        totalPago += uint256(trip.valorE1);

        emit PaymentProcessed(_tripId, trip.pseudonimo, trip.valorE1);
    }

    /**
     * @dev Processar múltiplos pagamentos em batch
     */
    function batchProcessPayments(
        uint256[] memory _tripIds
    ) external onlyOwner {
        for (uint256 i = 0; i < _tripIds.length; i++) {
            uint256 tripId = _tripIds[i];
            TelemetryData storage trip = trips[tripId];

            if (!trip.pago && trip.valorE1 > 0) {
                trip.pago = true;
                totalPago += uint256(trip.valorE1);
                emit PaymentProcessed(tripId, trip.pseudonimo, trip.valorE1);
            }
        }
    }

    /**
     * @dev Atualizar endereço do oracle
     */
    function updateOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "Endereco invalido");
        address oldOracle = oracle;
        oracle = _newOracle;
        emit OracleUpdated(oldOracle, _newOracle);
    }

    /**
     * @dev Obter viagens de um VIN
     */
    function getTripsByVIN(
        string memory vin
    ) external view returns (uint256[] memory) {
        return vinToTrips[vin];
    }

    /**
     * @dev Obter dados de uma viagem
     */
    function getTrip(
        uint256 tripId
    ) external view returns (TelemetryData memory) {
        return trips[tripId];
    }
}
