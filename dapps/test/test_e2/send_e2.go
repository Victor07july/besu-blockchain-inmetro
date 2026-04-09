package main

import (
	"context"
	"crypto/ecdsa"
	"crypto/tls"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math/big"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/ethereum/go-ethereum/accounts/abi"
	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/core/types"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/ethclient"
	"github.com/ethereum/go-ethereum/rpc"
)

// ======================================================================
// CONFIGURAÇÕES
// ======================================================================

const (
	RPCURL         = "https://ec2-18-117-120-52.us-east-2.compute.amazonaws.com/user/"
	DeploymentJSON = "./e2_deployment.json"
	WalletsJSON    = "./wallets_64_groups.json"
	DataCSV        = "./dados_gas.csv"
	NumWorkers     = 8192 // Número de workers paralelosz
	TotalRows      = 100  // Total de linhas a processar (cicla o CSV se necessário)
	TxTimeout      = 120 * time.Second
)

// ======================================================================
// ESTRUTURAS
// ======================================================================

type Wallet struct {
	Address    string `json:"address"`
	PrivateKey string `json:"private_key"`
}

// CalculationParams espelha o struct Solidity do contrato E2
// Todos os valores são inteiros escalados por 1e6
type CalculationParams struct {
	HighwayDistance    *big.Int // km * 1e6
	CityDistance       *big.Int // km * 1e6
	EthanolPercent     *big.Int // % (0-100) * 1e6
	RoadGasoline       *big.Int // km/L * 1e6
	RoadEthanol        *big.Int // km/L * 1e6
	CityGasoline       *big.Int // km/L * 1e6
	CityEthanol        *big.Int // km/L * 1e6
	PrecoGasolina      *big.Int // BRL/L * 1e6
	PrecoEtanol        *big.Int // BRL/L * 1e6
	BehaviorCautious   *big.Int // % * 1e6
	BehaviorNormal     *big.Int // % * 1e6
	BehaviorAggressive *big.Int // % * 1e6
}

type DeploymentData struct {
	ContractAddress string          `json:"contract_address"`
	ABI             json.RawMessage `json:"abi"`
	GasUsed         uint64          `json:"gas_used"`
}

type CSVRow struct {
	HighwayDistance    float64
	CityDistance       float64
	EthanolPercent     float64
	RoadGasoline       float64
	RoadEthanol        float64
	CityGasoline       float64
	CityEthanol        float64
	PrecoGasolina      float64
	PrecoEtanol        float64
	BehaviorCautious   float64
	BehaviorNormal     float64
	BehaviorAggressive float64
}

type Result struct {
	Linha         int
	WorkerID      int
	WalletAddr    string
	TxHash        string
	Block         uint64
	GasUsed       uint64
	Error         error
	StartTime     time.Time
	TxSentTime    time.Time
	ConfirmedTime time.Time
	Latency       time.Duration
}

type WorkerStats struct {
	WorkerID      int
	TotalTxs      int
	SuccessfulTxs int
	FailedTxs     int
	TotalLatency  time.Duration
	AvgLatency    time.Duration
	MinLatency    time.Duration
	MaxLatency    time.Duration
	StartTime     time.Time
	EndTime       time.Time
	Duration      time.Duration
}

// ======================================================================
// FUNÇÕES AUXILIARES
// ======================================================================

// toInt converte um float64 para *big.Int escalado por 1e6, com clamp mínimo
func toInt(val float64) *big.Int {
	if val < 0 {
		val = 0
	}
	if val > 1e12 {
		val = 1e12
	}
	return big.NewInt(int64(val * 1e6))
}

