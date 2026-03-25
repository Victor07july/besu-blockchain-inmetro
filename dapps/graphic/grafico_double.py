import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


FONT_SIZE_LABEL = 13
FONT_SIZE_TICKS = 11
FONT_SIZE_LEGEND = 11
FONT_SIZE_TITLE = 14


def apply_black_border(ax) -> None:
	for spine in ax.spines.values():
		spine.set_visible(True)
		spine.set_color("black")
		spine.set_linewidth(1.5)


def parse_mixed_number(value):
	"""Parse numeric values that may use pt-BR or en-US separators."""
	if pd.isna(value):
		return pd.NA

	text = str(value).strip()
	if not text:
		return pd.NA

	if "," in text and "." in text:
		# Assume format like 2.296,70 -> 2296.70
		text = text.replace(".", "").replace(",", ".")
	elif "," in text:
		# Assume format like 2,30 -> 2.30
		text = text.replace(",", ".")

	return pd.to_numeric(text, errors="coerce")


def load_and_prepare_data(csv_path: Path) -> pd.DataFrame:
	df = pd.read_csv(csv_path)

	required_cols = ["num_workers", "avg_latency_s", "throughput_tx_s"]
	missing = [col for col in required_cols if col not in df.columns]
	if missing:
		raise ValueError(f"Missing required columns: {missing}")

	for col in required_cols:
		df[col] = df[col].map(parse_mixed_number)

	df = df.dropna(subset=required_cols).sort_values(by="num_workers")
	return df


def resolve_title(csv_path: Path) -> str:
	title_by_stem = {
		"comparison_ec2old": "Baseline EC2",
		"comparison_ec2new": "Optimized EC2",
	}
	return title_by_stem.get(csv_path.stem, csv_path.stem)


def plot_dataset(ax, df: pd.DataFrame, title: str) -> None:
	workers = df["num_workers"].round().astype(int)

	ax.plot(
		workers,
		df["avg_latency_s"],
		marker="o",
		linewidth=2,
		color="#1f77b4",
		label="Latency (s)",
	)
	ax.plot(
		workers,
		df["throughput_tx_s"],
		marker="s",
		linewidth=2,
		color="#d62728",
		label="Throughput (s)",
	)

	ax.set_xlabel("Number of Workers", fontsize=FONT_SIZE_LABEL)
	ax.set_ylabel("Seconds", fontsize=FONT_SIZE_LABEL)
	ax.set_xscale("log", base=2)
	ax.set_xticks(workers.tolist())
	ax.set_xticklabels(
		[str(w) for w in workers.tolist()],
		rotation=30,
		ha="right",
		fontsize=FONT_SIZE_TICKS,
	)
	ax.tick_params(axis="y", labelsize=FONT_SIZE_TICKS)
	ax.grid(True, linestyle="--", alpha=0.4)
	ax.legend(loc="upper left", fontsize=FONT_SIZE_LEGEND)
	ax.set_title(title, fontsize=FONT_SIZE_TITLE)
	apply_black_border(ax)


def plot_comparison(
	df_left: pd.DataFrame,
	df_right: pd.DataFrame,
	left_title: str,
	right_title: str,
	output_path: Path,
	show: bool,
) -> None:
	fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 6), sharey=True)
	plot_dataset(axes[0], df_left, left_title)
	plot_dataset(axes[1], df_right, right_title)

	plt.tight_layout()
	plt.savefig(output_path, dpi=150)

	if show:
		plt.show()
	else:
		plt.close(fig)


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Compare latency and throughput from two CSV files side by side."
	)
	parser.add_argument(
		"--input-left",
		default="comparison_ec2old.csv",
		help="Left chart CSV path.",
	)
	parser.add_argument(
		"--input-right",
		default="comparison_ec2new.csv",
		help="Right chart CSV path.",
	)
	parser.add_argument(
		"--output",
		default="comparacao_workers.pdf",
		help="Output PDF file.",
	)
	parser.add_argument(
		"--show",
		action="store_true",
		help="Show the chart in an interactive window (if display is available).",
	)
	args = parser.parse_args()

	left_csv_path = Path(args.input_left)
	right_csv_path = Path(args.input_right)
	output_path = Path(args.output)
	if output_path.suffix.lower() != ".pdf":
		output_path = output_path.with_suffix(".pdf")

	df_left = load_and_prepare_data(left_csv_path)
	df_right = load_and_prepare_data(right_csv_path)
	plot_comparison(
		df_left,
		df_right,
		resolve_title(left_csv_path),
		resolve_title(right_csv_path),
		output_path,
		args.show,
	)

	print(f"Chart saved to: {output_path.resolve()}")


if __name__ == "__main__":
	main()
