#!/usr/bin/env python3
"""Analisa distribuicao da diferenca de distancia e gera grafico em PDF."""

import argparse
import os
from typing import List

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_BINS_KM = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
DIFF_COLUMN_CANDIDATES = [
    "Diferenca_Distancia_km",
    "distance_diff_km",
    "distance_difference_km",
    "Distancia_Trajeto_com_Offset_km_minus_Original",
]


def find_diff_column(columns: List[str]) -> str:
    col_set = set(columns)
    for name in DIFF_COLUMN_CANDIDATES:
        if name in col_set:
            return name

    for col in columns:
        col_norm = col.lower()
        if "diferenca" in col_norm and "distancia" in col_norm and "km" in col_norm:
            return col

    raise ValueError(
        "Nao foi possivel identificar coluna de diferenca de distancia (km). "
        f"Candidatas testadas: {DIFF_COLUMN_CANDIDATES}"
    )


def parse_bins(raw: str) -> List[float]:
    if not raw.strip():
        return DEFAULT_BINS_KM

    values = []
    for token in raw.split(","):
        token = token.strip()
        if token:
            values.append(float(token))

    values = sorted(v for v in values if v > 0)
    return values if values else DEFAULT_BINS_KM


def build_distribution(abs_series: pd.Series, bins_km: List[float]) -> pd.DataFrame:
    rows = []
    total = len(abs_series)
    lower = 0.0

    for upper in bins_km:
        mask = (abs_series >= lower) & (abs_series < upper)
        count = int(mask.sum())
        rows.append(
            {
                "faixa_abs_km": f"[{lower:.4f}, {upper:.4f})",
                "limite_inferior_km": lower,
                "limite_superior_km": upper,
                "quantidade": count,
                "percentual": (count / total * 100.0) if total else 0.0,
            }
        )
        lower = upper

    mask_last = abs_series >= lower
    count_last = int(mask_last.sum())
    rows.append(
        {
            "faixa_abs_km": f">= {lower:.4f}",
            "limite_inferior_km": lower,
            "limite_superior_km": None,
            "quantidade": count_last,
            "percentual": (count_last / total * 100.0) if total else 0.0,
        }
    )

    return pd.DataFrame(rows)


def save_pdf_chart(
    output_pdf: str,
    dist_df: pd.DataFrame,
    mean_signed: float,
    median_signed: float,
    mean_abs: float,
    median_abs: float,
    input_csv: str,
    diff_col: str,
    total: int,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 7))

    labels = dist_df["faixa_abs_km"].tolist()
    counts = dist_df["quantidade"].astype(int).tolist()

    bars = ax.bar(range(len(labels)), counts, color="#2E86AB", edgecolor="#1B4F72")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Quantidade de trajetorias")
    ax.set_xlabel("Faixas da diferenca absoluta (km)")
    ax.set_title("Distribuicao da diferenca de distancia (quanto mais perto de 0, mais proximo do original)")

    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(count),
            ha="center",
            va="bottom",
            fontsize=9,
        )

    stats_text = (
        f"Arquivo: {input_csv}\n"
        f"Coluna: {diff_col}\n"
        f"Registros validos: {total}\n\n"
        f"Media (assinada): {mean_signed:.6f} km\n"
        f"Mediana (assinada): {median_signed:.6f} km\n"
        f"Media (absoluta): {mean_abs:.6f} km\n"
        f"Mediana (absoluta): {median_abs:.6f} km"
    )
    fig.text(
        0.68,
        0.95,
        stats_text,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "#F8F9FA", "edgecolor": "#CED4DA"},
    )

    fig.tight_layout(rect=[0, 0, 0.98, 0.90])
    fig.savefig(output_pdf, format="pdf", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calcula distribuicao da diferenca de distancia (trajeto original vs com offset), "
            "inclui media/mediana e gera grafico PDF."
        )
    )
    parser.add_argument("input_csv", help="CSV de entrada com coluna de diferenca de distancia")
    parser.add_argument(
        "--output-csv",
        default=None,
        help="CSV de saida com distribuicao por faixas (padrao: <input>_distribution.csv)",
    )
    parser.add_argument(
        "--output-pdf",
        default=None,
        help="PDF de saida com grafico (padrao: <input>_distribution.pdf)",
    )
    parser.add_argument(
        "--bins-km",
        default=",".join(str(v) for v in DEFAULT_BINS_KM),
        help="Faixas absolutas em km separadas por virgula (ex: 0.01,0.05,0.1,0.2,0.5,1)",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv, sep=";", dtype=str)
    diff_col = find_diff_column(df.columns.tolist())

    diff_series = pd.to_numeric(df[diff_col].astype(str).str.replace(",", ".", regex=False), errors="coerce").dropna()
    if diff_series.empty:
        raise ValueError("A coluna de diferenca de distancia nao possui valores numericos validos")

    abs_series = diff_series.abs()
    mean_signed = float(diff_series.mean())
    median_signed = float(diff_series.median())
    mean_abs = float(abs_series.mean())
    median_abs = float(abs_series.median())

    bins_km = parse_bins(args.bins_km)
    dist_df = build_distribution(abs_series, bins_km)

    base, _ = os.path.splitext(args.input_csv)
    output_csv = args.output_csv or f"{base}_distribution.csv"
    output_pdf = args.output_pdf or f"{base}_distribution.pdf"

    dist_df.to_csv(output_csv, index=False, sep=";", decimal=",")
    save_pdf_chart(
        output_pdf=output_pdf,
        dist_df=dist_df,
        mean_signed=mean_signed,
        median_signed=median_signed,
        mean_abs=mean_abs,
        median_abs=median_abs,
        input_csv=args.input_csv,
        diff_col=diff_col,
        total=len(diff_series),
    )

    print("=" * 70)
    print("DISTRIBUICAO DA DIFERENCA DE DISTANCIA")
    print("=" * 70)
    print(f"Arquivo: {args.input_csv}")
    print(f"Coluna usada: {diff_col}")
    print(f"Registros validos: {len(diff_series)}")
    print("\nEstatisticas (diferenca assinada, km):")
    print(f"- Media:   {mean_signed:.6f}")
    print(f"- Mediana: {median_signed:.6f}")
    print("\nEstatisticas (diferenca absoluta, km):")
    print(f"- Media:   {mean_abs:.6f}")
    print(f"- Mediana: {median_abs:.6f}")
    print("\nQuanto mais perto de 0 na diferenca absoluta, mais proximo do trajeto original.")
    print(f"Distribuicao CSV: {output_csv}")
    print(f"Grafico PDF: {output_pdf}")


if __name__ == "__main__":
    main()