func prepareCalculationParams(row CSVRow) CalculationParams {
	// Valores padrão para campos ausentes no CSV
	// Consumos típicos de veículos flex brasileiros (INMETRO)
	if row.RoadGasoline == 0 {
		row.RoadGasoline = 14.0 // km/L rodovia gasolina
	}
	if row.RoadEthanol == 0 {
		row.RoadEthanol = 10.0 // km/L rodovia etanol
	}
	if row.CityGasoline == 0 {
		row.CityGasoline = 12.0 // km/L cidade gasolina
	}
	if row.CityEthanol == 0 {
		row.CityEthanol = 8.0 // km/L cidade etanol
	}
	if row.PrecoGasolina == 0 {
		row.PrecoGasolina = 6.0 // BRL/L fallback
	}
	if row.PrecoEtanol == 0 {
		row.PrecoEtanol = 4.2 // BRL/L fallback
	}

	return CalculationParams{
		HighwayDistance:    toInt(row.HighwayDistance),
		CityDistance:       toInt(row.CityDistance),
		EthanolPercent:     toInt(row.EthanolPercent),
		RoadGasoline:       toInt(row.RoadGasoline),
		RoadEthanol:        toInt(row.RoadEthanol),
		CityGasoline:       toInt(row.CityGasoline),
		CityEthanol:        toInt(row.CityEthanol),
		PrecoGasolina:      toInt(row.PrecoGasolina),
		PrecoEtanol:        toInt(row.PrecoEtanol),
		BehaviorCautious:   toInt(row.BehaviorCautious),
		BehaviorNormal:     toInt(row.BehaviorNormal),
		BehaviorAggressive: toInt(row.BehaviorAggressive),
	}
}

func loadDeploymentData() (*DeploymentData, error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	filePath := filepath.Join(dir, DeploymentJSON)
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var deployment DeploymentData
	err = json.Unmarshal(data, &deployment)
	if err != nil {
		return nil, err
	}

	return &deployment, nil
}

func loadWallets(numWallets int) ([]Wallet, error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, err
	}

	filePath := filepath.Join(dir, WalletsJSON)
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	var walletsMap map[string]Wallet
	err = json.Unmarshal(data, &walletsMap)
	if err != nil {
		return nil, err
	}

	var wallets []Wallet
	for i := 1; i <= numWallets && i <= len(walletsMap); i++ {
		key := fmt.Sprintf("vehicle_group_%d", i)
		if w, ok := walletsMap[key]; ok {
			wallets = append(wallets, w)
		}
	}

	if len(wallets) < numWallets {
		return nil, fmt.Errorf("número insuficiente de wallets: encontrado %d, necessário %d", len(wallets), numWallets)
	}

	return wallets, nil
}

func readCSV(filename string) ([]CSVRow, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)

	header, err := reader.Read()
	if err != nil {
		return nil, err
	}

	colMap := make(map[string]int)
	for i, col := range header {
		colMap[strings.TrimSpace(col)] = i
	}

	var rows []CSVRow
	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		parseFloat := func(colName string) float64 {
			if idx, ok := colMap[colName]; ok && idx < len(record) {
				val, _ := strconv.ParseFloat(strings.TrimSpace(record[idx]), 64)
				return val
			}
			return 0
		}

		row := CSVRow{
			HighwayDistance:    parseFloat("highway (distance)"),
			CityDistance:       parseFloat("city (distance)"),
			EthanolPercent:     parseFloat("ethanol (%)"),
			RoadGasoline:       parseFloat("road (gasoline)"),
			RoadEthanol:        parseFloat("road (ethanol)"),
			CityGasoline:       parseFloat("city (gasoline)"),
			CityEthanol:        parseFloat("city (ethanol)"),
			PrecoGasolina:      parseFloat("preco_gasolina"),
			PrecoEtanol:        parseFloat("preco_etanol"),
			BehaviorCautious:   parseFloat("behavior_cautious (%)"),
			BehaviorNormal:     parseFloat("behavior_normal (%)"),
			BehaviorAggressive: parseFloat("behavior_aggressive (%)"),
		}
		rows = append(rows, row)
	}

	return rows, nil
}

// expandRows cicla o slice base até atingir total linhas
func expandRows(base []CSVRow, total int) []CSVRow {
	if len(base) == 0 {
		return base
	}
	expanded := make([]CSVRow, total)
	for i := 0; i < total; i++ {
		expanded[i] = base[i%len(base)]
	}
	return expanded
}

func saveResults(results []Result, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	writer.Write([]string{
		"linha", "worker_id", "wallet_addr", "tx_hash", "block", "gas_used",
		"latency_ms", "error",
	})

	for _, r := range results {
		errStr := ""
		if r.Error != nil {
			errStr = r.Error.Error()
		}

		writer.Write([]string{
			fmt.Sprintf("%d", r.Linha),
			fmt.Sprintf("%d", r.WorkerID),
			r.WalletAddr,
			r.TxHash,
			fmt.Sprintf("%d", r.Block),
			fmt.Sprintf("%d", r.GasUsed),
			fmt.Sprintf("%.2f", r.Latency.Seconds()*1000),
			errStr,
		})
	}

	return nil
}

