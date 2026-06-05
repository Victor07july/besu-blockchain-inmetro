#!/usr/bin/env python3
"""
Script para analisar resultados de testes de carga e gerar CSV comparativo.
Configurado para o padrão decimal brasileiro (vírgula para decimais, ponto para milhares).

Além do throughput tradicional (sucessos / maior duração), calcula métricas mais estáveis:
- attempted_throughput_tx_s: total de tentativas por segundo
- throughput_tx_s: sucessos por segundo
- effective_throughput_tx_s: throughput ponderado pela taxa de sucesso
- net_throughput_tx_s: (sucessos - falhas) por segundo

Latências são calculadas separadamente para transações bem-sucedidas e com erro.
Colunas esperadas no CSV de entrada:
  worker_id, total_txs, successful_txs, failed_txs, duration_s, throughput_tx_s,
  success_avg_latency_ms, success_min_latency_ms, success_max_latency_ms,
  error_avg_latency_ms,   error_min_latency_ms,   error_max_latency_ms
"""

import pandas as pd
from pathlib import Path
import glob
import locale

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except Exception:
    pass


def format_br(val, precision=2):
    """Formata números no padrão brasileiro: 1.234,56"""
    if pd.isna(val):
        return "0,00"
    s = f"{val:,.{precision}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ──────────────────────────────────────────────────────────────────────────────
# Carregamento
# ──────────────────────────────────────────────────────────────────────────────

def load_test_results(results_dir: str = ".", experiment: str = "e2") -> dict:
    """
    Carrega todos os arquivos <experiment>_stats_*workers.csv do diretório.
    Retorna um dict  {num_workers: DataFrame}.
    """
    results = {}
    pattern = f"{results_dir}/{experiment}_stats_*workers.csv"
    files = glob.glob(pattern)

    if not files:
        print(f"❌ Nenhum arquivo encontrado com padrão: {pattern}")
        return results

    for file_path in sorted(
        files,
        key=lambda x: int(Path(x).stem.split('_')[-1].replace('workers', ''))
    ):
        filename = Path(file_path).stem
        num_workers = int(filename.split('_')[-1].replace('workers', ''))
        df = pd.read_csv(file_path)
        results[num_workers] = df
        print(f"✓ Carregado: {Path(file_path).name} ({len(df)} workers)")

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Métricas de throughput
# ──────────────────────────────────────────────────────────────────────────────

