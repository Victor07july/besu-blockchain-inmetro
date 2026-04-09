#!/usr/bin/env python3
"""
Script para analisar resultados de testes de carga e gerar CSV comparativo.
Configurado para o padrão decimal brasileiro (vírgula para decimais, ponto para milhares).

Além do throughput tradicional (sucessos / maior duração), calcula métricas mais estáveis:
- attempted_throughput_tx_s: total de tentativas por segundo
- throughput_tx_s: sucessos por segundo (compatível com versões anteriores)
- effective_throughput_tx_s: throughput ponderado pela taxa de sucesso
- net_throughput_tx_s: (sucessos - falhas) por segundo
"""

import pandas as pd
from pathlib import Path
import glob
import locale

# Configura o sistema para usar o padrão brasileiro de formatação
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    # Caso o sistema não tenha o locale pt_BR instalado, usaremos uma função manual
    pass

def format_br(val, precision=2):
    """Auxiliar para formatar números no padrão 1.234,56"""
    if pd.isna(val): return "0,00"
    # Formata com separador de milhar americano (,) e decimal (.)
    s = f"{val:,.{precision}f}"
    # Inverte para o padrão brasileiro
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def load_test_results(results_dir: str = ".") -> dict:
    results = {}
    pattern = f"{results_dir}/e1_stats_*workers.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"❌ Nenhum arquivo encontrado com padrão: {pattern}")
        return results
    
    for file_path in sorted(files, key=lambda x: int(Path(x).stem.split('_')[-1].replace('workers', ''))):
        filename = Path(file_path).stem
        num_workers = int(filename.split('_')[-1].replace('workers', ''))
        
        # Carregar CSV original (que assume padrão US ponto decimal)
        df = pd.read_csv(file_path)
        results[num_workers] = df
        print(f"✓ Carregado: {Path(file_path).name} ({len(df)} workers)")
    
    return results

def calculate_throughput_metrics(total_txs: int, total_successful: int, total_failed: int, max_duration: float) -> dict:
    if max_duration <= 0:
        return {
            'attempted_throughput_tx_s': 0.0,
            'throughput_tx_s': 0.0,
            'effective_throughput_tx_s': 0.0,
            'net_throughput_tx_s': 0.0,
        }

    success_rate = (total_successful / total_txs) if total_txs > 0 else 0.0
    attempted_throughput = total_txs / max_duration
    success_throughput = total_successful / max_duration
    effective_throughput = success_throughput * success_rate
    net_throughput = (total_successful - total_failed) / max_duration

    return {
        'attempted_throughput_tx_s': attempted_throughput,
        'throughput_tx_s': success_throughput,
        'effective_throughput_tx_s': effective_throughput,
        'net_throughput_tx_s': net_throughput,
    }