func saveWorkerStats(stats []WorkerStats, filename string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	writer.Write([]string{
		"worker_id", "total_txs", "successful_txs", "failed_txs",
		"duration_s", "avg_latency_ms", "min_latency_ms", "max_latency_ms",
		"throughput_tx_s",
	})

	for _, s := range stats {
		throughput := 0.0
		if s.Duration.Seconds() > 0 {
			throughput = float64(s.SuccessfulTxs) / s.Duration.Seconds()
		}

		writer.Write([]string{
			fmt.Sprintf("%d", s.WorkerID),
			fmt.Sprintf("%d", s.TotalTxs),
			fmt.Sprintf("%d", s.SuccessfulTxs),
			fmt.Sprintf("%d", s.FailedTxs),
			fmt.Sprintf("%.2f", s.Duration.Seconds()),
			fmt.Sprintf("%.2f", s.AvgLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", s.MinLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", s.MaxLatency.Seconds()*1000),
			fmt.Sprintf("%.2f", throughput),
		})
	}

	return nil
}

func waitForReceipt(ctx context.Context, client *ethclient.Client, txHash common.Hash, timeout time.Duration) (*types.Receipt, error) {
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	attempts := 0

	for {
		select {
		case <-ctx.Done():
			return nil, fmt.Errorf("timeout aguardando confirmação após %d tentativas", attempts)
		case <-ticker.C:
			attempts++
			receipt, err := client.TransactionReceipt(ctx, txHash)
			if err == nil {
				return receipt, nil
			}
			if err.Error() != "not found" {
				fmt.Printf("⚠️  Tentativa %d falhou: %v\n", attempts, err)
			}
		}
	}
}

func dialWithInsecureTLS(url string) (*ethclient.Client, error) {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	httpClient := &http.Client{Transport: tr}

	rpcClient, err := rpc.DialHTTPWithClient(url, httpClient)
	if err != nil {
		return nil, err
	}

	return ethclient.NewClient(rpcClient), nil
}

// ======================================================================
// WORKER
// ======================================================================