def calculate_throughput_metrics(
    total_txs: int,
    total_successful: int,
    total_failed: int,
    max_duration: float,
) -> dict:
    if max_duration <= 0:
        return {
            'attempted_throughput_tx_s': 0.0,
            'throughput_tx_s': 0.0,
            'effective_throughput_tx_s': 0.0,
            'net_throughput_tx_s': 0.0,
        }

    success_rate  = (total_successful / total_txs) if total_txs > 0 else 0.0
    attempted     = total_txs        / max_duration
    success_thr   = total_successful / max_duration
    effective_thr = success_thr * success_rate
    net_thr       = (total_successful - total_failed) / max_duration

    return {
        'attempted_throughput_tx_s':  attempted,
        'throughput_tx_s':            success_thr,
        'effective_throughput_tx_s':  effective_thr,
        'net_throughput_tx_s':        net_thr,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Helpers para lidar com colunas de latência que podem ser "-" (sem ocorrências)
# ──────────────────────────────────────────────────────────────────────────────

def _numeric_col(df: pd.DataFrame, col: str) -> pd.Series:
    """
    Retorna a coluna convertida para float, coercing "-" e strings inválidas
    para NaN, de modo que as funções de agregação as ignorem corretamente.
    """
    return pd.to_numeric(df[col], errors='coerce')


def _latency_stats(df_valid: pd.DataFrame, prefix: str) -> dict:
    """
    Calcula avg/median/p95/p99/min/max para o prefixo dado
    ('success' ou 'error'), ignorando linhas sem ocorrências ("-" → NaN).
    """
    avg_col = f"{prefix}_avg_latency_ms"
    min_col = f"{prefix}_min_latency_ms"
    max_col = f"{prefix}_max_latency_ms"

    avg_series = _numeric_col(df_valid, avg_col)
    min_series = _numeric_col(df_valid, min_col)
    max_series = _numeric_col(df_valid, max_col)

    valid_mask = avg_series.notna()

    if valid_mask.sum() == 0:
        return {
            f"{prefix}_avg_latency_ms":    None,
            f"{prefix}_median_latency_ms": None,
            f"{prefix}_p95_latency_ms":    None,
            f"{prefix}_p99_latency_ms":    None,
            f"{prefix}_min_latency_ms":    None,
            f"{prefix}_max_latency_ms":    None,
        }

    return {
        f"{prefix}_avg_latency_ms":    round(avg_series[valid_mask].mean(),         2),
        f"{prefix}_median_latency_ms": round(avg_series[valid_mask].median(),       2),
        f"{prefix}_p95_latency_ms":    round(avg_series[valid_mask].quantile(0.95), 2),
        f"{prefix}_p99_latency_ms":    round(avg_series[valid_mask].quantile(0.99), 2),
        f"{prefix}_min_latency_ms":    round(min_series[valid_mask].min(),          2),
        f"{prefix}_max_latency_ms":    round(max_series[valid_mask].max(),          2),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Agregação principal
# ──────────────────────────────────────────────────────────────────────────────

def calculate_aggregate_stats(results: dict) -> pd.DataFrame:
    stats_list = []

    for num_workers, df in sorted(results.items()):
        df_valid = df[df['duration_s'] > 0].copy()

        if len(df_valid) == 0:
            print(f"⚠️  Aviso: {num_workers} workers — todos os dados inválidos!")
            continue

        total_txs        = df['total_txs'].sum()
        total_successful = df['successful_txs'].sum()
        total_failed     = df['failed_txs'].sum()

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
        completion_rate   = (workers_completed / num_workers * 100) if num_workers > 0 else 0

        workers_with_failures    = (df['failed_txs'] > 0).sum()
        workers_without_failures = (df['failed_txs'] == 0).sum()

        # Latências separadas por resultado
        success_lat = _latency_stats(df_valid, 'success')
        error_lat   = _latency_stats(df_valid, 'error')

        stats = {
            'num_workers':               num_workers,
            'workers_completed':         workers_completed,
            'workers_expected':          num_workers,
            'completion_rate_pct':       round(completion_rate, 2),
            'total_transactions':        total_txs,
            'successful_txs':            total_successful,
            'failed_txs':                total_failed,
            'success_rate_pct':          round(success_rate, 2),
            'attempted_throughput_tx_s': round(throughput_metrics['attempted_throughput_tx_s'], 2),
            'throughput_tx_s':           round(throughput_metrics['throughput_tx_s'],            2),
            'effective_throughput_tx_s': round(throughput_metrics['effective_throughput_tx_s'],  2),
            'net_throughput_tx_s':       round(throughput_metrics['net_throughput_tx_s'],        2),
            'max_duration_s':            round(max_duration, 2),
            'avg_duration_s':            round(avg_duration, 2),
            'workers_with_failures':     workers_with_failures,
            'workers_without_failures':  workers_without_failures,
            **success_lat,
            **error_lat,
        }
        stats_list.append(stats)

    return pd.DataFrame(stats_list)


# ──────────────────────────────────────────────────────────────────────────────
# Saída
# ──────────────────────────────────────────────────────────────────────────────

def save_brazilian_csv(df: pd.DataFrame, filename: str):
    """Salva CSV com ; e , para Excel BR"""
    df.to_csv(filename, index=False, sep=';', decimal=',')
    print(f"💾 Arquivo salvo (Padrão BR): {filename}")


def _fmt(val, precision=2) -> str:
    """Formata valor ou retorna 'N/A' se None/NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return format_br(val, precision)


def print_summary_table(df_stats: pd.DataFrame):
    sep = "=" * 180
    print("\n" + sep)
    print("📊 COMPARAÇÃO DE TESTES DE CARGA e2 (Valores em Padrão Brasileiro)")
    print(sep)

    print(
        f"{'Workers':<8} {'Total':<8} {'OK':<8} {'Falhas':<8} {'Suc%':<8} "
        f"{'Thr.Tent':<10} {'Thr.Suc':<10} {'Thr.Ef':<10} "
        f"{'LatSuc.Avg':<13} {'LatSuc.P95':<13} {'LatSuc.Min':<13} {'LatSuc.Max':<13} "
        f"{'LatErr.Avg':<13} {'LatErr.P95':<13} {'LatErr.Min':<13} {'LatErr.Max':<13}"
    )
    print("-" * 180)

    for _, row in df_stats.iterrows():
        print(
            f"{int(row['num_workers']):<8} "
            f"{int(row['total_transactions']):<8} "
            f"{int(row['successful_txs']):<8} "
            f"{int(row['failed_txs']):<8} "
            f"{_fmt(row['success_rate_pct']):<8} "
            f"{_fmt(row['attempted_throughput_tx_s']):<10} "
            f"{_fmt(row['throughput_tx_s']):<10} "
            f"{_fmt(row['effective_throughput_tx_s']):<10} "
            # Latências de sucesso
            f"{_fmt(row.get('success_avg_latency_ms')):<13} "
            f"{_fmt(row.get('success_p95_latency_ms')):<13} "
            f"{_fmt(row.get('success_min_latency_ms')):<13} "
            f"{_fmt(row.get('success_max_latency_ms')):<13} "
            # Latências de erro
            f"{_fmt(row.get('error_avg_latency_ms')):<13} "
            f"{_fmt(row.get('error_p95_latency_ms')):<13} "
            f"{_fmt(row.get('error_min_latency_ms')):<13} "
            f"{_fmt(row.get('error_max_latency_ms')):<13}"
        )

    print("-" * 180)


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de entrada
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("🔬 INICIANDO ANÁLISE DE RESULTADOS e2...")
    results = load_test_results(".", experiment="e2")

    if not results:
        return

    df_stats = calculate_aggregate_stats(results)

    save_brazilian_csv(df_stats, "e2_comparison_summary_br.csv")
    print_summary_table(df_stats)

    print("\n✅ Análise concluída com sucesso!")


if __name__ == "__main__":
    main()