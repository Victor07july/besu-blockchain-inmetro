// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title E1WithQuality
 * @dev Monetização de emissões com score de qualidade integrado
 *
 * Registra viagens com:
 * - CO2 bruto (sem penalidade)
 * - Score de qualidade (0-100)
 * - Multiplicador (0.2-1.0)
 * - CO2 créditos (com penalidade aplicada)
 *
 * Garante auditabilidade total
 */
contract E1WithQuality {
    struct Trip {
        address user;
        string vehicleId;
        uint256 timestamp;
        uint256 numPoints;
        uint256 distanceMeters; // Distância em metros (x1000 para precisão)
        uint256 co2RawGrams; // CO2 bruto em gramas
        uint8 qualityScore; // Score 0-100
        uint16 qualityMultiplier; // Multiplicador x1000 (ex: 750 = 0.75)
        uint256 co2CreditsGrams; // CO2 com qualidade aplicada
        int32 startLatPrivate; // Lat inicial privada x10^6
        int32 startLonPrivate; // Lon inicial privada x10^6
        int32 endLatPrivate; // Lat final privada x10^6
        int32 endLonPrivate; // Lon final privada x10^6
    }

    mapping(uint256 => Trip) public trips;
    uint256 public tripCount;
    mapping(address => uint256[]) public userTrips;

    event TripRegistered(
        uint256 indexed tripId,
        address indexed user,
        string vehicleId,
        uint256 co2RawGrams,
        uint8 qualityScore,
        uint256 co2CreditsGrams
    );

    /**
     * @dev Registra nova viagem com qualidade
     */
    function registerTrip(
        string memory _vehicleId,
        uint256 _numPoints,
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
        require(_qualityScore <= 100, "Score 0-100");
        require(
            _qualityMultiplier >= 200 && _qualityMultiplier <= 1000,
            "Mult 0.2-1.0"
        );
        require(_co2CreditsGrams <= _co2RawGrams, "Credits <= Raw");

        tripCount++;

        trips[tripCount] = Trip({
            user: msg.sender,
            vehicleId: _vehicleId,
            timestamp: block.timestamp,
            numPoints: _numPoints,
            distanceMeters: _distanceMeters,
            co2RawGrams: _co2RawGrams,
            qualityScore: _qualityScore,
            qualityMultiplier: _qualityMultiplier,
            co2CreditsGrams: _co2CreditsGrams,
            startLatPrivate: _startLat,
            startLonPrivate: _startLon,
            endLatPrivate: _endLat,
            endLonPrivate: _endLon
        });

        userTrips[msg.sender].push(tripCount);

        emit TripRegistered(
            tripCount,
            msg.sender,
            _vehicleId,
            _co2RawGrams,
            _qualityScore,
            _co2CreditsGrams
        );

        return tripCount;
    }

    /**
     * @dev Retorna dados de viagem
     */
    function getTrip(
        uint256 _tripId
    )
        public
        view
        returns (
            address user,
            string memory vehicleId,
            uint256 co2RawGrams,
            uint8 qualityScore,
            uint256 co2CreditsGrams
        )
    {
        Trip memory trip = trips[_tripId];
        return (
            trip.user,
            trip.vehicleId,
            trip.co2RawGrams,
            trip.qualityScore,
            trip.co2CreditsGrams
        );
    }

    /**
     * @dev Retorna total de CO2 de usuário
     */
    function getUserTotal(
        address _user
    )
        public
        view
        returns (uint256 totalRaw, uint256 totalCredits, uint256 penalty)
    {
        uint256[] memory ids = userTrips[_user];

        for (uint256 i = 0; i < ids.length; i++) {
            totalRaw += trips[ids[i]].co2RawGrams;
            totalCredits += trips[ids[i]].co2CreditsGrams;
        }

        penalty = totalRaw - totalCredits;
    }
}
