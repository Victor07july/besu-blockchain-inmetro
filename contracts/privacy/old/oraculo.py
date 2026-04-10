#!/usr/bin/env python3
"""
Oraculo de privacidade por offset com alvo de diferenca percentual.

Fluxo:
1) Le CSV com pandas
2) Monta trajetoria original por veiculo
3) Gera N tentativas de offset aleatorio (+ map matching opcional)
4) Escolhe a tentativa mais proxima do alvo de privacidade
5) Gera hash auditavel da trajetoria original
6) Salva resultados e opcionalmente envia para blockchain via modulo separado
"""

import argparse
import hashlib
import json
import math
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from hd_wallet import build_vehicle_private_keys, load_mnemonic_from_file

try:
	import osmnx as ox
	from shapely.geometry import Point

	MAP_MATCHING_AVAILABLE = True
except ImportError:
	MAP_MATCHING_AVAILABLE = False


EARTH_RADIUS_KM = 6371.0
DEFAULT_MAX_TARGET_ERROR_PERCENT = 5.0


def progress_print(message: str) -> None:
	"""Impressao com flush para acompanhamento em tempo real."""
	print(message, flush=True)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	lat1_rad = math.radians(lat1)
	lon1_rad = math.radians(lon1)
	lat2_rad = math.radians(lat2)
	lon2_rad = math.radians(lon2)

	dlat = lat2_rad - lat1_rad
	dlon = lon2_rad - lon1_rad

	a = (
		math.sin(dlat / 2.0) ** 2
		+ math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2.0) ** 2
	)
	c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
	return EARTH_RADIUS_KM * c


def trajectory_distance_km(points: List[List[float]]) -> float:
	if len(points) < 2:
		return 0.0

	total = 0.0
	for i in range(len(points) - 1):
		lat1, lon1 = points[i]
		lat2, lon2 = points[i + 1]
		total += haversine_km(lat1, lon1, lat2, lon2)
	return total


def generate_random_offset(max_radius_km: float, ref_lat: float) -> Tuple[float, float, float, float]:
	angle = random.uniform(0.0, 2.0 * math.pi)
	distance_km = math.sqrt(random.uniform(0.0, 1.0)) * max_radius_km

	dx_km = distance_km * math.cos(angle)
	dy_km = distance_km * math.sin(angle)

	offset_lat = dx_km / 111.32
	cos_lat = math.cos(math.radians(ref_lat))
	offset_lon = dy_km / (111.32 * cos_lat) if cos_lat != 0 else 0.0

	return offset_lat, offset_lon, distance_km, math.degrees(angle)


def normalize_point(point: List[float], decimals: int = 7) -> List[float]:
	return [round(float(point[0]), decimals), round(float(point[1]), decimals)]


def build_audit_hash(vehicle_id: str, trajectory_original: List[List[float]]) -> str:
	payload = {
		"vehicle_id": vehicle_id,
		"trajectory_original": [normalize_point(p) for p in trajectory_original],
	}
	canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_columns(df: pd.DataFrame) -> Dict[str, Optional[str]]:
	cols = set(df.columns)

	def pick(candidates: List[str]) -> Optional[str]:
		for c in candidates:
			if c in cols:
				return c
		return None

	return {
		"vehicle_id": pick(["vehicle_id", "veh_id", "vehicle", "id", "vin"]),
		"time": pick(["time", "timestamp", "start_time", "step"]),
		"end_time": pick(["end_time"]),
		"lat": pick(["lat", "latitude", "start_lat"]),
		"lon": pick(["lon", "lng", "longitude", "start_lon"]),
		"end_lat": pick(["end_lat"]),
		"end_lon": pick(["end_lon"]),
		"distance": pick(["distance", "total_distance_km"]),
	}


def extract_cumulative_distance_max(group: pd.DataFrame, col_name: Optional[str]) -> Optional[float]:
	if not col_name or col_name not in group.columns:
		return None
	series = pd.to_numeric(group[col_name], errors="coerce")
	if not series.notna().any():
		return None
	return float(series.max())


