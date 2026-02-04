// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title E1Registry
 * @dev Registro de monetização E1 - Mercado Europeu de Carbono
 *
 * Fórmula E1: Compara emissão real vs. meta do fabricante
 * - Meta_CO2: Baseada em consumo declarado (km/l) pelo fabricante
 * - Diff: Meta_CO2 - Emissão_Real
 * - Valor: Diff × Preço_Carbono_Europeu
 *
 * Privacidade: Usa pseudônimos HD para pagamentos
 */
contract E1Registry {
    // ============================================================
    //                         ESTRUTURAS
    // ============================================================

    struct TripData {
        string vin; // Vehicle Identification Number
        uint256 timestamp; // Data da viagem
        uint256 totalDistance; // Distância total (metros)
        uint256 emissaoReal; // Emissão real medida (gramas CO2)
        uint256 metaCO2; // Meta baseada no fabricante (gramas CO2)
        int256 diff; // Meta - Real (pode ser negativo)
        uint256 realPrice; // Preço carbono europeu (R$ × 10^6)
        int256 valorE1; // Valor final E1 (R$ × 10^6, pode ser negativo)
        address pseudonimo; // Endereço pseudônimo para pagamento
        bool pago; // Se já foi pago
    }

    // ============================================================
    //                          STORAGE
    // ============================================================

    address public owner;
    address public oracle; // Quem pode enviar dados

    mapping(uint256 => TripData) public trips; // tripId => TripData
    mapping(string => uint256[]) public vinToTrips; // VIN => lista de tripIds

    uint256 public tripCount;
    uint256 public totalPago; // Total pago em R$ × 10^6

    // ============================================================
    //                          EVENTOS
    // ============================================================

    event TripRegistered(
        uint256 indexed tripId,
        string vin,
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

    // ============================================================
    //                        MODIFICADORES
    // ============================================================

    modifier onlyOwner() {
        require(msg.sender == owner, "Apenas owner");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == oracle, "Apenas oracle");
        _;
    }

    // ============================================================
    //                        CONSTRUTOR
    // ============================================================

    constructor() {
        owner = msg.sender;
        oracle = msg.sender;
    }

    // ============================================================
    //                    FUNÇÕES PRINCIPAIS
    // ============================================================

    /**
     * @dev Registra uma viagem com dados E1
     * @param _vin Vehicle Identification Number
     * @param _timestamp Data da viagem (Unix timestamp)
     * @param _totalDistance Distância total em metros
     * @param _emissaoReal Emissão real medida (gramas × 10^3)
     * @param _metaCO2 Meta do fabricante (gramas × 10^3)
     * @param _diff Diferença Meta - Real (gramas × 10^3, pode ser negativo)
     * @param _realPrice Preço carbono europeu (R$ × 10^6 por tonelada)
     * @param _valorE1 Valor final E1 (R$ × 10^6, pode ser negativo)
     * @param _pseudonimo Endereço pseudônimo HD para pagamento
     */
    function registerTrip(
        string memory _vin,
        uint256 _timestamp,
        uint256 _totalDistance,
        uint256 _emissaoReal,
        uint256 _metaCO2,
        int256 _diff,
        uint256 _realPrice,
        int256 _valorE1,
        address _pseudonimo
    ) external onlyOracle returns (uint256) {
        require(_pseudonimo != address(0), "Pseudonimo invalido");

        uint256 tripId = tripCount++;

        trips[tripId] = TripData({
            vin: _vin,
            timestamp: _timestamp,
            totalDistance: _totalDistance,
            emissaoReal: _emissaoReal,
            metaCO2: _metaCO2,
            diff: _diff,
            realPrice: _realPrice,
            valorE1: _valorE1,
            pseudonimo: _pseudonimo,
            pago: false
        });

        vinToTrips[_vin].push(tripId);

        emit TripRegistered(tripId, _vin, _diff, _valorE1, _pseudonimo);

        return tripId;
    }

    /**
     * @dev Processa pagamento para um pseudônimo
     * Apenas valores positivos são pagos (economia de CO2)
     */
    function processPayment(uint256 _tripId) external onlyOwner {
        TripData storage trip = trips[_tripId];

        require(!trip.pago, "Ja foi pago");
        require(trip.valorE1 > 0, "Valor deve ser positivo");

        trip.pago = true;
        totalPago += uint256(trip.valorE1);

        // Aqui seria integrado com sistema de pagamento real
        // Por enquanto apenas registra o evento

        emit PaymentProcessed(_tripId, trip.pseudonimo, trip.valorE1);
    }

    /**
     * @dev Processa pagamentos em lote
     */
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

    // ============================================================
    //                    FUNÇÕES DE CONSULTA
    // ============================================================

    /**
     * @dev Retorna dados de uma viagem
     */
    function getTrip(uint256 _tripId) external view returns (TripData memory) {
        return trips[_tripId];
    }

    /**
     * @dev Retorna todas as viagens de um VIN
     */
    function getTripsByVIN(
        string memory _vin
    ) external view returns (uint256[] memory) {
        return vinToTrips[_vin];
    }

    /**
     * @dev Retorna estatísticas gerais
     */
    function getStats()
        external
        view
        returns (uint256 _tripCount, uint256 _totalPago, uint256 _mediaValor)
    {
        _tripCount = tripCount;
        _totalPago = totalPago;
        _mediaValor = tripCount > 0 ? totalPago / tripCount : 0;
    }

    /**
     * @dev Retorna viagens pendentes de pagamento
     */
    function getPendingPayments() external view returns (uint256[] memory) {
        uint256 pendingCount = 0;

        // Primeiro contar quantas pendentes
        for (uint256 i = 0; i < tripCount; i++) {
            if (!trips[i].pago && trips[i].valorE1 > 0) {
                pendingCount++;
            }
        }

        // Criar array e preencher
        uint256[] memory pending = new uint256[](pendingCount);
        uint256 index = 0;

        for (uint256 i = 0; i < tripCount; i++) {
            if (!trips[i].pago && trips[i].valorE1 > 0) {
                pending[index++] = i;
            }
        }

        return pending;
    }

    // ============================================================
    //                    FUNÇÕES ADMINISTRATIVAS
    // ============================================================

    /**
     * @dev Atualiza endereço do oracle
     */
    function setOracle(address _newOracle) external onlyOwner {
        require(_newOracle != address(0), "Oracle invalido");
        address oldOracle = oracle;
        oracle = _newOracle;
        emit OracleUpdated(oldOracle, _newOracle);
    }

    /**
     * @dev Transfere ownership
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Owner invalido");
        owner = _newOwner;
    }
}
