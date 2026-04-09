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
	RPCURL         = "https://ec2-18-191-167-241.us-east-2.compute.amazonaws.com/user/"
	DeploymentJSON = "./simple_counter_deployment.json"
	WalletsJSON    = "./wallets_64_groups.json"
	DataCSV        = "./dados_gas.csv"
	NumWorkers     = 2 // Comece com 2 para teste rápido
	MaxRowsToRead  = 100  // Teste rápido com 100 transações
	TxTimeout      = 120 * time.Second
)

// ======================================================================
// ESTRUTURAS
// ======================================================================

type Wallet struct {
	Address    string `json:"address"`
	PrivateKey string `json:"private_key"`
}

type VehicleData struct {
	DistanceHighway     *big.Int
	DistanceCity        *big.Int
	CityGasoline        *big.Int
	RoadGasoline        *big.Int
	CityEthanol         *big.Int
	RoadEthanol         *big.Int
	CarbonPriceEuropean *big.Int
	EuroPrice           *big.Int
}

type DeploymentData struct {
	ContractAddress string          `json:"contract_address"`
	ABI             json.RawMessage `json:"abi"`
	GasUsed         uint64          `json:"gas_used"`
}

type CSVRow struct {
	DistanceHighway     float64
	DistanceCity        float64
	CityGasoline        float64
	RoadGasoline        float64
	CityEthanol         float64
	RoadEthanol         float64
	CarbonPriceEuropean float64
	EuroPrice           float64
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

func prepareVehicleData(row CSVRow) VehicleData {
	if row.CityGasoline == 0 {
		row.CityGasoline = 12.0
	}
	if row.RoadGasoline == 0 {
		row.RoadGasoline = 14.0
	}
	if row.CityEthanol == 0 {
		row.CityEthanol = 8.0
	}
	if row.RoadEthanol == 0 {
		row.RoadEthanol = 10.0
	}
	if row.CarbonPriceEuropean == 0 {
		row.CarbonPriceEuropean = 80.0
	}
	if row.EuroPrice == 0 {
		row.EuroPrice = 6.0
	}

	// Garantir que valores são positivos e dentro de limites seguros
	clampPositive := func(val float64) float64 {
		if val < 0 {
			return 0
		}
		if val > 1e9 { // Limite máximo para evitar overflow
			return 1e9
		}
		return val
	}

	return VehicleData{
		DistanceHighway:     big.NewInt(int64(clampPositive(row.DistanceHighway))),
		DistanceCity:        big.NewInt(int64(clampPositive(row.DistanceCity))),
		CityGasoline:        big.NewInt(int64(clampPositive(row.CityGasoline * 1000))),
		RoadGasoline:        big.NewInt(int64(clampPositive(row.RoadGasoline * 1000))),
		CityEthanol:         big.NewInt(int64(clampPositive(row.CityEthanol * 1000))),
		RoadEthanol:         big.NewInt(int64(clampPositive(row.RoadEthanol * 1000))),
		CarbonPriceEuropean: big.NewInt(int64(clampPositive(row.CarbonPriceEuropean * 100))),
		EuroPrice:           big.NewInt(int64(clampPositive(row.EuroPrice * 10000))),
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
		colMap[col] = i
	}

	var rows []CSVRow
	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		parseFloat := func(colName string) float64 {
			if idx, ok := colMap[colName]; ok && idx < len(record) {
				val, _ := strconv.ParseFloat(record[idx], 64)
				return val
			}
			return 0
		}

		row := CSVRow{
			DistanceHighway:     parseFloat("highway (distance)"),
			DistanceCity:        parseFloat("city (distance)"),
			CityGasoline:        parseFloat("city (gasoline)"),
			RoadGasoline:        parseFloat("road (gasoline)"),
			CityEthanol:         parseFloat("city (ethanol)"),
			RoadEthanol:         parseFloat("road (ethanol)"),
			CarbonPriceEuropean: parseFloat("carbon_price_european"),
			EuroPrice:           parseFloat("euro_price"),
		}
		rows = append(rows, row)

		if MaxRowsToRead > 0 && len(rows) >= MaxRowsToRead {
			break
		}
	}

	return rows, nil
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
			// Se erro mas não é só "not found", mostrar
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

	// Remove o prefixo "0x" se existir
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

	// Obter nonce inicial uma única vez
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

		vehicleData := prepareVehicleData(row)

		// Blockchain tem zeroBaseFee: true, então gasPrice = 0
		gasPrice := big.NewInt(0)

		input, err := contractABI.Pack("calculateAndRecordE1", vehicleData)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			results <- result
			continue
		}

		gasLimit := uint64(500000)
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

			// Se erro é "nonce too low", incrementar e continuar
			// Se erro é outro (invalid params, network), não incrementar
			errStr := err.Error()
			if strings.Contains(strings.ToLower(errStr), "nonce too low") {
				nonce++
			}

			results <- result
			continue
		}

		// TX enviada com sucesso - incrementar nonce
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
		fmt.Printf("[Worker %d] ✅ TX %d confirmada! Bloco: %d, Latência: %.2fs\n",
			workerID, idx+1, result.Block, result.Latency.Seconds())
		printMutex.Unlock()

		if receipt.Status != 1 {
			result.Error = fmt.Errorf("transação falhou")
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
	fmt.Println("TESTE DE PERFORMANCE - SIMPLE COUNTER")
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

	rows, err := readCSV(DataCSV)
	if err != nil {
		log.Fatalf("❌ Erro ao ler CSV: %v", err)
	}
	fmt.Printf("📊 Linhas do CSV: %d\n", len(rows))

	if MaxRowsToRead > 0 && len(rows) > MaxRowsToRead {
		rows = rows[:MaxRowsToRead]
		fmt.Printf("⚠️  Limitado a: %d linhas\n", MaxRowsToRead)
	}

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

	// Calcular estatísticas
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

	// Criar diretório de resultados
	os.MkdirAll("results", 0755)

	// Salvar resultados
	saveResults(allResults, fmt.Sprintf("results/simple_results_%dworkers.csv", NumWorkers))
	saveWorkerStats(statsSlice, fmt.Sprintf("results/simple_stats_%dworkers.csv", NumWorkers))

	// Resumo
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
