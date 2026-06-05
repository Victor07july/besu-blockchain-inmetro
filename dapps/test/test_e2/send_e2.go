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
	RPCURL         = "https://ec2-3-133-99-147.us-east-2.compute.amazonaws.com/user/"
	DeploymentJSON = "./e2_deployment.json"
	WalletsJSON    = "./wallets_64_groups.json"
	DataCSV        = "./dados_gas.csv"
	NumWorkers     = 1024
	TotalRows      = 100
	TxTimeout      = 120 * time.Second

	// Duração máxima do teste. Após esse tempo:
	//   - workers param de iniciar novas transações
	//   - transações já enviadas mas confirmadas após o deadline são descartadas
	// Use 0 para desativar o limite (comportamento original).
	TestDuration = 10 * time.Minute
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
	StartTime     time.Time
	EndTime       time.Time
	Duration      time.Duration

	// Latências apenas de transações bem-sucedidas
	TotalLatency time.Duration
	AvgLatency   time.Duration
	MinLatency   time.Duration
	MaxLatency   time.Duration

	// Latências apenas de transações com erro
	TotalErrorLatency time.Duration
	AvgErrorLatency   time.Duration
	MinErrorLatency   time.Duration
	MaxErrorLatency   time.Duration
}

// ======================================================================
// FUNÇÕES AUXILIARES
// ======================================================================

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
	if row.RoadGasoline == 0 {
		row.RoadGasoline = 14.0
	}
	if row.RoadEthanol == 0 {
		row.RoadEthanol = 10.0
	}
	if row.CityGasoline == 0 {
		row.CityGasoline = 12.0
	}
	if row.CityEthanol == 0 {
		row.CityEthanol = 8.0
	}
	if row.PrecoGasolina == 0 {
		row.PrecoGasolina = 6.0
	}
	if row.PrecoEtanol == 0 {
		row.PrecoEtanol = 4.2
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
	data, err := os.ReadFile(filepath.Join(dir, DeploymentJSON))
	if err != nil {
		return nil, err
	}
	var deployment DeploymentData
	return &deployment, json.Unmarshal(data, &deployment)
}

