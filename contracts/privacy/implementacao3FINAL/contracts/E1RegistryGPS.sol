// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title E1RegistryGPS
 * @dev Extensão do E1Registry com coordenadas GPS protegidas por Differential Privacy
 * Implementação 2: Proof-of-concept para pesquisa
 */
contract E1RegistryGPS {
    struct GPSLocation {
        int256 latitude; // × 1e6 (ex: -5.7945° → -5794500)
        int256 longitude; // × 1e6
    }

    struct TripGPSParams {
        string vin;
        uint256 timestamp;
        uint256 highwayDistance;
        uint256 cityDistance;
        uint256 ethanolPercent;
        uint256 roadGasoline;
        uint256 roadEthanol;
        uint256 cityGasoline;
        uint256 cityEthanol;
        uint256 emissaoReal;
        uint256 carbonPrice;
        address pseudonimo;
        GPSLocation startLocation; // Com DP aplicado
        GPSLocation endLocation; // Com DP aplicado
        uint16 startElevation; // Elevação inicial em metros
    }

    struct TripGPSData {
        string vin;
        uint256 timestamp;
        uint256 totalDistance;
        uint256 emissaoReal;
        uint256 metaCO2;
        int256 diff;
        uint256 realPrice;
        int256 valorE1;
        address pseudonimo;
        bool pago;
        GPSLocation startLocation;
        GPSLocation endLocation;
        uint256 gpsDistance; // Distância calculada por GPS (km × 1e6)
        uint16 startElevation; // Elevação inicial em metros
    }

    address public owner;
    address public oracle;

    mapping(uint256 => TripGPSData) public trips;
    mapping(string => uint256[]) public vinToTrips;

    uint256 public tripCount;
    uint256 public totalPago;

    uint256 constant EMISSAO_GASOLINA = 1720 * 1e6;
    uint256 constant EMISSAO_ETANOL = 1510 * 1e6;

    event TripRegistered(
        uint256 indexed tripId,
        string vin,
        uint256 metaCO2,
        int256 diff,
        int256 valorE1,
        address pseudonimo,
        int256 startLat,
        int256 startLon
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

    function registerTrip(
        TripGPSParams memory params
    ) external onlyOracle returns (uint256) {
        require(params.pseudonimo != address(0), "Pseudonimo invalido");
        require(params.roadGasoline > 0, "Road gasoline > 0");
        require(params.roadEthanol > 0, "Road ethanol > 0");
        require(params.cityGasoline > 0, "City gasoline > 0");
        require(params.cityEthanol > 0, "City ethanol > 0");
        require(params.ethanolPercent <= 100 * 1e6, "Ethanol <= 100%");
        require(params.carbonPrice > 0, "Carbon price > 0");

        // Calcular E1
        (uint256 metaCO2, int256 diff, int256 valorE1) = _calculateE1(params);

        // Calcular distância GPS (usando fórmula de Haversine simplificada)
        uint256 gpsDistance = _calculateGPSDistance(
            params.startLocation,
            params.endLocation
        );

        uint256 tripId = tripCount++;
        uint256 totalDistance = params.highwayDistance + params.cityDistance;

        trips[tripId] = TripGPSData({
            vin: params.vin,
            timestamp: params.timestamp,
            totalDistance: totalDistance,
            emissaoReal: params.emissaoReal,
            metaCO2: metaCO2,
            diff: diff,
            realPrice: params.carbonPrice,
            valorE1: valorE1,
            pseudonimo: params.pseudonimo,
            pago: false,
            startLocation: params.startLocation,
            endLocation: params.endLocation,
            gpsDistance: gpsDistance,
            startElevation: params.startElevation
        });

        vinToTrips[params.vin].push(tripId);

        emit TripRegistered(
            tripId,
            params.vin,
            metaCO2,
            diff,
            valorE1,
            params.pseudonimo,
            params.startLocation.latitude,
            params.startLocation.longitude
        );

        return tripId;
    }

    function _calculateE1(
        TripGPSParams memory params
    ) internal pure returns (uint256 metaCO2, int256 diff, int256 valorE1) {
        uint256 tanqueGasoline = (100 * 1e6) - params.ethanolPercent;
        uint256 p_gas = tanqueGasoline;
        uint256 p_etanol = params.ethanolPercent;

        uint256 parte_1_1 = 0;
        uint256 parte_1_2 = 0;

        if (params.roadGasoline > 0) {
            parte_1_1 =
                (params.highwayDistance * EMISSAO_GASOLINA * p_gas) /
                (params.roadGasoline * 100 * 1e6);
        }

        if (params.roadEthanol > 0) {
            parte_1_2 =
                (params.highwayDistance * EMISSAO_ETANOL * p_etanol) /
                (params.roadEthanol * 100 * 1e6);
        }

        uint256 parte1 = parte_1_1 + parte_1_2;

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

        uint256 parte2 = parte_2_1 + parte_2_2;

        metaCO2 = parte1 + parte2;

        // Aplicar fator de correção baseado em elevação
        uint256 elevationFactor = _getElevationFactor(params.startElevation);
        metaCO2 = (metaCO2 * elevationFactor) / 100;

        if (metaCO2 >= params.emissaoReal) {
            diff = int256(metaCO2 - params.emissaoReal);
        } else {
            diff = -int256(params.emissaoReal - metaCO2);
        }

        valorE1 = (diff * int256(params.carbonPrice)) / int256(1_000_000 * 1e6);

        return (metaCO2, diff, valorE1);
    }

    /**
     * @dev Retorna fator de correção baseado em elevação
     * Veículos em regiões montanhosas consomem 15-40% mais combustível
     * @param elevation Elevação em metros
     * @return Fator multiplicador × 100 (ex: 115 = 1.15x = +15%)
     */
    function _getElevationFactor(
        uint16 elevation
    ) internal pure returns (uint256) {
        if (elevation <= 100) {
            return 100; // 0-100m: Plano (sem correção)
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
     * @dev Calcula distância entre dois pontos GPS usando Haversine simplificado
     * @return Distância em km × 1e6
     */
    function _calculateGPSDistance(
        GPSLocation memory start,
        GPSLocation memory end
    ) internal pure returns (uint256) {
        // Diferenças em graus (já × 1e6)
        int256 dLat = end.latitude - start.latitude;
        int256 dLon = end.longitude - start.longitude;

        // Conversão aproximada: 1° ≈ 111 km
        // Usando distância euclidiana simplificada (sem Haversine completo por limitações de Solidity)

        // |dLat| e |dLon| em valor absoluto
        uint256 absLat = dLat >= 0 ? uint256(dLat) : uint256(-dLat);
        uint256 absLon = dLon >= 0 ? uint256(dLon) : uint256(-dLon);

        // Distância aproximada em km × 1e6
        // dLat em graus × 1e6 → dLat / 1e6 → × 111 → km
        // Simplificando: dLat × 111 / 1
        uint256 latKm = (absLat * 111) / 1e6;
        uint256 lonKm = (absLon * 111) / 1e6;

        // Distância euclidiana: sqrt(latKm² + lonKm²)
        // Como Solidity não tem sqrt, usamos aproximação: max(lat, lon) + min(lat, lon)/2
        uint256 maxKm = latKm > lonKm ? latKm : lonKm;
        uint256 minKm = latKm <= lonKm ? latKm : lonKm;

        uint256 distKm = maxKm + (minKm / 2);

        return distKm * 1e6; // Retorna km × 1e6
    }

    function processPayment(uint256 _tripId) external onlyOwner {
        TripGPSData storage trip = trips[_tripId];

        require(!trip.pago, "Ja foi pago");
        require(trip.valorE1 > 0, "Valor deve ser positivo");

        trip.pago = true;
        totalPago += uint256(trip.valorE1);

        emit PaymentProcessed(_tripId, trip.pseudonimo, trip.valorE1);
    }

    function batchProcessPayments(
        uint256[] memory _tripIds
    ) external onlyOwner {
        for (uint256 i = 0; i < _tripIds.length; i++) {
            uint256 tripId = _tripIds[i];
            TripGPSData storage trip = trips[tripId];

            if (!trip.pago && trip.valorE1 > 0) {
                trip.pago = true;
                totalPago += uint256(trip.valorE1);
                emit PaymentProcessed(tripId, trip.pseudonimo, trip.valorE1);
            }
        }
    }

    function getTrip(
        uint256 _tripId
    ) external view returns (TripGPSData memory) {
        return trips[_tripId];
    }

    function getTripsByVIN(
        string memory _vin
    ) external view returns (uint256[] memory) {
        return vinToTrips[_vin];
    }

    function getStats()
        external
        view
        returns (uint256 _tripCount, uint256 _totalPago, uint256 _mediaValor)
    {
        _tripCount = tripCount;
        _totalPago = totalPago;
        _mediaValor = tripCount > 0 ? totalPago / tripCount : 0;
    }

    function getPendingPayments() external view returns (uint256[] memory) {
        uint256 pendingCount = 0;

        for (uint256 i = 0; i < tripCount; i++) {
            if (!trips[i].pago && trips[i].valorE1 > 0) {
                pendingCount++;
            }
        }

        uint256[] memory pending = new uint256[](pendingCount);
        uint256 index = 0;

        for (uint256 i = 0; i < tripCount; i++) {
            if (!trips[i].pago && trips[i].valorE1 > 0) {
                pending[index++] = i;
            }
        }

        return pending;
    }

    function setOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "Oracle invalido");
        address oldOracle = oracle;
        oracle = _newOracle;
        emit OracleUpdated(oldOracle, _newOracle);
    }

    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Owner invalido");
        owner = _newOwner;
    }

    /**
     * @dev Retorna apenas as coordenadas GPS de uma viagem (para análise de privacidade)
     */
    function getTripGPS(
        uint256 _tripId
    )
        external
        view
        returns (
            GPSLocation memory startLocation,
            GPSLocation memory endLocation,
            uint256 gpsDistance
        )
    {
        TripGPSData memory trip = trips[_tripId];
        return (trip.startLocation, trip.endLocation, trip.gpsDistance);
    }
}
