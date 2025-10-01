/*
 * SPDX-License-Identifier: Apache-2.0
 */

package chaincode

import (
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"strconv"

	"github.com/hyperledger/fabric-contract-api-go/v2/contractapi"
)

// ==================================================
// Verificar variaveis de struct que entram como chave privada
// ==================================================

// Define prefixes for state management

// Nomes para serem usados como chaves no estado do contrato
const nameKey = "name"
const symbolKey = "symbol"

// ContractState represents the contract's global state
type ContractState struct {
	CarbonPriceEUR    float64 `json:"carbonPricePerG"`
	PrecoCentavosPorG float64 `json:"precoCentavosPorG"`
	CotacaoEthEmReais float64 `json:"cotacaoEthEmReais"`
	NextTokenId       uint64  `json:"nextTokenId"`
	CotacaoEuroBRL    float64 `json:"cotacaoEuro"` // Adicionando cotação do euro
}

// ViagemDetalhada represents detailed trip information
type ViagemDetalhada struct {
	TokenID          string `json:"tokenId"`
	Condutor         string `json:"condutor"`
	Co2MetaG         string `json:"co2MetaG"`
	EconomiaCO2      string `json:"economiaCO2"`
	Recompensa       string `json:"recompensa"`
	DadosHash        string `json:"dadosHash"`
	RecompensaSacada bool   `json:"recompensaSacada"`
}

type StatusRecompensa struct {
	Condutor string `json:"condutor"` // Condutor provavelmente será alguma chave privada do usuário
	TokenId  string `json:"tokenId"`
	Sacada   bool   `json:"sacada"`
	Valor    uint64 `json:"valor"` // Valor da recompensa em wei
}

type Carteira struct {
	Condutor string `json:"condutor"` // Condutor provavelmente será alguma chave privada do usuário
	Saldo    uint64 `json:"saldo"`    // Saldo da carteira em wei
}

// DadosCarbonizacao represents vehicle emission data for CO2 calculation
type DadosCarbonizacao struct {
	TokenID           string  `json:"tokenId"`
	VehicleID         string  `json:"vehicleId"`
	Condutor          string  `json:"condutor"`
	HighwayDistance   float64 `json:"highway_distance"`
	CityDistance      float64 `json:"city_distance"`
	EthanolPercent    float64 `json:"ethanol_percent"`
	CO2EtanolOriginal float64 `json:"co2_etanol_original"`
	RoadGasoline      float64 `json:"road_gasoline"`
	RoadEthanol       float64 `json:"road_ethanol"`
	CityGasoline      float64 `json:"city_gasoline"`
	CityEthanol       float64 `json:"city_ethanol"`
	TanqueGasoline    float64 `json:"tanque_gasoline"`
	RealPrice         float64 `json:"real_price"`
	MetaCO2           float64 `json:"meta_co2"`
	Diff              float64 `json:"diff"`     // E1 calculation (CO2 saved/difference)
	E2Value           float64 `json:"e2_value"` // Monetization value
	// CarbonPriceEUR    float64 `json:"carbon_price_eur"`  // Carbon price in EUR
	// EURBRLRate        float64 `json:"eur_brl_rate"`      // EUR/BRL exchange rate
	RecompensaEmWei uint64 `json:"recompensa_em_wei"` // Final reward in wei
	Timestamp       string `json:"timestamp"`
}



// ======================================
// TOKENIZAÇÃO DE CRÉDITOS DE CARBONO
// ======================================