func loadWallets(numWallets int) ([]Wallet, error) {
	dir, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(filepath.Join(dir, WalletsJSON))
	if err != nil {
		return nil, err
	}
	var walletsMap map[string]Wallet
	if err := json.Unmarshal(data, &walletsMap); err != nil {
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
		rows = append(rows, CSVRow{
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
		})
	}
	return rows, nil
}

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
		"duration_s", "throughput_tx_s",
		"success_avg_latency_ms", "success_min_latency_ms", "success_max_latency_ms",
		"error_avg_latency_ms", "error_min_latency_ms", "error_max_latency_ms",
	})

	for _, s := range stats {
		throughput := 0.0
		if s.Duration.Seconds() > 0 {
			throughput = float64(s.SuccessfulTxs) / s.Duration.Seconds()
		}

		sucAvg, sucMin, sucMax := "-", "-", "-"
		if s.SuccessfulTxs > 0 {
			sucAvg = fmt.Sprintf("%.2f", s.AvgLatency.Seconds()*1000)
			sucMin = fmt.Sprintf("%.2f", s.MinLatency.Seconds()*1000)
			sucMax = fmt.Sprintf("%.2f", s.MaxLatency.Seconds()*1000)
		}

		errAvg, errMin, errMax := "-", "-", "-"
		if s.FailedTxs > 0 {
			errAvg = fmt.Sprintf("%.2f", s.AvgErrorLatency.Seconds()*1000)
			errMin = fmt.Sprintf("%.2f", s.MinErrorLatency.Seconds()*1000)
			errMax = fmt.Sprintf("%.2f", s.MaxErrorLatency.Seconds()*1000)
		}

		writer.Write([]string{
			fmt.Sprintf("%d", s.WorkerID),
			fmt.Sprintf("%d", s.TotalTxs),
			fmt.Sprintf("%d", s.SuccessfulTxs),
			fmt.Sprintf("%d", s.FailedTxs),
			fmt.Sprintf("%.2f", s.Duration.Seconds()),
			fmt.Sprintf("%.2f", throughput),
			sucAvg, sucMin, sucMax,
			errAvg, errMin, errMax,
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
	rpcClient, err := rpc.DialHTTPWithClient(url, &http.Client{Transport: tr})
	if err != nil {
		return nil, err
	}
	return ethclient.NewClient(rpcClient), nil
}

// ======================================================================
// WORKER
// ======================================================================

// worker recebe deadlineCtx: quando ele expira, nenhuma nova transação é iniciada.
// Transações já em voo continuam até TxTimeout, mas serão filtradas no main
// caso a confirmação chegue após o deadline.
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
	deadlineCtx context.Context, // cancelado quando TestDuration expirar
) {
	defer wg.Done()

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

	publicKeyECDSA, ok := privateKey.Public().(*ecdsa.PublicKey)
	if !ok {
		printMutex.Lock()
		fmt.Printf("[Worker %d] ❌ Erro ao converter chave pública\n", workerID)
		printMutex.Unlock()
		return
	}

	fromAddress := crypto.PubkeyToAddress(*publicKeyECDSA)

	// Usa deadlineCtx para obter o nonce: se o deadline já expirou antes de
	// começar, o worker encerra limpo.
	nonce, err := client.PendingNonceAt(deadlineCtx, fromAddress)
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
		// ── Verifica o deadline ANTES de iniciar cada nova transação ──────
		select {
		case <-deadlineCtx.Done():
			printMutex.Lock()
			fmt.Printf("[Worker %d] ⏱️  Tempo esgotado — encerrando após %d transações.\n", workerID, idx)
			printMutex.Unlock()
			return
		default:
		}

		startTime := time.Now()

		result := Result{
			Linha:      idx + 1,
			WorkerID:   workerID,
			WalletAddr: wallet.Address,
			StartTime:  startTime,
		}

		params := prepareCalculationParams(row)
		gasPrice := big.NewInt(0)

		input, err := contractABI.Pack("calculateE2AndTokenize", params, fromAddress)
		if err != nil {
			result.Error = fmt.Errorf("erro ao empacotar dados: %v", err)
			result.Latency = time.Since(startTime)
			results <- result
			continue
		}

		tx := types.NewTransaction(nonce, contractAddress, big.NewInt(0), uint64(700000), gasPrice, input)

		signedTx, err := types.SignTx(tx, types.NewEIP155Signer(chainID), privateKey)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			results <- result
			continue
		}

		// Envia usando deadlineCtx: se o contexto já foi cancelado, SendTransaction
		// retorna imediatamente com erro, sem enviar à rede.
		err = client.SendTransaction(deadlineCtx, signedTx)
		if err != nil {
			result.Error = err
			result.Latency = time.Since(startTime)
			printMutex.Lock()
			fmt.Printf("[Worker %d] ❌ Erro ao enviar TX %d (nonce %d): %v\n", workerID, idx+1, nonce, err)
			printMutex.Unlock()

			if strings.Contains(strings.ToLower(err.Error()), "nonce too low") {
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

		// Para o waitForReceipt usamos context.Background() com TxTimeout próprio,
		// pois a transação já foi enviada à rede e deve ser aguardada normalmente.
		// O filtro do deadline é feito no main, após a confirmação.
		receipt, err := waitForReceipt(context.Background(), client, signedTx.Hash(), TxTimeout)
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

	if TestDuration > 0 {
		fmt.Printf("⏱️  Duração máxima do teste: %v\n", TestDuration)
	} else {
		fmt.Println("⏱️  Duração máxima: sem limite (processará todas as linhas)")
	}

	deployment, err := loadDeploymentData()
	if err != nil {
		log.Fatalf("❌ Erro ao carregar deployment: %v", err)
	}
	fmt.Printf("📍 Contrato: %s\n", deployment.ContractAddress)

	var abiJSON []interface{}
	if err := json.Unmarshal(deployment.ABI, &abiJSON); err != nil {
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

	// ── Deadline global ───────────────────────────────────────────────────
	testStart := time.Now()
	var deadline time.Time
	var deadlineCtx context.Context
	var cancelDeadline context.CancelFunc

	if TestDuration > 0 {
		deadlineCtx, cancelDeadline = context.WithTimeout(context.Background(), TestDuration)
		deadline = testStart.Add(TestDuration)
	} else {
		// Sem limite: contexto que nunca expira
		deadlineCtx, cancelDeadline = context.WithCancel(context.Background())
	}
	defer cancelDeadline()

	results := make(chan Result, NumWorkers*len(rows))
	var wg sync.WaitGroup
	var printMutex sync.Mutex

	contractAddress := common.HexToAddress(deployment.ContractAddress)

	for i := 0; i < NumWorkers; i++ {
		wg.Add(1)
		go worker(i+1, wallets[i], rows, results, &wg, contractAddress, contractABI, chainID, &printMutex, deadlineCtx)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	var allResults []Result
	for r := range results {
		allResults = append(allResults, r)
	}

	totalDuration := time.Since(testStart)

	// ── Filtro pelo deadline ───────────────────────────────────────────────
	// Descarta transações confirmadas APÓS o deadline (ou com erro ocorrido
	// após o deadline). Transações com erro instantâneo (pack/sign/send)
	// têm ConfirmedTime zero — essas são mantidas se StartTime <= deadline.
	var filteredResults []Result
	discarded := 0

	for _, r := range allResults {
		if TestDuration > 0 {
			ref := r.ConfirmedTime
			if ref.IsZero() {
				ref = r.StartTime
			}
			if ref.After(deadline) {
				discarded++
				continue
			}
		}
		filteredResults = append(filteredResults, r)
	}

	if TestDuration > 0 && discarded > 0 {
		fmt.Printf("\n⏱️  %d transação(ões) descartada(s) por confirmação após o deadline.\n", discarded)
	}

	// ── Acumulação de estatísticas por worker (sobre filteredResults) ──────
	workerStatsMap := make(map[int]*WorkerStats)
	for _, r := range filteredResults {
		if _, ok := workerStatsMap[r.WorkerID]; !ok {
			workerStatsMap[r.WorkerID] = &WorkerStats{
				WorkerID:        r.WorkerID,
				MinLatency:      24 * time.Hour,
				MinErrorLatency: 24 * time.Hour,
				StartTime:       r.StartTime,
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
			stats.TotalErrorLatency += r.Latency
			if r.Latency < stats.MinErrorLatency {
				stats.MinErrorLatency = r.Latency
			}
			if r.Latency > stats.MaxErrorLatency {
				stats.MaxErrorLatency = r.Latency
			}
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
		if stats.FailedTxs > 0 {
			stats.AvgErrorLatency = stats.TotalErrorLatency / time.Duration(stats.FailedTxs)
		}
		statsSlice = append(statsSlice, *stats)
	}

	os.MkdirAll("results", 0755)
	saveResults(filteredResults, fmt.Sprintf("results/e2_results_%dworkers.csv", NumWorkers))
	saveWorkerStats(statsSlice, fmt.Sprintf("results/e2_stats_%dworkers.csv", NumWorkers))

	// ── Resumo global ─────────────────────────────────────────────────────
	totalSuccess := 0
	totalFail := 0
	var totalSuccessLatency time.Duration
	var totalErrorLatency time.Duration
	minSuccessLatency := 24 * time.Hour
	maxSuccessLatency := time.Duration(0)
	minErrorLatency := 24 * time.Hour
	maxErrorLatency := time.Duration(0)

	for _, stats := range statsSlice {
		totalSuccess += stats.SuccessfulTxs
		totalFail += stats.FailedTxs
		totalSuccessLatency += stats.TotalLatency
		totalErrorLatency += stats.TotalErrorLatency

		if stats.SuccessfulTxs > 0 {
			if stats.MinLatency < minSuccessLatency {
				minSuccessLatency = stats.MinLatency
			}
			if stats.MaxLatency > maxSuccessLatency {
				maxSuccessLatency = stats.MaxLatency
			}
		}
		if stats.FailedTxs > 0 {
			if stats.MinErrorLatency < minErrorLatency {
				minErrorLatency = stats.MinErrorLatency
			}
			if stats.MaxErrorLatency > maxErrorLatency {
				maxErrorLatency = stats.MaxErrorLatency
			}
		}
	}

	avgSuccessLatency := time.Duration(0)
	if totalSuccess > 0 {
		avgSuccessLatency = totalSuccessLatency / time.Duration(totalSuccess)
	}

	avgErrorLatency := time.Duration(0)
	if totalFail > 0 {
		avgErrorLatency = totalErrorLatency / time.Duration(totalFail)
	}

	totalThroughput := float64(totalSuccess) / totalDuration.Seconds()

	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("📊 RESUMO FINAL")
	fmt.Println(strings.Repeat("=", 70))
	fmt.Printf("Workers:             %d\n", NumWorkers)
	if TestDuration > 0 {
		fmt.Printf("Duração configurada: %v\n", TestDuration)
	}
	fmt.Printf("Total transações:    %d\n", totalSuccess+totalFail)
	fmt.Printf("Bem-sucedidas:       %d\n", totalSuccess)
	fmt.Printf("Falhas:              %d\n", totalFail)
	fmt.Printf("Descartadas:         %d\n", discarded)
	fmt.Printf("Taxa de sucesso:     %.2f%%\n", float64(totalSuccess)/float64(totalSuccess+totalFail)*100)
	fmt.Printf("\nDuração total:       %.2fs (%.2f min)\n", totalDuration.Seconds(), totalDuration.Minutes())
	fmt.Printf("Throughput total:    %.3f tx/s\n", totalThroughput)

	fmt.Println("\n── Latência (transações bem-sucedidas) ──")
	if totalSuccess > 0 {
		fmt.Printf("  Média:             %.2f s\n", avgSuccessLatency.Seconds())
		fmt.Printf("  Mínima:            %.2f s\n", minSuccessLatency.Seconds())
		fmt.Printf("  Máxima:            %.2f s\n", maxSuccessLatency.Seconds())
	} else {
		fmt.Println("  Nenhuma transação bem-sucedida.")
	}

	fmt.Println("\n── Latência (transações com erro) ──")
	if totalFail > 0 {
		fmt.Printf("  Média:             %.2f s\n", avgErrorLatency.Seconds())
		fmt.Printf("  Mínima:            %.2f s\n", minErrorLatency.Seconds())
		fmt.Printf("  Máxima:            %.2f s\n", maxErrorLatency.Seconds())
	} else {
		fmt.Println("  Nenhuma falha registrada.")
	}

	fmt.Println(strings.Repeat("=", 70))
}