def build_trajectory_from_group(group: pd.DataFrame, columns: Dict[str, Optional[str]]) -> List[List[float]]:
	lat_col = columns["lat"]
	lon_col = columns["lon"]
	end_lat_col = columns["end_lat"]
	end_lon_col = columns["end_lon"]

	if lat_col is None or lon_col is None:
		return []

	points: List[List[float]] = []
	for _, row in group.iterrows():
		lat = row.get(lat_col)
		lon = row.get(lon_col)
		if pd.notna(lat) and pd.notna(lon):
			points.append([float(lat), float(lon)])

	if end_lat_col and end_lon_col and not group.empty:
		last = group.iloc[-1]
		end_lat = last.get(end_lat_col)
		end_lon = last.get(end_lon_col)
		if pd.notna(end_lat) and pd.notna(end_lon):
			end_point = [float(end_lat), float(end_lon)]
			if not points or points[-1] != end_point:
				points.append(end_point)

	return points


def get_road_graph(center_lat: float, center_lon: float, search_radius_m: int):
	if not MAP_MATCHING_AVAILABLE:
		return None
	return ox.graph_from_point((center_lat, center_lon), dist=search_radius_m, network_type="drive", simplify=False)


def snap_point_to_road(graph, lat: float, lon: float) -> List[float]:
	if graph is None or not MAP_MATCHING_AVAILABLE:
		return [lat, lon]

	try:
		u, v, key = ox.distance.nearest_edges(graph, X=lon, Y=lat)
		edge_geom = graph.edges[u, v, key].get("geometry")
		if edge_geom is not None:
			projected = edge_geom.interpolate(edge_geom.project(Point(lon, lat)))
			return [float(projected.y), float(projected.x)]

		node = ox.distance.nearest_nodes(graph, X=lon, Y=lat)
		return [float(graph.nodes[node]["y"]), float(graph.nodes[node]["x"])]
	except Exception:
		return [lat, lon]


def apply_offset(points: List[List[float]], offset_lat: float, offset_lon: float) -> List[List[float]]:
	return [[p[0] + offset_lat, p[1] + offset_lon] for p in points]


def maybe_map_match(points: List[List[float]], enabled: bool, search_radius_m: int) -> List[List[float]]:
	if not enabled or not points:
		return points

	if not MAP_MATCHING_AVAILABLE:
		return points

	center_lat = sum(p[0] for p in points) / len(points)
	center_lon = sum(p[1] for p in points) / len(points)

	try:
		graph = get_road_graph(center_lat, center_lon, search_radius_m)
	except Exception:
		return points

	return [snap_point_to_road(graph, p[0], p[1]) for p in points]


def privacy_diff_percent(orig_km: float, private_km: float) -> float:
	if orig_km <= 0:
		return 0.0
	return ((private_km - orig_km) / orig_km) * 100.0