func worker(
	workerID int,
	wallet Wallet,
	rows []CSVRow,
	results chan<- Result,
	wg *sync.WaitGroup,
	contractAddress common.Address,
	contractABI abi.ABI,
	chainID *big.Int,
	printMutex *sync.Mutex,
) {
	defer wg.Done()

	ctx := context.Background()

	client, err := dialWithInsecureTLS(RPCURL)
	if err != nil {
		printMutex.Lock()
		fmt.Printf("[Worker %d] ❌ Erro ao conectar: %v\n", workerID, err)
		printMutex.Unlock()
		return
	}
	defer client.Close()

	privKeyHex := wallet.PrivateKey
	if strings.HasPrefix(privKeyHex, "0x") || strings.HasPrefix(privKeyHex, "0X") {
		privKeyHex = privKeyHex[2:]
	}

	privateKey, err := crypto.HexToECDSA(privKeyHex)
	if err != nil {
		printMutex.Lock()
		fmt.Printf("[Worker %d] ❌ Erro ao carregar chave: %v\n", workerID, err)
		printMutex.Unlock()
		return
	}

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		printMutex.Lock()
		fmt.Printf("[Worker %d] ❌ Erro ao converter chave pública\n", workerID)
		printMutex.Unlock()
		return
	}

	fromAddress := crypto.PubkeyToAddress(*publicKeyECDSA)

	nonce, err := client.PendingNonceAt(ctx, fromAddress)
	if err != nil {
		printMutex.Lock()
		fmt.Printf("[Worker %d] ❌ Erro ao obter nonce inicial: %v\n", workerID, err)
		printMutex.Unlock()
		return
	}

	printMutex.Lock()
	fmt.Printf("[Worker %d] 🚀 Iniciando com carteira %s (nonce inicial: %d)\n", workerID, fromAddress.Hex(), nonce)
	printMutex.Unlock()

	for idx, row := range rows {
		startTime := time.Now()

		result := Result{
			Linha:      idx + 1,
			WorkerID:   workerID,
			WalletAddr: wallet.Address,
			StartTime:  startTime,
		}

		params := prepareCalculationParams(row)

		// Blockchain tem zeroBaseFee: true, então gasPrice = 0
		gasPrice := big.NewInt(0)

		// calculateE2AndTokenize(CalculationParams params, address recipient)
		// O recipient é o próprio sender (cada worker minsta para sua própria carteira)
		input, err := contractABI.Pack("calculateE2AndTokenize", params, fromAddress)
		if err != nil {
			result.Error = fmt.Errorf("erro ao empacotar dados: %v", err)
			result.Latency = time.Since(startTime)
			results <- result
			continue
		}

		gasLimit := uint64(700000)
		tx := types.NewTransaction(nonce, contractAddress, big.NewInt(0), gasLimit, gasPrice, input)

		signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			results <- result
			continue
		}

		err = client.SendTransaction(ctx, signedTx)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			printMutex.Lock()
			fmt.Printf("[Worker %d] ❌ Erro ao enviar TX %d (nonce %d): %v\n", workerID, idx+1, nonce, err)
			printMutex.Unlock()

			errStr := err.Error()
			if strings.Contains(strings.ToLower(errStr), "nonce too low") {
				nonce++
			}

			results <- result
			continue
		}

		nonce++

		result.TxHash = signedTx.Hash().Hex()
		result.TxSentTime = time.Now()

		printMutex.Lock()
		fmt.Printf("[Worker %d] 📤 TX %d enviada: %s - Aguardando confirmação...\n", workerID, idx+1, result.TxHash[:10])
		printMutex.Unlock()

		receipt, err := waitForReceipt(ctx, client, signedTx.Hash(), TxTimeout)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			printMutex.Lock()
			fmt.Printf("[Worker %d] ❌ TX %d timeout/erro: %v\n", workerID, idx+1, err)
			printMutex.Unlock()
			results <- result
			continue
		}

		result.ConfirmedTime = time.Now()
		result.Latency = time.Since(startTime)
		result.Block = receipt.BlockNumber.Uint64()
		result.GasUsed = receipt.GasUsed

		printMutex.Lock()
		fmt.Printf("[Worker %d] ✅ TX %d confirmada! Bloco: %d, Gas: %d, Latência: %.2fs\n",
			workerID, idx+1, result.Block, result.GasUsed, result.Latency.Seconds())
		printMutex.Unlock()

		if receipt.Status != 1 {
			result.Error = fmt.Errorf("transação falhou (status=0)")
			printMutex.Lock()
			fmt.Printf("[Worker %d] ⚠️  TX %d falhou (status=0)\n", workerID, idx+1)
			printMutex.Unlock()
		}

		results <- result
	}

	printMutex.Lock()
	fmt.Printf("[Worker %d] ✅ Finalizado\n", workerID)
	printMutex.Unlock()
}

// ======================================================================
// MAIN
// ======================================================================