// CalculateE1AndTokenize calcula o E1 (economia de CO2) e cria um NFT com os créditos de carbono
func (s *SmartContract) CalculateE1AndTokenize(ctx contractapi.TransactionContextInterface,
	vehicleId string,
	condutor string,
	highwayDistance string,
	cityDistance string,
	ethanolPercent string,
	co2EtanolOriginal string,
	roadGasoline string,
	roadEthanol string,
	cityGasoline string,
	cityEthanol string,
	tanqueGasoline string,
	// carbonPriceEUR string,
	// eurBrlRate string,
	timestamp string,
) (string, error) {

	// Verificar autorização
	clientMSPID, err := ctx.GetClientIdentity().GetMSPID()
	if err != nil {
		return "", fmt.Errorf("failed to get clientMSPID: %v", err)
	}

	if clientMSPID != "INMETROMSP" {
		return "", errors.New("client is not authorized to tokenize carbon credits")
	}

	// Verificar se o contrato está inicializado
	contractStateBytes, err := ctx.GetStub().GetState("contractState")
	if err != nil {
		return "", fmt.Errorf("failed to get contract state: %v", err)
	}
	if contractStateBytes == nil {
		return "", errors.New("contract not initialized")
	}

	var contractState ContractState
	err = json.Unmarshal(contractStateBytes, &contractState)
	if err != nil {
		return "", fmt.Errorf("failed to unmarshal contract state: %v", err)
	}

	// Obtem eur e cotacao do contractState
	carbonPrice := float64(contractState.CarbonPriceEUR)
	eurBrl := float64(contractState.CotacaoEuroBRL)

	// Converter parâmetros string para float64
	hwDistance := toNumeric(highwayDistance)
	ctDistance := toNumeric(cityDistance)
	ethPercent := toNumeric(ethanolPercent)
	co2Original := toNumeric(co2EtanolOriginal)
	roadGas := toNumeric(roadGasoline)
	roadEth := toNumeric(roadEthanol)
	cityGas := toNumeric(cityGasoline)
	cityEth := toNumeric(cityEthanol)
	tanqueGas := toNumeric(tanqueGasoline)

	// CÁLCULO DO CO2 META (baseado na lógica do CalculateMonetization)

	// PARTE 1 - Highway calculations
	parte_1_1 := hwDistance * ((1 / roadGas) * (tanqueGas / 100) * 1.720) * 1000
	parte_1_2 := hwDistance * ((1 / roadEth) * (ethPercent / 100) * 1.510) * 1000

	// Replace NaN and Inf values with 0
	parte_1_1 = replaceInfAndNaN(parte_1_1)
	parte_1_2 = replaceInfAndNaN(parte_1_2)

	parte_1 := parte_1_1 + parte_1_2

	// PARTE 2 - City calculations
	parte_2_1 := ctDistance * ((1 / cityGas) * (tanqueGas / 100) * 1.720) * 1000
	parte_2_2 := ctDistance * ((1 / cityEth) * (ethPercent / 100) * 1.510) * 1000

	// Replace NaN and Inf values with 0
	parte_2_1 = replaceInfAndNaN(parte_2_1)
	parte_2_2 = replaceInfAndNaN(parte_2_2)

	parte_2 := parte_2_1 + parte_2_2

	// META CO2 calculation
	metaCO2 := parte_1 + parte_2

	// DIFERENÇA (E1) = META CO2 - EMISSÃO REAL
	// Se positivo = economia de CO2, se negativo = excesso de emissão
	diff := metaCO2 - co2Original

	// Calcular valor monetário em BRL
	realPrice := carbonPrice * eurBrl
	e2Value := diff * realPrice / 1000000

	// Somente criar NFT se houve economia de CO2 (diff > 0)
	if diff <= 0 {
		return "", fmt.Errorf("no carbon savings detected: actual emission (%.2f) >= target emission (%.2f)", co2Original, metaCO2)
	}

	// Gerar token ID
	tokenId := strconv.FormatUint(contractState.NextTokenId, 10)
	contractState.NextTokenId++

	// Verificar se o token já existe
	exists := _nftExists(ctx, tokenId)
	if exists {
		return "", fmt.Errorf("the token %s is already minted", tokenId)
	}

	// Calcular recompensa em wei usando o valor E2
	// E2 é o valor monetário da economia de CO2, convertido para wei (1 ETH = 1e18 wei)
	recompensaEmWei := uint64(e2Value * 1e18)

	// Criar NFT
	nft := new(Nft)
	nft.TokenId = tokenId
	nft.Owner = condutor
	nft.TokenURI = fmt.Sprintf(
		`{"vehicleId":"%s","co2Economy":"%.2f","metaCO2":"%.2f","originalCO2":"%.2f","recompensaEmWei":"%d","carbonPriceEUR":"%.2f","eurBrlRate":"%.2f"}`,
		vehicleId, diff, metaCO2, co2Original, recompensaEmWei, carbonPrice, eurBrl,
	)

	nftKey, err := ctx.GetStub().CreateCompositeKey(nftPrefix, []string{condutor, tokenId})
	if err != nil {
		return "", fmt.Errorf("failed to CreateCompositeKey to nftKey: %v", err)
	}

	nftBytes, err := json.Marshal(nft)
	if err != nil {
		return "", fmt.Errorf("failed to marshal nft: %v", err)
	}

	err = ctx.GetStub().PutState(nftKey, nftBytes)
	if err != nil {
		return "", fmt.Errorf("failed to PutState nftBytes: %v", err)
	}

	// Criar struct da recompensa
	recompensa := StatusRecompensa{
		TokenId:  tokenId,
		Sacada:   false,
		Condutor: condutor,
		Valor:    recompensaEmWei,
	}

	// Salvar status da recompensa
	recompensaBytes, err := json.Marshal(recompensa)
	if err != nil {
		return "", fmt.Errorf("failed to marshal reward status: %v", err)
	}

	recompensaKey, err := ctx.GetStub().CreateCompositeKey("recompensa", []string{condutor, tokenId})
	if err != nil {
		return "", fmt.Errorf("failed to CreateCompositeKey for recompensaKey: %v", err)
	}

	err = ctx.GetStub().PutState(recompensaKey, recompensaBytes)
	if err != nil {
		return "", fmt.Errorf("failed to PutState recompensaBytes: %v", err)
	}

	// Salvar dados detalhados da carbonização
	dadosCarbonizacao := DadosCarbonizacao{
		TokenID:           tokenId,
		VehicleID:         vehicleId,
		Condutor:          condutor,
		HighwayDistance:   hwDistance,
		CityDistance:      ctDistance,
		EthanolPercent:    ethPercent,
		CO2EtanolOriginal: co2Original,
		RoadGasoline:      roadGas,
		RoadEthanol:       roadEth,
		CityGasoline:      cityGas,
		CityEthanol:       cityEth,
		TanqueGasoline:    tanqueGas,
		RealPrice:         realPrice,
		MetaCO2:           metaCO2,
		Diff:              diff,
		E2Value:           e2Value,
		// CarbonPriceEUR:    carbonPrice,
		// EURBRLRate:        eurBrl,
		RecompensaEmWei: recompensaEmWei,
		Timestamp:       timestamp,
	}

	carbonizacaoBytes, err := json.Marshal(dadosCarbonizacao)
	if err != nil {
		return "", fmt.Errorf("failed to marshal carbonization data: %v", err)
	}

	carbonizacaoKey, err := ctx.GetStub().CreateCompositeKey("carbonizacao", []string{tokenId})
	if err != nil {
		return "", fmt.Errorf("failed to CreateCompositeKey for carbonizacaoKey: %v", err)
	}

	err = ctx.GetStub().PutState(carbonizacaoKey, carbonizacaoBytes)
	if err != nil {
		return "", fmt.Errorf("failed to PutState carbonizacaoBytes: %v", err)
	}

	// Atualizar estado do contrato
	contractStateBytes, err = json.Marshal(contractState)
	if err != nil {
		return "", fmt.Errorf("failed to marshal updated contract state: %v", err)
	}

	err = ctx.GetStub().PutState("contractState", contractStateBytes)
	if err != nil {
		return "", fmt.Errorf("failed to save updated contract state: %v", err)
	}

	// Emitir evento de tokenização
	eventoTokenizacao := map[string]interface{}{
		"tokenId":        tokenId,
		"condutor":       condutor,
		"vehicleId":      vehicleId,
		"co2Economy":     diff,
		"recompensaWei":  recompensaEmWei,
		"carbonPriceEUR": carbonPrice,
		"eurBrlRate":     eurBrl,
		"timestamp":      timestamp,
	}

	eventoBytes, _ := json.Marshal(eventoTokenizacao)
	ctx.GetStub().SetEvent("CarbonCreditTokenized", eventoBytes)

	return tokenId, nil
}