def evaluate_attempts(
	vehicle_id: str,
	trajectory_original: List[List[float]],
	sumo_distance_km: Optional[float],
	attempts: int,
	target_percent: float,
	max_radius_km: float,
	enable_map_matching: bool,
	search_radius_m: int,
	progress_every: int,
) -> Dict:
	orig_km = trajectory_distance_km(trajectory_original)
	if not trajectory_original:
		raise ValueError(f"Trajetoria vazia para {vehicle_id}")

	ref_lat = sum(p[0] for p in trajectory_original) / len(trajectory_original)
	tries: List[Dict] = []
	started = time.monotonic()

	progress_print(
		f"[{vehicle_id}] Iniciando busca do melhor offset: "
		f"{attempts} tentativas | alvo={target_percent:.2f}% | map_matching={enable_map_matching}"
	)

	for i in range(1, attempts + 1):
		if i == 1 or i == attempts or i % progress_every == 0:
			elapsed_s = int(time.monotonic() - started)
			if tries:
				best_so_far = min(tries, key=lambda x: x["error_to_target_percent"])
				best_err = best_so_far["error_to_target_percent"]
				best_diff = best_so_far["distance"]["abs_diff_percent"]
				progress_print(
					f"[{vehicle_id}] Tentativa {i}/{attempts} | "
					f"melhor_abs_diff={best_diff:.2f}% | melhor_erro={best_err:.2f}% | {elapsed_s}s"
				)
			else:
				progress_print(f"[{vehicle_id}] Tentativa {i}/{attempts} | iniciando... | {elapsed_s}s")

		offset_lat, offset_lon, offset_dist_km, offset_angle_deg = generate_random_offset(max_radius_km, ref_lat)
		offset_points = apply_offset(trajectory_original, offset_lat, offset_lon)
		private_points = maybe_map_match(offset_points, enable_map_matching, search_radius_m)

		private_km = trajectory_distance_km(private_points)
		diff = privacy_diff_percent(orig_km, private_km)
		abs_diff = abs(diff)
		error_to_target = abs(abs_diff - target_percent)

		tries.append(
			{
				"attempt": i,
				"offset": {
					"offset_lat_deg": offset_lat,
					"offset_lon_deg": offset_lon,
					"distance_km": offset_dist_km,
					"angle_deg": offset_angle_deg,
				},
				"distance": {
					"original_km": orig_km,
					"private_km": private_km,
					"diff_percent": diff,
					"abs_diff_percent": abs_diff,
				},
				"error_to_target_percent": error_to_target,
				"trajectory_private": [normalize_point(p) for p in private_points],
			}
		)

	best = min(tries, key=lambda x: x["error_to_target_percent"])
	total_elapsed_s = int(time.monotonic() - started)
	progress_print(
		f"[{vehicle_id}] Concluido: melhor tentativa={best['attempt']} | "
		f"abs_diff={best['distance']['abs_diff_percent']:.2f}% | "
		f"erro_alvo={best['error_to_target_percent']:.2f}% | {total_elapsed_s}s"
	)
	audit_hash = build_audit_hash(vehicle_id, trajectory_original)

	result = {
		"vehicle_id": vehicle_id,
		"timestamp_utc": datetime.utcnow().isoformat() + "Z",
		"audit": {
			"original_hash_sha256": audit_hash,
			"hash_algorithm": "SHA-256",
		},
		"privacy": {
			"target_percent": target_percent,
			"best_diff_percent": best["distance"]["diff_percent"],
			"best_abs_diff_percent": best["distance"]["abs_diff_percent"],
			"error_to_target_percent": best["error_to_target_percent"],
		},
		"distance": {
			"sumo_km": sumo_distance_km,
			"original_km": best["distance"]["original_km"],
			"private_km": best["distance"]["private_km"],
		},
		"trajectory": {
			"original": [normalize_point(p) for p in trajectory_original],
			"private": best["trajectory_private"],
			"private_json": json.dumps(best["trajectory_private"], ensure_ascii=True, separators=(",", ":")),
		},
		"best_attempt": {
			"attempt": best["attempt"],
			"offset": best["offset"],
		},
		"attempts": tries,
	}
	return result


def process_csv(
	input_csv: str,
	attempts: int,
	target_percent: float,
	max_radius_km: float,
	vehicle_id_filter: Optional[str],
	enable_map_matching: bool,
	search_radius_m: int,
	progress_every: int,
) -> List[Dict]:
	progress_print(f"Lendo CSV: {input_csv}")
	df = pd.read_csv(input_csv)
	columns = detect_columns(df)

	if columns["lat"] is None or columns["lon"] is None:
		raise ValueError("Nao foi possivel identificar colunas de latitude/longitude no CSV")

	if columns["time"] is not None:
		df["_sort_time"] = pd.to_numeric(df[columns["time"]], errors="coerce")
	else:
		df["_sort_time"] = 0

	if columns["end_time"] is not None:
		df["_sort_end_time"] = pd.to_numeric(df[columns["end_time"]], errors="coerce")
	else:
		df["_sort_end_time"] = 0

	df["_row_order"] = range(len(df))

	vehicle_col = columns["vehicle_id"]
	if vehicle_col is None:
		df["_vehicle_id"] = "veh0"
		vehicle_col = "_vehicle_id"

	if vehicle_id_filter:
		df = df[df[vehicle_col].astype(str) == str(vehicle_id_filter)]

	if df.empty:
		raise ValueError("Nenhum dado encontrado apos filtros")

	results: List[Dict] = []
	total_groups = df[vehicle_col].nunique()
	progress_print(
		f"Veiculos para processar: {total_groups} | "
		f"tentativas_por_veiculo={attempts} | map_matching={enable_map_matching}"
	)

	for idx, (vehicle_id, group) in enumerate(df.groupby(vehicle_col), start=1):
		progress_print(f"\n[{idx}/{total_groups}] Veiculo {vehicle_id}: preparando trajetoria...")
		group = group.sort_values(by=["_sort_time", "_sort_end_time", "_row_order"], kind="mergesort")
		trajectory_original = build_trajectory_from_group(group, columns)
		if len(trajectory_original) < 2:
			progress_print(f"[{vehicle_id}] Ignorado: trajetoria com menos de 2 pontos.")
			continue

		sumo_distance_km = extract_cumulative_distance_max(group, columns["distance"])

		result = evaluate_attempts(
			vehicle_id=str(vehicle_id),
			trajectory_original=trajectory_original,
			sumo_distance_km=sumo_distance_km,
			attempts=attempts,
			target_percent=target_percent,
			max_radius_km=max_radius_km,
			enable_map_matching=enable_map_matching,
			search_radius_m=search_radius_m,
			progress_every=progress_every,
		)
		results.append(result)

	if not results:
		raise ValueError("Nenhuma trajetoria valida foi processada")

	return results


