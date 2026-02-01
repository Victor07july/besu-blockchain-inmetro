// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract E1Registry {
    struct TripParams {
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
    }

    struct TripData {
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
    }

    address public owner;
    address public oracle;

    mapping(uint256 => TripData) public trips;
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

    function registerTrip(
        TripParams memory params
    ) external onlyOracle returns (uint256) {
        require(params.pseudonimo != address(0), "Pseudonimo invalido");
        require(params.roadGasoline > 0, "Road gasoline > 0");
        require(params.roadEthanol > 0, "Road ethanol > 0");
        require(params.cityGasoline > 0, "City gasoline > 0");
        require(params.cityEthanol > 0, "City ethanol > 0");
        require(params.ethanolPercent <= 100 * 1e6, "Ethanol <= 100%");
        require(params.carbonPrice > 0, "Carbon price > 0");

        (uint256 metaCO2, int256 diff, int256 valorE1) = _calculateE1(params);

        uint256 tripId = tripCount++;
        uint256 totalDistance = params.highwayDistance + params.cityDistance;

        trips[tripId] = TripData({
            vin: params.vin,
            timestamp: params.timestamp,
            totalDistance: totalDistance,
            emissaoReal: params.emissaoReal,
            metaCO2: metaCO2,
            diff: diff,
            realPrice: params.carbonPrice,
            valorE1: valorE1,
            pseudonimo: params.pseudonimo,
            pago: false
        });

        vinToTrips[params.vin].push(tripId);

        emit TripRegistered(
            tripId,
            params.vin,
            metaCO2,
            diff,
            valorE1,
            params.pseudonimo
        );

        return tripId;
    }

    function _calculateE1(
        TripParams memory params
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

        if (metaCO2 >= params.emissaoReal) {
            diff = int256(metaCO2 - params.emissaoReal);
        } else {
            diff = -int256(params.emissaoReal - metaCO2);
        }

        valorE1 = (diff * int256(params.carbonPrice)) / int256(1_000_000 * 1e6);

        return (metaCO2, diff, valorE1);
    }

    function processPayment(uint256 _tripId) external onlyOwner {
        TripData storage trip = trips[_tripId];

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
            TripData storage trip = trips[tripId];

            if (!trip.pago && trip.valorE1 > 0) {
                trip.pago = true;
                totalPago += uint256(trip.valorE1);
                emit PaymentProcessed(tripId, trip.pseudonimo, trip.valorE1);
            }
        }
    }

    function getTrip(uint256 _tripId) external view returns (TripData memory) {
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
}
