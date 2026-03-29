// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title E1RegistryEuclidean
 * @dev Contrato simplificado para monetização E1 com distância euclidiana
 *
 * Características:
 * - Distância calculada por euclidiana aproximada (Python)
 * - Emissão CO2 calculada por fuel rate + mix combustível (Python)
 * - Monetização comparativa (meta vs real)
 * - GPS com privacidade diferencial
 * - Todos os cálculos pesados feitos off-chain
 */
contract E1RegistryEuclidean {
    struct GPSLocation {
        int256 latitude; // × 1e6
        int256 longitude; // × 1e6
    }

    struct TripData {
        string vin;
        uint256 timestamp;
        uint256 totalDistance; // km × 1e6
        uint256 fuelConsumed; // litros × 1e6
        uint256 co2Real; // kg × 1e6 (emissão real calculada)
        uint256 co2Meta; // kg × 1e6 (meta do fabricante)
        int256 valorE1; // R$ × 1e6 (positivo = crédito, negativo = débito)
        uint256 avgEthanolPercent; // % × 1e3
        GPSLocation startLocation; // Com DP aplicado
        GPSLocation endLocation; // Com DP aplicado
        address pseudonimo;
        bool pago;
    }

    address public owner;
    address public oracle;

    mapping(uint256 => TripData) public trips;
    mapping(string => uint256[]) public vinToTrips;

    uint256 public tripCount;
    uint256 public totalCreditos; // Soma de valores E1 positivos
    uint256 public totalDebitos; // Soma de valores E1 negativos (magnitude)

    event TripRegistered(
        uint256 indexed tripId,
        string vin,
        uint256 totalDistance,
        uint256 co2Real,
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
     * @dev Registra viagem com dados já calculados off-chain
     * Todos os cálculos complexos (distância euclidiana, emissão CO2, monetização)
     * são feitos em Python antes de chamar esta função
     */
    function registerTrip(
        TripData memory data
    ) external onlyOracle returns (uint256) {
        require(data.pseudonimo != address(0), "Pseudonimo invalido");
        require(data.totalDistance > 0, "Distancia deve ser > 0");
        require(data.fuelConsumed > 0, "Combustivel deve ser > 0");
        require(data.co2Real > 0, "CO2 real deve ser > 0");
        require(data.co2Meta > 0, "CO2 meta deve ser > 0");
        require(data.avgEthanolPercent <= 100 * 1e3, "Ethanol <= 100%");

        uint256 tripId = tripCount++;

        // Armazenar dados
        trips[tripId] = data;
        vinToTrips[data.vin].push(tripId);

        // Atualizar estatísticas
        if (data.valorE1 > 0) {
            totalCreditos += uint256(data.valorE1);
        } else if (data.valorE1 < 0) {
            totalDebitos += uint256(-data.valorE1);
        }

        emit TripRegistered(
            tripId,
            data.vin,
            data.totalDistance,
            data.co2Real,
            data.valorE1,
            data.pseudonimo
        );

        return tripId;
    }

    /**
     * @dev Processar pagamento de crédito E1
     */
    function processPayment(uint256 _tripId) external onlyOwner {
        TripData storage trip = trips[_tripId];

        require(!trip.pago, "Ja foi pago");
        require(trip.valorE1 > 0, "Valor deve ser positivo para pagamento");

        trip.pago = true;

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
            TripData storage trip = trips[tripId];

            if (!trip.pago && trip.valorE1 > 0) {
                trip.pago = true;
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
    function getTrip(uint256 tripId) external view returns (TripData memory) {
        return trips[tripId];
    }

    /**
     * @dev Obter estatísticas gerais
     */
    function getStats()
        external
        view
        returns (
            uint256 _tripCount,
            uint256 _totalCreditos,
            uint256 _totalDebitos,
            int256 _saldoLiquido
        )
    {
        _tripCount = tripCount;
        _totalCreditos = totalCreditos;
        _totalDebitos = totalDebitos;
        _saldoLiquido = int256(totalCreditos) - int256(totalDebitos);
    }

    /**
     * @dev Obter estatísticas de um VIN específico
     */
    function getVinStats(
        string memory vin
    )
        external
        view
        returns (
            uint256 numTrips,
            uint256 totalDistanceVin,
            uint256 totalCO2Real,
            int256 saldoE1
        )
    {
        uint256[] memory tripIds = vinToTrips[vin];
        numTrips = tripIds.length;

        for (uint256 i = 0; i < tripIds.length; i++) {
            TripData memory trip = trips[tripIds[i]];
            totalDistanceVin += trip.totalDistance;
            totalCO2Real += trip.co2Real;
            saldoE1 += trip.valorE1;
        }
    }
}