def confirm_large_target_error(
	results: List[Dict],
	max_target_error_percent: float,
) -> bool:
	"""
	Valida proximidade do alvo e pede confirmacao quando erro excede limite.

	Retorna True para continuar e False para abortar.
	"""
	exceeded = [
		r
		for r in results
		if float(r["privacy"]["error_to_target_percent"]) > float(max_target_error_percent)
	]

	if not exceeded:
		return True

	print("=" * 70)
	print("AVISO: NAO FOI POSSIVEL ATINGIR O ALVO DE PRIVACIDADE DENTRO DO LIMITE")
	print("=" * 70)
	print(f"Limite configurado de erro para o alvo: {max_target_error_percent:.2f}%")
	print(f"Veiculos fora do limite: {len(exceeded)}")

	for r in exceeded:
		privacy = r["privacy"]
		best_attempt = r["best_attempt"]
		offset = best_attempt["offset"]
		print("-" * 70)
		print(f"Veiculo: {r['vehicle_id']}")
		print(f"Alvo solicitado: {privacy['target_percent']:.2f}%")
		print(f"Melhor diferenca encontrada: {privacy['best_abs_diff_percent']:.2f}%")
		print(f"Erro para o alvo: {privacy['error_to_target_percent']:.2f}%")
		print(
			"Offset mais proximo encontrado: "
			f"lat={offset['offset_lat_deg']:.8f}, "
			f"lon={offset['offset_lon_deg']:.8f}, "
			f"dist={offset['distance_km']:.4f} km, "
			f"angulo={offset['angle_deg']:.2f}"
		)

	while True:
		answer = input("Deseja continuar mesmo assim? [s/N]: ").strip().lower()
		if answer in ("s", "sim", "y", "yes"):
			return True
		if answer in ("", "n", "nao", "não", "no"):
			return False
		print("Resposta invalida. Digite 's' para continuar ou 'n' para abortar.")