def calculate_aggregate_stats(results: dict) -> pd.DataFrame:
    stats_list = []
    
    for num_workers, df in sorted(results.items()):
        df_valid = df[df['duration_s'] > 0].copy()
        
        if len(df_valid) == 0:
            print(f"⚠️  Aviso: {num_workers} workers - todos os dados inválidos!")
            continue
        
        total_txs = df['total_txs'].sum()
        total_successful = df['successful_txs'].sum()
        total_failed = df['failed_txs'].sum()
        
        success_rate = (total_successful / total_txs * 100) if total_txs > 0 else 0
        max_duration = df_valid['duration_s'].max()
        avg_duration = df_valid['duration_s'].mean()
        throughput_metrics = calculate_throughput_metrics(
            total_txs=total_txs,
            total_successful=total_successful,
            total_failed=total_failed,
            max_duration=max_duration,
        )
        
        workers_completed = len(df_valid[df_valid['total_txs'] > 0])
        workers_expected = num_workers
        completion_rate = (workers_completed / workers_expected * 100) if workers_expected > 0 else 0
        
        avg_latency = df_valid['avg_latency_ms'].mean()
        median_latency = df_valid['avg_latency_ms'].median()
        p95_latency = df_valid['avg_latency_ms'].quantile(0.95)
        p99_latency = df_valid['avg_latency_ms'].quantile(0.99)
        
        min_latency_global = df_valid['min_latency_ms'].min()
        max_latency_global = df_valid['max_latency_ms'].max()
        
        workers_with_failures = (df['failed_txs'] > 0).sum()
        workers_without_failures = (df['failed_txs'] == 0).sum()
        
        stats = {
            'num_workers': num_workers,
            'workers_completed': workers_completed,
            'workers_expected': workers_expected,
            'completion_rate_pct': round(completion_rate, 2),
            'total_transactions': total_txs,
            'successful_txs': total_successful,
            'failed_txs': total_failed,
            'success_rate_pct': round(success_rate, 2),
            'attempted_throughput_tx_s': round(throughput_metrics['attempted_throughput_tx_s'], 2),
            'throughput_tx_s': round(throughput_metrics['throughput_tx_s'], 2),
            'effective_throughput_tx_s': round(throughput_metrics['effective_throughput_tx_s'], 2),
            'net_throughput_tx_s': round(throughput_metrics['net_throughput_tx_s'], 2),
            'max_duration_s': round(max_duration, 2),
            'avg_duration_s': round(avg_duration, 2),
            'avg_latency_ms': round(avg_latency, 2),
            'median_latency_ms': round(median_latency, 2),
            'p95_latency_ms': round(p95_latency, 2),
            'p99_latency_ms': round(p99_latency, 2),
            'min_latency_ms': round(min_latency_global, 2),
            'max_latency_ms': round(max_latency_global, 2),
            'workers_with_failures': workers_with_failures,
            'workers_without_failures': workers_without_failures
        }
        stats_list.append(stats)
    
    return pd.DataFrame(stats_list)

def save_brazilian_csv(df, filename):
    """Salva CSV com ; e , para Excel BR"""
    df.to_csv(filename, index=False, sep=';', decimal=',')
    print(f"💾 Arquivo salvo (Padrão BR): {filename}")

def print_summary_table(df_stats: pd.DataFrame):
    print("\n" + "="*166)
    print("📊 COMPARAÇÃO DE TESTES DE CARGA (Valores em Padrão Brasileiro)")
    print("="*166)
    
    print(f"{'Workers':<8} {'Total TXs':<12} {'Sucesso':<10} {'Taxa %':<10} "
        f"{'Thr Tent':<12} {'Thr Sucesso':<13} {'Thr Efetivo':<13} {'Comp. %':<10} "
        f"{'Lat Méd(ms)':<15} {'P95 Lat':<10}")
    print("-" * 166)
    
    for _, row in df_stats.iterrows():
        print(f"{int(row['num_workers']):<8} "
              f"{int(row['total_transactions']):<12} "
              f"{int(row['successful_txs']):<10} "
              f"{format_br(row['success_rate_pct']):<10} "
          f"{format_br(row['attempted_throughput_tx_s']):<12} "
              f"{format_br(row['throughput_tx_s']):<15} "
          f"{format_br(row['effective_throughput_tx_s']):<13} "
              f"{format_br(row['completion_rate_pct']):<10} "
              f"{format_br(row['avg_latency_ms']):<15} "
              f"{format_br(row['p95_latency_ms']):<10}")
    print("-" * 166)

def main():
    print("🔬 INICIANDO ANÁLISE DE RESULTADOS...")
    results = load_test_results(".")
    
    if not results:
        return
    
    df_stats = calculate_aggregate_stats(results)
    
    # Geração dos arquivos com separadores brasileiros
    save_brazilian_csv(df_stats, "comparison_summary_br.csv")
    
    # Tabelas no terminal
    print_summary_table(df_stats)
    
    print("\n✅ Análise concluída com sucesso!")

if __name__ == "__main__":
    main()