func main() {
	fmt.Println("=" + strings.Repeat("=", 70))
	fmt.Println("TESTE DE PERFORMANCE - CARBON CREDIT NFT E2")
	fmt.Println("=" + strings.Repeat("=", 70))

	deployment, err := loadDeploymentData()
	if err != nil {
		log.Fatalf("❌ Erro ao carregar deployment: %v", err)
	}

	fmt.Printf("📍 Contrato: %s\n", deployment.ContractAddress)

	var abiJSON []interface{}
	err = json.Unmarshal(deployment.ABI, &abiJSON)
	if err != nil {
		log.Fatalf("❌ Erro ao parsear ABI: %v", err)
	}

	abiBytes, _ := json.Marshal(abiJSON)
	contractABI, err := abi.JSON(strings.NewReader(string(abiBytes)))
	if err != nil {
		log.Fatalf("❌ Erro ao criar ABI: %v", err)
	}

	wallets, err := loadWallets(NumWorkers)
	if err != nil {
		log.Fatalf("❌ Erro ao carregar wallets: %v", err)
	}
	fmt.Printf("💼 Wallets carregadas: %d\n", len(wallets))

	client, err := dialWithInsecureTLS(RPCURL)
	if err != nil {
		log.Fatalf("❌ Erro ao conectar: %v", err)
	}

	chainID, err := client.ChainID(context.Background())
	if err != nil {
		log.Fatalf("❌ Erro ao obter chain ID: %v", err)
	}
	fmt.Printf("🔗 Chain ID: %s\n", chainID.String())

	client.Close()

	rawRows, err := readCSV(DataCSV)
	if err != nil {
		log.Fatalf("❌ Erro ao ler CSV: %v", err)
	}
	fmt.Printf("📊 Linhas no CSV: %d | Total a processar (por worker): %d\n", len(rawRows), TotalRows)

	rows := expandRows(rawRows, TotalRows)
	fmt.Printf("🔄 Linhas expandidas (com ciclo): %d\n", len(rows))

	fmt.Printf("\n🚀 Iniciando %d workers...\n", NumWorkers)

	startTime := time.Now()
	results := make(chan Result, NumWorkers*len(rows))
	var wg sync.WaitGroup
	var printMutex sync.Mutex

	contractAddress := common.HexToAddress(deployment.ContractAddress)

	for i := 0; i < NumWorkers; i++ {
		wg.Add(1)
		go worker(
			i+1,
			wallets[i],
			rows,
			results,
			&wg,
			contractAddress,
			contractABI,
			chainID,
			&printMutex,
		)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	var allResults []Result
	for r := range results {
		allResults = append(allResults, r)
	}

	totalDuration := time.Since(startTime)

	// Calcular estatísticas por worker
	workerStatsMap := make(map[int]*WorkerStats)
	for _, r := range allResults {
		if _, ok := workerStatsMap[r.WorkerID]; !ok {
			workerStatsMap[r.WorkerID] = &WorkerStats{
				WorkerID:   r.WorkerID,
				MinLatency: time.Hour * 24,
				StartTime:  r.StartTime,
			}
		}

		stats := workerStatsMap[r.WorkerID]
		stats.TotalTxs++

		if r.Error == nil {
			stats.SuccessfulTxs++
			stats.TotalLatency += r.Latency

			if r.Latency < stats.MinLatency {
				stats.MinLatency = r.Latency
			}
			if r.Latency > stats.MaxLatency {
				stats.MaxLatency = r.Latency
			}
		} else {
			stats.FailedTxs++
		}

		if r.ConfirmedTime.After(stats.EndTime) {
			stats.EndTime = r.ConfirmedTime
		}
	}

	var statsSlice []WorkerStats
	for _, stats := range workerStatsMap {
		stats.Duration = stats.EndTime.Sub(stats.StartTime)
		if stats.SuccessfulTxs > 0 {
			stats.AvgLatency = stats.TotalLatency / time.Duration(stats.SuccessfulTxs)
		}
		statsSlice = append(statsSlice, *stats)
	}

	os.MkdirAll("results", 0755)

	saveResults(allResults, fmt.Sprintf("results/e2_results_%dworkers.csv", NumWorkers))
	saveWorkerStats(statsSlice, fmt.Sprintf("results/e2_stats_%dworkers.csv", NumWorkers))

	// Resumo final
	totalSuccess := 0
	totalFail := 0
	var totalLatency time.Duration
	minLatency := time.Hour * 24
	maxLatency := time.Duration(0)

	for _, stats := range statsSlice {
		totalSuccess += stats.SuccessfulTxs
		totalFail += stats.FailedTxs
		totalLatency += stats.TotalLatency

		if stats.MinLatency < minLatency {
			minLatency = stats.MinLatency
		}
		if stats.MaxLatency > maxLatency {
			maxLatency = stats.MaxLatency
		}
	}

	avgLatency := time.Duration(0)
	if totalSuccess > 0 {
		avgLatency = totalLatency / time.Duration(totalSuccess)
	}

	totalThroughput := float64(totalSuccess) / totalDuration.Seconds()

	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("📊 RESUMO FINAL")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("Workers:             %d\n", NumWorkers)
	fmt.Printf("Total transações:    %d\n", totalSuccess+totalFail)
	fmt.Printf("Bem-sucedidas:       %d\n", totalSuccess)
	fmt.Printf("Falhas:              %d\n", totalFail)
	fmt.Printf("Taxa de sucesso:     %.2f%%\n", float64(totalSuccess)/float64(totalSuccess+totalFail)*100)
	fmt.Printf("\nDuração total:       %.2f segundos (%.2f minutos)\n", totalDuration.Seconds(), totalDuration.Minutes())
	fmt.Printf("Latência média:      %.2f segundos\n", avgLatency.Seconds())
	fmt.Printf("Latência mínima:     %.2f segundos\n", minLatency.Seconds())
	fmt.Printf("Latência máxima:     %.2f segundos\n", maxLatency.Seconds())
	fmt.Printf("\nThroughput total:    %.3f tx/s\n", totalThroughput)
	fmt.Println(strings.Repeat("=", 70))
}