def save_outputs(results: List[Dict], output_dir: str) -> Tuple[str, str]:
	os.makedirs(output_dir, exist_ok=True)

	result_json = os.path.join(output_dir, "oraculo_resultados.json")
	summary_csv = os.path.join(output_dir, "oraculo_resumo.csv")
	trajectories_json = os.path.join(output_dir, "oraculo_trajectories.json")
	distance_analysis_csv = os.path.join(output_dir, "oraculo_distance_analysis.csv")

	with open(result_json, "w", encoding="utf-8") as f:
		json.dump(results, f, ensure_ascii=False, indent=2)

	# JSON no formato esperado por visualize_trips.py
	trajectories_payload = []
	for r in results:
		trajectory_original = r["trajectory"]["original"]
		trajectory_private = r["trajectory"]["private"]
		trajectories_payload.append(
			{
				"vin": r["vehicle_id"],
				"model": "ORACLE_OFFSET",
				"fuel_type": "N/A",
				"start_time": r["timestamp_utc"],
				"end_time": r["timestamp_utc"],
				"total_distance_km": (
					r["distance"]["sumo_km"]
					if r["distance"]["sumo_km"] is not None
					else r["distance"]["original_km"]
				),
				"co2_real_g": 0.0,
				"delta_co2_g": 0.0,
				"valor_e1_reais": 0.0,
				"trajectory_original": trajectory_original,
				"trajectory_private": trajectory_private,
				"trajectory_times": [],
				"num_points": min(len(trajectory_original), len(trajectory_private)),
				"run_id": int(r["best_attempt"]["attempt"]),
			}
		)

	with open(trajectories_json, "w", encoding="utf-8") as f:
		json.dump(trajectories_payload, f, ensure_ascii=False, indent=2)

	rows = []
	analysis_rows = []
	for r in results:
		rows.append(
			{
				"vehicle_id": r["vehicle_id"],
				"target_percent": r["privacy"]["target_percent"],
				"sumo_km": r["distance"]["sumo_km"],
				"best_diff_percent": r["privacy"]["best_diff_percent"],
				"error_to_target_percent": r["privacy"]["error_to_target_percent"],
				"original_km": r["distance"]["original_km"],
				"private_km": r["distance"]["private_km"],
				"best_attempt": r["best_attempt"]["attempt"],
				"offset_distance_km": r["best_attempt"]["offset"]["distance_km"],
				"offset_angle_deg": r["best_attempt"]["offset"]["angle_deg"],
				"audit_hash_sha256": r["audit"]["original_hash_sha256"],
			}
		)

		analysis_rows.append(
			{
				"VIN": r["vehicle_id"],
				"Distancia_SUMO_km": r["distance"]["sumo_km"],
				"Distancia_Trajeto_Original_km": r["distance"]["original_km"],
				"Distancia_Trajeto_com_Offset_km": r["distance"]["private_km"],
				"Diferenca_Distancia_km": r["distance"]["private_km"] - r["distance"]["original_km"],
				"Diferenca_Distancia_Percentual": r["privacy"]["best_diff_percent"],
				"Alvo_Privacidade_Percentual": r["privacy"]["target_percent"],
				"Erro_para_Alvo_Percentual": r["privacy"]["error_to_target_percent"],
				"Num_Pontos_Trajeto_Original": len(r["trajectory"]["original"]),
				"Num_Pontos_Trajeto_com_Offset": len(r["trajectory"]["private"]),
				"Offset_X_Graus": r["best_attempt"]["offset"]["offset_lat_deg"],
				"Offset_Y_Graus": r["best_attempt"]["offset"]["offset_lon_deg"],
				"Offset_Distance_km": r["best_attempt"]["offset"]["distance_km"],
				"Offset_Angulo_Graus": r["best_attempt"]["offset"]["angle_deg"],
				"Hash_Auditoria_SHA256": r["audit"]["original_hash_sha256"],
			}
		)

	pd.DataFrame(rows).to_csv(summary_csv, index=False, sep=";", decimal=",")
	pd.DataFrame(analysis_rows).to_csv(distance_analysis_csv, index=False, sep=";", decimal=",")

	print(f"Trajetorias JSON (visualize_trips): {trajectories_json}")
	print(f"Analise de distancia CSV: {distance_analysis_csv}")

	return result_json, summary_csv


