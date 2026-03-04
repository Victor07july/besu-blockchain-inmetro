// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title E1MonetizationWithQuality
 * @dev Sistema de monetização de emissões com score de qualidade
 *
 * Registra viagens com:
 * - CO2 bruto calculado
 * - Score de qualidade (0-100)
 * - Multiplicador aplicado (0.2-1.0)
 * - CO2 com crédito ajustado pela qualidade
 *
 * Garante auditabilidade: sempre registra CO2 bruto + penalidade aplicada
 *
 * Autor: Victor
 * Data: 2026-03-03
 */
contract E1MonetizationWithQuality {
    // Estrutura de uma viagem
    struct Trip {
        address user; // Endereço do usuário
        string vehicleId; // Identificador do veículo
        uint256 timestamp; // Timestamp da viagem
        uint256 numPoints; // Número de pontos no trajeto
        uint256 durationSeconds; // Duração em segundos
        uint256 distanceMeters; // Distância em metros (x1000 para precisão)
        uint256 co2RawGrams; // CO2 bruto em gramas (sem qualidade)
        uint8 qualityScore; // Score de qualidade (0-100)
        uint16 qualityMultiplier; // Multiplicador x1000 (ex: 750 = 0.75)
        uint256 co2CreditsGrams; // CO2 final com qualidade aplicada (gramas)
        int32 startLatitude; // Latitude inicial x10^6
        int32 startLongitude; // Longitude inicial x10^6
        int32 endLatitude; // Latitude final x10^6
        int32 endLongitude; // Longitude final x10^6
        bool exists; // Flag de existência
    }

    // Mapeamento de trips
    mapping(uint256 => Trip) public trips;
    uint256 public tripCount;

    // Mapeamento de trips por usuário
    mapping(address => uint256[]) public userTrips;

    // Eventos
    event TripRegistered(
        uint256 indexed tripId,
        address indexed user,
        string vehicleId,
        uint256 co2RawGrams,
        uint8 qualityScore,
        uint256 co2CreditsGrams
    );

    event QualityPenaltyApplied(
        uint256 indexed tripId,
        uint8 qualityScore,
        uint16 qualityMultiplier,
        uint256 penaltyGrams
    );

    /**
     * @dev Registra uma nova viagem com dados de qualidade
     */
    function registerTrip(
        string memory _vehicleId,
        uint256 _numPoints,
        uint256 _durationSeconds,
        uint256 _distanceMeters,
        uint256 _co2RawGrams,
        uint8 _qualityScore,
        uint16 _qualityMultiplier,
        uint256 _co2CreditsGrams,
        int32 _startLat,
        int32 _startLon,
        int32 _endLat,
        int32 _endLon
    ) public returns (uint256) {
        require(_qualityScore <= 100, "Score deve ser 0-100");
        require(
            _qualityMultiplier >= 200 && _qualityMultiplier <= 1000,
            "Multiplicador deve ser 0.2-1.0 (200-1000)"
        );
        require(
            _co2CreditsGrams <= _co2RawGrams,
            "Creditos nao podem exceder CO2 bruto"
        );

        tripCount++;

        trips[tripCount] = Trip({
            user: msg.sender,
            vehicleId: _vehicleId,
            timestamp: block.timestamp,
            numPoints: _numPoints,
            durationSeconds: _durationSeconds,
            distanceMeters: _distanceMeters,
            co2RawGrams: _co2RawGrams,
            qualityScore: _qualityScore,
            qualityMultiplier: _qualityMultiplier,
            co2CreditsGrams: _co2CreditsGrams,
            startLatitude: _startLat,
            startLongitude: _startLon,
            endLatitude: _endLat,
            endLongitude: _endLon,
            exists: true
        });

        userTrips[msg.sender].push(tripCount);

        uint256 penaltyGrams = _co2RawGrams - _co2CreditsGrams;

        emit TripRegistered(
            tripCount,
            msg.sender,
            _vehicleId,
            _co2RawGrams,
            _qualityScore,
            _co2CreditsGrams
        );

        emit QualityPenaltyApplied(
            tripCount,
            _qualityScore,
            _qualityMultiplier,
            penaltyGrams
        );

        return tripCount;
    }

    /**
     * @dev Retorna dados de uma viagem
     */
    function getTrip(
        uint256 _tripId
    )
        public
        view
        returns (
            address user,
            string memory vehicleId,
            uint256 timestamp,
            uint256 distanceMeters,
            uint256 co2RawGrams,
            uint8 qualityScore,
            uint256 co2CreditsGrams
        )
    {
        require(trips[_tripId].exists, "Viagem nao existe");
        Trip memory trip = trips[_tripId];
        return (
            trip.user,
            trip.vehicleId,
            trip.timestamp,
            trip.distanceMeters,
            trip.co2RawGrams,
            trip.qualityScore,
            trip.co2CreditsGrams
        );
    }

    /**
     * @dev Retorna dados de qualidade de uma viagem
     */
    function getTripQuality(
        uint256 _tripId
    )
        public
        view
        returns (
            uint8 qualityScore,
            uint16 qualityMultiplier,
            uint256 co2RawGrams,
            uint256 co2CreditsGrams,
            uint256 penaltyGrams,
            uint8 penaltyPercent
        )
    {
        require(trips[_tripId].exists, "Viagem nao existe");
        Trip memory trip = trips[_tripId];

        uint256 penalty = trip.co2RawGrams - trip.co2CreditsGrams;
        uint8 penaltyPct = uint8((penalty * 100) / trip.co2RawGrams);

        return (
            trip.qualityScore,
            trip.qualityMultiplier,
            trip.co2RawGrams,
            trip.co2CreditsGrams,
            penalty,
            penaltyPct
        );
    }

    /**
     * @dev Retorna coordenadas de uma viagem
     */
    function getTripCoordinates(
        uint256 _tripId
    )
        public
        view
        returns (int32 startLat, int32 startLon, int32 endLat, int32 endLon)
    {
        require(trips[_tripId].exists, "Viagem nao existe");
        Trip memory trip = trips[_tripId];
        return (
            trip.startLatitude,
            trip.startLongitude,
            trip.endLatitude,
            trip.endLongitude
        );
    }

    /**
     * @dev Retorna IDs de todas as viagens de um usuário
     */
    function getUserTrips(
        address _user
    ) public view returns (uint256[] memory) {
        return userTrips[_user];
    }

    /**
     * @dev Retorna total de CO2 (bruto e com qualidade) de um usuário
     */
    function getUserTotalCO2(
        address _user
    )
        public
        view
        returns (
            uint256 totalRawGrams,
            uint256 totalCreditsGrams,
            uint256 totalPenaltyGrams
        )
    {
        uint256[] memory userTripIds = userTrips[_user];

        for (uint256 i = 0; i < userTripIds.length; i++) {
            Trip memory trip = trips[userTripIds[i]];
            totalRawGrams += trip.co2RawGrams;
            totalCreditsGrams += trip.co2CreditsGrams;
        }

        totalPenaltyGrams = totalRawGrams - totalCreditsGrams;

        return (totalRawGrams, totalCreditsGrams, totalPenaltyGrams);
    }

    /**
     * @dev Retorna estatísticas globais
     */
    function getGlobalStats()
        public
        view
        returns (
            uint256 totalTrips,
            uint256 totalRawGrams,
            uint256 totalCreditsGrams,
            uint256 avgQualityScore
        )
    {
        uint256 sumQuality = 0;

        for (uint256 i = 1; i <= tripCount; i++) {
            totalRawGrams += trips[i].co2RawGrams;
            totalCreditsGrams += trips[i].co2CreditsGrams;
            sumQuality += trips[i].qualityScore;
        }

        avgQualityScore = tripCount > 0 ? sumQuality / tripCount : 0;

        return (tripCount, totalRawGrams, totalCreditsGrams, avgQualityScore);
    }
}
