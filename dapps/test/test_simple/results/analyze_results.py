#!/usr/bin/env python3
"""
Script para analisar resultados de testes de carga e gerar CSV comparativo
Lê arquivos simple_stats_*workers.csv e gera relatório consolidado

Uso: python3 analyze_results.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import glob


def load_test_results(results_dir: str = ".") -> dict:
    """
    Carrega todos os arquivos de resultados
    
    Returns:
        Dicionário {num_workers: DataFrame}
    """
    results = {}
    
    # Buscar todos os arquivos simple_stats_*workers.csv
    pattern = f"{results_dir}/simple_stats_*workers.csv"
    files = glob.glob(pattern)
    
    if not files:
        print(f"❌ Nenhum arquivo encontrado com padrão: {pattern}")
        return results
    
    for file_path in sorted(files):
        # Extrair número de workers do nome do arquivo
        filename = Path(file_path).stem  # simple_stats_256workers
        num_workers = int(filename.split('_')[-1].replace('workers', ''))
        
        # Carregar CSV
        df = pd.read_csv(file_path)
        results[num_workers] = df
        
        print(f"✓ Carregado: {Path(file_path).name} ({len(df)} workers)")
    
    return results


def calculate_aggregate_stats(results: dict) -> pd.DataFrame:
    """
    Calcula estatísticas agregadas por número de workers
    
    Args:
        results: Dicionário {num_workers: DataFrame}
        
    Returns:
        DataFrame com estatísticas consolidadas
    """
    stats_list = []
    
    for num_workers, df in sorted(results.items()):
        # Filtrar workers com dados inválidos (duration negativa = worker travado)
        df_valid = df[df['duration_s'] > 0].copy()
        
        if len(df_valid) == 0:
            print(f"⚠️  Aviso: {num_workers} workers - todos os dados inválidos!")
            continue
        
        # Calcular estatísticas agregadas
        total_txs = df['total_txs'].sum()  # Usa df original para contar todas as txs
        total_successful = df['successful_txs'].sum()
        total_failed = df['failed_txs'].sum()
        
        # Taxa de sucesso
        success_rate = (total_successful / total_txs * 100) if total_txs > 0 else 0
        
        # Throughput: total_successful / tempo_do_teste
        # Usamos a duração máxima (worker mais lento válido) como aproximação do tempo total
        max_duration = df_valid['duration_s'].max()
        avg_duration = df_valid['duration_s'].mean()
        
        # Throughput baseado no tempo total do teste
        throughput = total_successful / max_duration if max_duration > 0 else 0
        
        # Eficiência: quantos workers realmente completaram (com dados válidos)
        workers_completed = len(df_valid[df_valid['total_txs'] > 0])
        workers_expected = num_workers
        completion_rate = (workers_completed / workers_expected * 100) if workers_expected > 0 else 0
        
        avg_latency = df_valid['avg_latency_ms'].mean()
        median_latency = df_valid['avg_latency_ms'].median()
        p95_latency = df_valid['avg_latency_ms'].quantile(0.95)
        p99_latency = df_valid['avg_latency_ms'].quantile(0.99)
        
        min_latency_global = df_valid['min_latency_ms'].min()
        max_latency_global = df_valid['max_latency_ms'].max()
        
        # Workers com falhas
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
            'throughput_tx_s': round(throughput, 2),
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


def generate_comparison_csv(df_stats: pd.DataFrame, output_file: str = "comparison_summary.csv"):
    """
    Gera CSV comparativo
    """
    df_stats.to_csv(output_file, index=False)
    print(f"\n💾 CSV comparativo salvo: {output_file}")


def print_summary_table(df_stats: pd.DataFrame):
    """
    Imprime tabela resumida no terminal
    """
    print("\n" + "="*120)
    print("📊 COMPARAÇÃO DE TESTES DE CARGA")
    print("="*120)
    
    # Tabela principal
    print(f"\n{'Workers':<10} {'Total TXs':<12} {'Sucesso':<10} {'Taxa %':<10} "
          f"{'Throughput':<15} {'Completude %':<15} {'Lat Média':<12} {'P95 Lat':<12}")
    print("-" * 120)
    
    for _, row in df_stats.iterrows():
        print(f"{row['num_workers']:<10} "
              f"{row['total_transactions']:<12} "
              f"{row['successful_txs']:<10} "
              f"{row['success_rate_pct']:<10.2f} "
              f"{row['throughput_tx_s']:<15.2f} "
              f"{row['completion_rate_pct']:<15.2f} "
              f"{row['avg_latency_ms']:<12.2f} "
              f"{row['p95_latency_ms']:<12.2f}")
    
    print("-" * 120)
    
    # Análise de melhor desempenho
    print("\n🏆 ANÁLISES")
    print("-" * 100)
    
    best_throughput = df_stats.loc[df_stats['throughput_tx_s'].idxmax()]
    print(f"✓ Melhor throughput: {best_throughput['num_workers']} workers "
          f"({best_throughput['throughput_tx_s']:.2f} tx/s)")
    
    best_success = df_stats.loc[df_stats['success_rate_pct'].idxmax()]
    print(f"✓ Melhor taxa de sucesso: {best_success['num_workers']} workers "
          f"({best_success['success_rate_pct']:.2f}%)")
    
    lowest_latency = df_stats.loc[df_stats['avg_latency_ms'].idxmin()]
    print(f"✓ Menor latência média: {lowest_latency['num_workers']} workers "
          f"({lowest_latency['avg_latency_ms']:.2f} ms)")
    
    print("="*100)


def generate_detailed_comparison(results: dict, output_file: str = "detailed_comparison.csv"):
    """
    Gera CSV com comparação detalhada (percentis de latência por worker count)
    """
    detailed_rows = []
    
    for num_workers, df in sorted(results.items()):
        # Calcular percentis de latência
        latencies = df['avg_latency_ms']
        
        row = {
            'num_workers': num_workers,
            'p0_latency_ms': round(latencies.min(), 2),
            'p10_latency_ms': round(latencies.quantile(0.10), 2),
            'p25_latency_ms': round(latencies.quantile(0.25), 2),
            'p50_latency_ms': round(latencies.quantile(0.50), 2),
            'p75_latency_ms': round(latencies.quantile(0.75), 2),
            'p90_latency_ms': round(latencies.quantile(0.90), 2),
            'p95_latency_ms': round(latencies.quantile(0.95), 2),
            'p99_latency_ms': round(latencies.quantile(0.99), 2),
            'p100_latency_ms': round(latencies.max(), 2),
            'std_latency_ms': round(latencies.std(), 2)
        }
        detailed_rows.append(row)
    
    df_detailed = pd.DataFrame(detailed_rows)
    df_detailed.to_csv(output_file, index=False)
    print(f"💾 Comparação detalhada salva: {output_file}")


def generate_throughput_analysis(results: dict, output_file: str = "throughput_analysis.csv"):
    """
    Gera análise específica de throughput
    """
    throughput_rows = []
    
    for num_workers, df in sorted(results.items()):
        total_throughput = df['throughput_tx_s'].sum()
        avg_per_worker = df['throughput_tx_s'].mean()
        median_per_worker = df['throughput_tx_s'].median()
        std_per_worker = df['throughput_tx_s'].std()
        
        # Eficiência (throughput real vs teórico)
        # Assumindo que cada worker deveria conseguir ~0.1 tx/s ideal
        theoretical_throughput = num_workers * 0.1
        efficiency = (total_throughput / theoretical_throughput * 100) if theoretical_throughput > 0 else 0
        
        row = {
            'num_workers': num_workers,
            'total_throughput_tx_s': round(total_throughput, 2),
            'avg_throughput_per_worker': round(avg_per_worker, 4),
            'median_throughput_per_worker': round(median_per_worker, 4),
            'std_throughput_per_worker': round(std_per_worker, 4),
            'theoretical_throughput': round(theoretical_throughput, 2),
            'efficiency_pct': round(efficiency, 2)
        }
        throughput_rows.append(row)
    
    df_throughput = pd.DataFrame(throughput_rows)
    df_throughput.to_csv(output_file, index=False)
    print(f"💾 Análise de throughput salva: {output_file}")


def main():
    """Função principal"""
    print("="*100)
    print("🔬 ANÁLISE DE RESULTADOS DE TESTES DE CARGA")
    print("="*100)
    
    # Carregar resultados
    print("\n📥 Carregando arquivos...")
    results = load_test_results(".")
    
    if not results:
        print("❌ Nenhum resultado encontrado!")
        return
    
    print(f"\n✓ Carregados {len(results)} conjuntos de testes")
    
    # Calcular estatísticas agregadas
    print("\n📊 Calculando estatísticas agregadas...")
    df_stats = calculate_aggregate_stats(results)
    
    # Gerar arquivos
    print("\n📝 Gerando arquivos...")
    generate_comparison_csv(df_stats, "comparison_summary.csv")
    generate_detailed_comparison(results, "detailed_comparison.csv")
    generate_throughput_analysis(results, "throughput_analysis.csv")
    
    # Imprimir resumo
    print_summary_table(df_stats)
    
    print("\n✅ Análise concluída!")
    print("\n📁 Arquivos gerados:")
    print("   1. comparison_summary.csv - Resumo comparativo geral")
    print("   2. detailed_comparison.csv - Percentis de latência detalhados")
    print("   3. throughput_analysis.csv - Análise específica de throughput")
    print("\n💡 Use esses CSVs para criar gráficos no Excel, Google Sheets, ou Python (matplotlib)")


if __name__ == "__main__":
    main()