def main() -> None:
	parser = argparse.ArgumentParser(description="Oraculo de offset orientado por alvo de privacidade")
	parser.add_argument("input_csv", help="CSV de entrada")
	parser.add_argument("--attempts", type=int, default=100, help="Quantidade de tentativas de offset")
	parser.add_argument(
		"--target-privacy-percent",
		type=float,
		required=True,
		help="Alvo de diferenca percentual absoluta entre distancia privada e original",
	)
	parser.add_argument("--max-radius-km", type=float, default=2.0, help="Raio maximo do offset")
	parser.add_argument("--vehicle-id", type=str, default=None, help="Filtra um veiculo especifico")
	parser.add_argument(
		"--enable-map-matching",
		action="store_true",
		help="Ativa snap para malha viaria (se osmnx estiver instalado)",
	)
	parser.add_argument("--search-radius-m", type=int, default=1500, help="Raio de busca da malha viaria")
	parser.add_argument(
		"--progress-every",
		type=int,
		default=5,
		help="Exibe progresso a cada N tentativas (padrao: 5)",
	)
	parser.add_argument(
		"--max-target-error-percent",
		type=float,
		default=DEFAULT_MAX_TARGET_ERROR_PERCENT,
		help="Erro maximo permitido em relacao ao alvo de privacidade antes de pedir confirmacao",
	)
	parser.add_argument("--seed", type=int, default=None, help="Seed aleatoria para reproducibilidade")
	parser.add_argument("--output-dir", default="../data/oraculo_offset", help="Diretorio de saida")

	parser.add_argument("--send-onchain", action="store_true", help="Envia melhor resultado para blockchain")
	parser.add_argument("--deployment-file", default="../deployment_info.json", help="JSON deployment")
	parser.add_argument("--private-key", default=None, help="Chave privada da conta oracle")
	parser.add_argument(
		"--use-hd-wallets",
		action="store_true",
		help="Deriva pseudonimos via HD wallet (uma conta por vehicle_id)",
	)
	parser.add_argument(
		"--seed-file",
		default="seed.txt",
		help="Arquivo TXT com mnemonic BIP-39 para derivacao HD",
	)
	parser.add_argument(
		"--hd-account-path-template",
		default="m/44'/60'/0'/0/{index}",
		help="Template do caminho HD (use {index} para indice por veiculo)",
	)
	parser.add_argument("--method-name", default="registerOracleResult", help="Metodo do contrato")
	parser.add_argument(
		"--method-arg",
		action="append",
		default=[],
		help="Arg do metodo. Literal ou caminho $.campo.subcampo no JSON",
	)

	args = parser.parse_args()

	if args.seed is not None:
		random.seed(args.seed)

	mm_enabled = args.enable_map_matching and MAP_MATCHING_AVAILABLE

	if args.enable_map_matching and not MAP_MATCHING_AVAILABLE:
		progress_print("[aviso] Map matching solicitado, mas osmnx/shapely nao estao instalados. Continuando sem map matching.")

	if args.progress_every <= 0:
		raise ValueError("--progress-every deve ser >= 1")

	progress_print("=" * 70)
	progress_print("ORACULO OFFSET - INICIO")
	progress_print("=" * 70)
	progress_print(f"CSV: {args.input_csv}")
	progress_print(f"attempts={args.attempts} | target={args.target_privacy_percent:.2f}% | raio={args.max_radius_km} km")
	progress_print(f"map_matching={mm_enabled} | search_radius_m={args.search_radius_m} | progress_every={args.progress_every}")

	results = process_csv(
		input_csv=args.input_csv,
		attempts=args.attempts,
		target_percent=args.target_privacy_percent,
		max_radius_km=args.max_radius_km,
		vehicle_id_filter=args.vehicle_id,
		enable_map_matching=mm_enabled,
		search_radius_m=args.search_radius_m,
		progress_every=args.progress_every,
	)

	if not confirm_large_target_error(results, args.max_target_error_percent):
		progress_print("Execucao cancelada pelo usuario devido ao limite de erro para o alvo.")
		return

	result_json, summary_csv = save_outputs(results, args.output_dir)

	progress_print("=" * 70)
	progress_print("ORACULO OFFSET FINALIZADO")
	progress_print("=" * 70)
	progress_print(f"Veiculos processados: {len(results)}")
	progress_print(f"Resultados JSON: {result_json}")
	progress_print(f"Resumo CSV: {summary_csv}")

	if args.send_onchain:
		if not args.private_key and not args.use_hd_wallets:
			raise ValueError("Use --private-key ou --use-hd-wallets quando --send-onchain for usado")
		if not args.method_arg:
			raise ValueError("--method-arg e obrigatorio quando --send-onchain for usado")

		from blockchain_sender import send_oracle_results

		private_keys_by_vehicle = None
		if args.use_hd_wallets:
			mnemonic = load_mnemonic_from_file(args.seed_file)

			indices_by_vehicle: Dict[str, int] = {}
			for r in results:
				vehicle_id = str(r["vehicle_id"])
				audit_hash = str(r["audit"]["original_hash_sha256"])
				idx = int(audit_hash[:8], 16)
				indices_by_vehicle[vehicle_id] = idx

			vehicle_ids = [str(r["vehicle_id"]) for r in results]
			private_keys_by_vehicle, addresses_by_vehicle = build_vehicle_private_keys(
				vehicle_ids=vehicle_ids,
				mnemonic=mnemonic,
				vehicle_indices=indices_by_vehicle,
				account_path_template=args.hd_account_path_template,
			)
			progress_print(
				f"HD wallets derivados para {len(addresses_by_vehicle)} veiculos via {args.seed_file} "
				f"(template={args.hd_account_path_template}, indice=hash[audit_hash[:8]])"
			)

		txs = send_oracle_results(
			results=results,
			deployment_file=args.deployment_file,
			private_key=args.private_key,
			method_name=args.method_name,
			method_args_spec=args.method_arg,
			private_keys_by_vehicle=private_keys_by_vehicle,
		)
		progress_print(f"Transacoes enviadas: {len(txs)}")


if __name__ == "__main__":
	main()
