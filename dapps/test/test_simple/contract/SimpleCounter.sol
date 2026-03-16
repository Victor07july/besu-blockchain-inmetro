// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title SimpleCounter
 * @dev Contrato minimalista para teste de performance da blockchain
 *
 * Este contrato recebe os mesmos parâmetros do CarbonCreditNFT_E1,
 * mas ao invés de executar cálculos complexos, apenas incrementa
 * um contador e retorna valores fixos.
 *
 * Objetivo: Isolar o tempo de confirmação da blockchain do tempo
 * de processamento do algoritmo de monetização.
 */
contract SimpleCounter {
    // === ESTRUTURA DE DADOS (igual ao contrato original) ===
    struct VehicleData {
        uint256 distanceHighway;
        uint256 distanceCity;
        uint256 cityGasoline;
        uint256 roadGasoline;
        uint256 cityEthanol;
        uint256 roadEthanol;
        uint256 carbonPriceEuropean;
        uint256 euroPrice;
    }

    // === ESTADO DO CONTRATO ===
    uint256 public counter;
    mapping(uint256 => VehicleData) public records;

    // === EVENTO ===
    event E1Calculated(
        address indexed user,
        uint256 indexed recordId,
        uint256 metaCO2,
        uint256 diff,
        uint256 e1Value,
        uint256 timestamp
    );

    // === CONSTRUTOR ===
    constructor() {
        counter = 0;
    }

    /**
     * @dev Função principal - recebe dados mas apenas incrementa contador
     * @param data Dados do veículo (mesma estrutura do contrato original)
     * @return recordId ID sequencial do registro
     * @return metaCO2 Valor fixo de teste (1000)
     * @return diff Valor fixo de teste (500)
     * @return e1Value Valor fixo de teste (100)
     */
    function calculateAndRecordE1(
        VehicleData memory data
    )
        external
        returns (
            uint256 recordId,
            uint256 metaCO2,
            uint256 diff,
            uint256 e1Value
        )
    {
        // Incrementa contador
        counter++;
        recordId = counter;

        // Armazena dados (para manter estado similar ao contrato original)
        records[recordId] = data;

        // Valores fixos de retorno (sem cálculos complexos)
        metaCO2 = 1000 * 1e6; // 1000 kg CO2
        diff = 500 * 1e6; // 500 kg economia
        e1Value = 100 * 1e6; // R$ 100

        // Emite evento (para compatibilidade com logs)
        emit E1Calculated(
            msg.sender,
            recordId,
            metaCO2,
            diff,
            e1Value,
            block.timestamp
        );

        return (recordId, metaCO2, diff, e1Value);
    }

    /**
     * @dev Função para consultar um registro
     * @param recordId ID do registro
     * @return data Dados armazenados
     */
    function getRecord(
        uint256 recordId
    ) external view returns (VehicleData memory data) {
        return records[recordId];
    }

    /**
     * @dev Retorna o total de registros
     * @return total Número total de registros
     */
    function getTotalRecords() external view returns (uint256 total) {
        return counter;
    }
}
