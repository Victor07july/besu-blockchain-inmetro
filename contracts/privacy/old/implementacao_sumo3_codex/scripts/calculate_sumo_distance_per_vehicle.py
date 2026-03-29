#!/usr/bin/env python3
"""
Calcula distancias por vehicle_id a partir de CSV de steps do SUMO.

Uso:
  python3 calculate_sumo_distance_per_vehicle.py <input_csv> [output_csv]

Saida (por veiculo):
  - distance_last_km: ultimo valor da coluna distance
  - distance_max_km: maior valor da coluna distance
  - distance_sum_km: soma bruta da coluna distance
  - distance_delta_sum_km: soma dos incrementos positivos consecutivos
  - monotonic_ratio_percent: percentual de passos nao decrescentes
"""

import sys
import pandas as pd


DEFAULT_INPUT = "../data/vehicles_step.csv"
DEFAULT_OUTPUT = "../data/vehicles_distance_summary.csv"


def compute_vehicle_distances(df: pd.DataFrame) -> pd.DataFrame:
    """Gera resumo de distancia por vehicle_id."""
    required_cols = {"vehicle_id", "distance"}
    missing = required_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")

    # Mantem ordem original para evitar artefatos com timestamps iguais.
    df = df.copy()
    df["_row_order"] = range(len(df))

    # Se houver colunas de tempo, usa ordenacao estavel; senao usa ordem original.
    sort_cols = [c for c in ["start_time", "end_time"] if c in df.columns]
    if sort_cols:
        sort_cols.append("_row_order")
    else:
        sort_cols = ["_row_order"]

    df = df.sort_values(sort_cols, kind="mergesort")
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce")

    rows = []
    for vehicle_id, group in df.groupby("vehicle_id", sort=True):
        distances = group["distance"].dropna()
        if distances.empty:
            rows.append(
                {
                    "vehicle_id": vehicle_id,
                    "num_rows": len(group),
                    "distance_last_km": 0.0,
                    "distance_max_km": 0.0,
                    "distance_sum_km": 0.0,
                    "distance_delta_sum_km": 0.0,
                    "negative_jumps": 0,
                    "monotonic_ratio_percent": 0.0,
                }
            )
            continue

        diffs = distances.diff().fillna(0.0)
        negative_jumps = int((diffs < 0).sum())
        non_decreasing = int((diffs >= 0).sum())
        monotonic_ratio = (non_decreasing / len(diffs)) * 100 if len(diffs) > 0 else 0.0

        rows.append(
            {
                "vehicle_id": vehicle_id,
                "num_rows": len(group),
                "distance_last_km": float(distances.iloc[-1]),
                "distance_max_km": float(distances.max()),
                "distance_sum_km": float(distances.sum()),
                "distance_delta_sum_km": float(diffs.clip(lower=0).sum()),
                "negative_jumps": negative_jumps,
                "monotonic_ratio_percent": monotonic_ratio,
            }
        )

    summary = pd.DataFrame(rows)
    summary = summary.sort_values("vehicle_id", kind="mergesort")
    return summary


def main() -> None:
    if len(sys.argv) < 2:
        input_csv = DEFAULT_INPUT
        output_csv = DEFAULT_OUTPUT
    else:
        input_csv = sys.argv[1]
        output_csv = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    print("=" * 70)
    print("DISTANCIA SUMO POR VEICULO")
    print("=" * 70)
    print(f"Entrada: {input_csv}")
    print(f"Saida:   {output_csv}")

    df = pd.read_csv(input_csv)
    summary = compute_vehicle_distances(df)

    summary.to_csv(output_csv, index=False, float_format="%.6f")

    print("\nResumo (primeiras linhas):")
    print(summary.head(20).to_string(index=False))
    print(f"\nVeiculos analisados: {len(summary)}")
    print(f"Arquivo gerado: {output_csv}")


if __name__ == "__main__":
    main()
