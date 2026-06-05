#!/usr/bin/env python3
"""
Cliente local do usuario para interagir com o oraculo e com a blockchain.

0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3
0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63

python3 usuario.py ../data/trajetos/vehicles_step_sim_1.csv \
--oracle-url http://127.0.0.1:5001 \
--deployment-file deployment_info.json \
--user-private-key 0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63

python3 usuario.py ../data/trajetos/vehicles_step_sim_1.csv \
	--oracle-url http://127.0.0.1:5001 \
	--deployment-file deployment_info.json \
	--user-private-key 0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3 \
	--pseudonym-seed-file ./seed.txt \
	--pseudonym-hd-index 0

python3 usuario.py ../data/trajetos/vehicles_step_sim_1.csv \
  --oracle-url http://127.0.0.1:5001 \
  --deployment-file deployment_info.json \
  --user-private-key 0xc87509a1c067bbde78beb793e6fa76530b6382a4c0241e5e4a9ec0a0f44dc0d3 \
  --enable-map-matching \
  --search-radius-m 1500

Fluxo:
1) Le CSV local e detecta colunas automaticamente
2) Pergunta se deseja aplicar ofuscacao por offset
3) Se sim: chama API do oraculo, recebe top 5, usuario escolhe, confirma
4) Se nao: envia trajeto original direto para blockchain com carteira do usuario
"""

import argparse
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from eth_account import Account
from web3 import Web3

from blockchain_sender import load_deployment_info, send_oracle_results
from hd_wallet import DEFAULT_ACCOUNT_PATH_TEMPLATE, derive_account_from_mnemonic, load_mnemonic_from_file


EARTH_RADIUS_KM = 6371.0

DEFAULT_ROAD_GASOLINE_KM_L = 12.0
DEFAULT_CITY_GASOLINE_KM_L = 11.5
DEFAULT_CARBON_PRICE_BRL_TON = 50.0


def progress_print(message: str) -> None:
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


def normalize_point(point: List[float], decimals: int = 7) -> List[float]:
	return [round(float(point[0]), decimals), round(float(point[1]), decimals)]


def build_trajectory_hash(trajectory: List[List[float]]) -> str:
	payload = {
		"trajectory_original": [normalize_point(p) for p in trajectory],
	}
	canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
	return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def to_bytes32_hex(raw_hash: str) -> str:
	h = raw_hash.lower().replace("0x", "")
	if len(h) != 64:
		raise ValueError("Hash deve ter 64 caracteres hex")
	int(h, 16)
	return "0x" + h


def get_web3_for_user(rpc_url: str) -> Web3:
	return Web3(Web3.HTTPProvider(rpc_url))


def get_contract_instance(deployment_file: str):
	deployment = load_deployment_info(deployment_file)
	rpc_url = deployment.get("rpc_url", "http://localhost:8545")
	w3 = get_web3_for_user(rpc_url)
	if not w3.is_connected():
		raise ConnectionError(f"Nao foi possivel conectar ao RPC: {rpc_url}")
	contract = w3.eth.contract(address=deployment["contract_address"], abi=deployment["abi"])
	return w3, contract


def resolve_pseudonym_private_key(seed_file: str, hd_index: int) -> tuple[str, str]:
	if hd_index < 0:
		raise ValueError(f"Indice HD invalido (<0): {hd_index}")
	mnemonic = load_mnemonic_from_file(seed_file)
	account_path = DEFAULT_ACCOUNT_PATH_TEMPLATE.format(index=hd_index)
	address, private_key = derive_account_from_mnemonic(mnemonic, account_path)
	return address, private_key


def read_hash_onchain(deployment_file: str, token_id: int) -> str:
	_, contract = get_contract_instance(deployment_file)
	onchain_hash = contract.functions.getOriginalTrajectoryHash(token_id).call()
	if isinstance(onchain_hash, (bytes, bytearray)):
		return "0x" + bytes(onchain_hash).hex()
	return str(onchain_hash)


def verify_hash_onchain(deployment_file: str, token_id: int, local_hash: str) -> bool:
	_, contract = get_contract_instance(deployment_file)
	provided_hash = to_bytes32_hex(local_hash)
	return bool(contract.functions.verifyOriginalTrajectoryHash(token_id, provided_hash).call())


def get_next_token_id_onchain(deployment_file: str) -> int:
	_, contract = get_contract_instance(deployment_file)
	return int(contract.functions.nextTokenId().call())


def is_hash_registered_onchain(deployment_file: str, local_hash: str) -> bool:
	_, contract = get_contract_instance(deployment_file)
	provided_hash = to_bytes32_hex(local_hash)
	return bool(contract.functions.isTrajectoryHashRegistered(provided_hash).call())


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
		"distance_city": pick(["distance_city", "city_distance", "cidade_km"]),
		"distance_highway": pick(["distance_highway", "highway_distance", "estrada_km"]),
		"co2": pick(["CO2", "co2", "co2_g", "co2_emissions", "emissoes_co2"]),
	}


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


def split_city_highway(total_km: float) -> tuple[float, float]:
	return total_km * 0.4, total_km * 0.6


def pick_sum_numeric(group: pd.DataFrame, col_name: Optional[str]) -> Optional[float]:
	if not col_name or col_name not in group.columns:
		return None
	series = pd.to_numeric(group[col_name], errors="coerce").dropna()
	if series.empty:
		return None
	# Se a serie for cumulativa (monotona crescente), usar max; senao usar soma.
	if bool((series.diff().fillna(0) >= 0).all()):
		return float(series.max())
	return float(series.sum())


def build_contract_params_from_group(group: pd.DataFrame, columns: Dict[str, Optional[str]], trajectory: List[List[float]]) -> Dict[str, int]:
	total_km = trajectory_distance_km(trajectory)
	city_km_default, highway_km_default = split_city_highway(total_km)

	city_km = pick_sum_numeric(group, columns["distance_city"])
	highway_km = pick_sum_numeric(group, columns["distance_highway"])
	co2 = pick_sum_numeric(group, columns["co2"])

	if city_km is None:
		city_km = city_km_default
	if highway_km is None:
		highway_km = highway_km_default

	if co2 is None:
		co2_g = max(total_km * 120.0, 1.0)
	else:
		co2_g = co2 * 1000.0 if 0 < co2 < 1000 else co2

	return {
		"highwayDistance": int(highway_km * 1e6),
		"cityDistance": int(city_km * 1e6),
		"ethanolPercent": 0,
		"roadGasoline": int(DEFAULT_ROAD_GASOLINE_KM_L * 1e6),
		"roadEthanol": 0,
		"cityGasoline": int(DEFAULT_CITY_GASOLINE_KM_L * 1e6),
		"cityEthanol": 0,
		"realCO2Emissions": int(co2_g * 1e6),
		"carbonPricePerTon": int(DEFAULT_CARBON_PRICE_BRL_TON * 1e6),
	}


def simulate_e1_value(contract_params: Dict[str, int]) -> int:
	road_gas = int(contract_params.get("roadGasoline", 0))
	city_gas = int(contract_params.get("cityGasoline", 0))
	price = int(contract_params.get("carbonPricePerTon", 0))
	if road_gas <= 0 or city_gas <= 0 or price <= 0:
		return 0

	highway = int(contract_params.get("highwayDistance", 0))
	city = int(contract_params.get("cityDistance", 0))
	real_co2 = int(contract_params.get("realCO2Emissions", 0))

	emissao_gas = 1720 * 10**6
	p_gas = 100 * 10**6

	parte1 = (highway * emissao_gas * p_gas) // (road_gas * 100 * 10**6)
	parte2 = (city * emissao_gas * p_gas) // (city_gas * 100 * 10**6)
	meta = parte1 + parte2
	diff = meta - real_co2 if meta >= real_co2 else 0
	e1 = (diff * price) // (1_000_000 * 10**6)
	return int(e1)


def load_csv_first_vehicle(input_csv: str) -> Dict[str, Any]:
	df = pd.read_csv(input_csv)
	columns = detect_columns(df)

	if columns["lat"] is None or columns["lon"] is None:
		raise ValueError("Nao foi possivel detectar colunas de latitude/longitude")

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

	if df.empty:
		raise ValueError("CSV vazio")

	vehicle_id, group = next(iter(df.groupby(vehicle_col)))
	group = group.sort_values(by=["_sort_time", "_sort_end_time", "_row_order"], kind="mergesort")

	trajectory = build_trajectory_from_group(group, columns)
	if len(trajectory) < 2:
		raise ValueError("Trajetoria invalida (<2 pontos)")

	params = build_contract_params_from_group(group, columns, trajectory)
	traj_hash = build_trajectory_hash(trajectory)

	return {
		"vehicle_id": str(vehicle_id),
		"trajectory": trajectory,
		"hash": traj_hash,
		"contract_params": params,
	}


def print_options_table(options: List[Dict[str, Any]]) -> None:
	print("\nTop opcoes do oraculo:")
	print("idx | tentativa | diff_abs(%) | monetizacao_estimada_reais")
	print("----+----------+-------------+------------------")
	for opt in options:
		idx = opt["option_index"]
		att = opt["attempt"]
		diff_abs = opt["distance"]["abs_diff_percent"]
		reais = opt["monetizacao"]["private_final_e1_reais"]
		print(f"{idx:>3} | {att:>8} | {diff_abs:>11.4f} | {reais:>16.6f}")


def send_direct_without_offset(
	deployment_file: str,
	private_key: str,
	recipient: str,
	contract_params: Dict[str, int],
	hash_original: str,
	vehicle_id: str,
) -> Dict[str, Any]:
	estimated_micro = simulate_e1_value(contract_params)
	next_token_before = get_next_token_id_onchain(deployment_file)

	payload = [
		{
			"vehicle_id": vehicle_id,
			"contract_params": contract_params,
			"recipient": recipient,
			"original_hash": to_bytes32_hex(hash_original),
		}
	]

	tx_hashes = send_oracle_results(
		results=payload,
		deployment_file=deployment_file,
		private_key=private_key,
		method_name="calculateAndMintWithHash",
		method_args_spec=["$.contract_params", "$.recipient", "$.original_hash"],
	)

	minted_token_id = int(next_token_before)
	hash_match = verify_hash_onchain(deployment_file, minted_token_id, hash_original)
	onchain_hash = read_hash_onchain(deployment_file, minted_token_id)

	return {
		"estimated_e1_micro": estimated_micro,
		"estimated_e1_reais": round(estimated_micro / 1e6, 6),
		"minted_token_id": minted_token_id,
		"hash_match": hash_match,
		"onchain_hash": onchain_hash,
		"tx_hashes": tx_hashes,
	}


def request_redeem_by_hash(
	deployment_file: str,
	private_key: str,
	local_hash: str,
	pseudonym: str,
) -> Dict[str, Any]:
	provided_hash = to_bytes32_hex(local_hash)
	hash_registered = is_hash_registered_onchain(deployment_file, local_hash)
	if not hash_registered:
		raise ValueError("Hash nao registrado na blockchain")

	payload = [
		{
			"hash": provided_hash,
			"pseudonym": pseudonym,
		}
	]

	tx_hashes = send_oracle_results(
		results=payload,
		deployment_file=deployment_file,
		private_key=private_key,
		method_name="requestRedeemByHash",
		method_args_spec=["$.hash", "$.pseudonym"],
	)

	requester = Account.from_key(private_key).address
	return {
		"requester": requester,
		"hash": provided_hash,
		"pseudonym": pseudonym,
		"tx_hashes": tx_hashes,
	}


def main() -> None:
	parser = argparse.ArgumentParser(description="Cliente local do usuario para fluxo de privacidade")
	parser.add_argument("input_csv", nargs="?", help="CSV local com trajetoria (necessario no modo enviar)")
	parser.add_argument("--oracle-url", default="http://127.0.0.1:5000", help="URL base da API do oraculo")
	parser.add_argument("--deployment-file", required=True, help="deployment_info.json")
	parser.add_argument("--user-private-key", required=True, help="Chave privada da carteira do usuario")
	parser.add_argument("--pseudonym-private-key", default=None, help="Chave privada da carteira pseudonima")
	parser.add_argument("--pseudonym-seed-file", default=None, help="Arquivo local com a seed/mnemonic da carteira pseudonima")
	parser.add_argument("--pseudonym-hd-index", type=int, default=0, help="Indice HD usado para derivar a carteira pseudonima")
	parser.add_argument("--attempts", type=int, default=20, help="N tentativas para o oraculo")
	parser.add_argument("--enable-map-matching", action="store_true", help="Ativa map matching via OSM no oraculo")
	parser.add_argument("--search-radius-m", type=int, default=1500, help="Raio de busca para map matching no oraculo")
	parser.add_argument("--audit-token-id", type=int, default=None, help="Executa apenas auditoria de hash para um tokenId")
	args = parser.parse_args()

	progress_print("=" * 70)
	progress_print("CLIENTE USUARIO")
	progress_print("=" * 70)

	mode = input("Escolha a operacao: Enviar dados ou Resgatar? (E/R): ").strip().lower()
	if mode in ("r", "resgatar", "resgate"):
		hash_input = input("Informe o hash da trajetoria para resgate (hex): ").strip()
		hash_clean = hash_input.lower().replace("0x", "")
		if len(hash_clean) != 64:
			raise ValueError("Hash invalido. Informe 64 caracteres hex.")

		if not is_hash_registered_onchain(args.deployment_file, hash_clean):
			progress_print("Hash nao registrado na blockchain. Resgate nao pode ser solicitado.")
			return

		wallet_mode = input("Resgatar com carteira Real ou Pseudonimo? (R/P): ").strip().lower()
		if wallet_mode in ("p", "pseudonimo", "pseudonimo"):
			if args.pseudonym_seed_file:
				pseudonym_address, chosen_key = resolve_pseudonym_private_key(
					seed_file=args.pseudonym_seed_file,
					hd_index=args.pseudonym_hd_index,
				)
				progress_print(
					f"Carteira pseudonima derivada da seed no indice {args.pseudonym_hd_index}: {pseudonym_address}"
				)
			else:
				chosen_key = args.pseudonym_private_key
				if not chosen_key:
					chosen_key = input("Informe a chave privada da carteira pseudonima: ").strip()
				if not chosen_key:
					raise ValueError("Chave privada da carteira pseudonima nao informada")
			pseudonym = input("Informe o pseudonimo para registrar no evento: ").strip() or "anonimo"
		else:
			chosen_key = args.user_private_key
			pseudonym = ""

		redeem_result = request_redeem_by_hash(
			deployment_file=args.deployment_file,
			private_key=chosen_key,
			local_hash=hash_clean,
			pseudonym=pseudonym,
		)

		progress_print("\nResgate solicitado com sucesso")
		progress_print(f"Carteira emissora: {redeem_result['requester']}")
		progress_print(f"Hash usado: {redeem_result['hash']}")
		if pseudonym:
			progress_print(f"Pseudonimo: {redeem_result['pseudonym']}")
		progress_print(f"TX: {', '.join(redeem_result['tx_hashes'])}")
		return

	if not args.input_csv:
		raise ValueError("No modo enviar, informe o arquivo CSV")

	data = load_csv_first_vehicle(args.input_csv)
	user_address = Account.from_key(args.user_private_key).address
	progress_print(f"VIN: {data['vehicle_id']}")
	progress_print(f"Pontos: {len(data['trajectory'])}")
	progress_print(f"Hash: {data['hash']}")

	if args.audit_token_id is not None:
		onchain_hash = read_hash_onchain(args.deployment_file, args.audit_token_id)
		match = verify_hash_onchain(args.deployment_file, args.audit_token_id, data["hash"])
		progress_print("\nAUDITORIA MANUAL")
		progress_print(f"Token ID: {args.audit_token_id}")
		progress_print(f"Hash local:   {to_bytes32_hex(data['hash'])}")
		progress_print(f"Hash on-chain:{onchain_hash}")
		progress_print(f"Hash bate? {'SIM' if match else 'NAO'}")
		return

	answer = input("Deseja aplicar ofuscacao por Offset neste trajeto? (S/N): ").strip().lower()

	if answer in ("s", "sim", "y", "yes"):
		progress_print(
			"Modo offset: "
			+ ("map matching OSM ATIVADO" if args.enable_map_matching else "map matching OSM DESATIVADO")
		)
		payload = {
			"trajetoria": data["trajectory"],
			"hash_trajetoria_original": data["hash"],
			"vehicle_id": data["vehicle_id"],
			"attempts": args.attempts,
			"top_k": 5,
			"enable_map_matching": args.enable_map_matching,
			"search_radius_m": args.search_radius_m,
			"contract_params": data["contract_params"],
		}
		progress_print("Consultando oraculo para gerar opcoes...")
		start_process = time.perf_counter()
		try:
			resp = requests.post(
				f"{args.oracle_url}/processar_trajeto",
				json=payload,
				timeout=None,
			)
		except requests.exceptions.ReadTimeout as exc:
			raise RuntimeError("Timeout inesperado em /processar_trajeto") from exc
		except requests.exceptions.RequestException as exc:
			raise RuntimeError(f"Erro de comunicacao com o oraculo em /processar_trajeto: {exc}") from exc
		elapsed_process = time.perf_counter() - start_process
		progress_print(f"Oraculo respondeu em {elapsed_process:.3f}s")
		if resp.status_code != 200:
			raise RuntimeError(f"Erro no oraculo: {resp.status_code} - {resp.text}")

		body = resp.json()
		diag = body.get("diagnostico", {})
		if diag:
			progress_print(
				f"Diagnostico oraculo: map_matching_enabled={diag.get('map_matching_enabled')} "
				f"map_matching_available={diag.get('map_matching_available')} "
				f"processing_seconds={diag.get('processing_seconds')}"
			)
		progress_print("\nOpcao sem offset (referencia):")
		progress_print(f"Monetizacao original estimada: {body['original']['e1_reais']:.6f} BRL")
		progress_print("Valores das opcoes abaixo sao estimativas ate a confirmacao on-chain.")
		print_options_table(body["opcoes"])

		selected = input("Escolha a opcao desejada (1-5): ").strip()
		try:
			selected_idx = int(selected)
		except ValueError as exc:
			raise ValueError("Opcao invalida") from exc

		confirm_payload = {
			"request_id": body["request_id"],
			"option_index": selected_idx,
		}
		progress_print("Confirmando opcao com o oraculo...")
		start_confirm = time.perf_counter()
		try:
			conf = requests.post(
				f"{args.oracle_url}/confirmar_opcao",
				json=confirm_payload,
				timeout=None,
			)
		except requests.exceptions.ReadTimeout as exc:
			raise RuntimeError("Timeout inesperado em /confirmar_opcao") from exc
		except requests.exceptions.RequestException as exc:
			raise RuntimeError(f"Erro de comunicacao com o oraculo em /confirmar_opcao: {exc}") from exc
		elapsed_confirm = time.perf_counter() - start_confirm
		progress_print(f"Confirmacao recebida em {elapsed_confirm:.3f}s")
		if conf.status_code != 200:
			raise RuntimeError(f"Erro ao confirmar: {conf.status_code} - {conf.text}")

		conf_body = conf.json()
		progress_print("\nSelecao confirmada e armazenada na blockchain pelo oraculo")
		progress_print(f"Carteira do oraculo: {conf_body['carteira_oraculo']}")
		progress_print(f"Hash original armazenado: {conf_body['hash_original']}")
		progress_print(f"Monetizado: {conf_body['monetizacao_e1_reais']:.6f} BRL")
		progress_print(f"TX: {', '.join(conf_body['tx_hashes'])}")

		token_guess = input("Se quiser auditar agora, informe tokenId (Enter para pular): ").strip()
		if token_guess:
			try:
				token_id = int(token_guess)
				onchain_hash = read_hash_onchain(args.deployment_file, token_id)
				match = verify_hash_onchain(args.deployment_file, token_id, data["hash"])
				progress_print(f"Hash local:    {to_bytes32_hex(data['hash'])}")
				progress_print(f"Hash on-chain: {onchain_hash}")
				progress_print(f"Hash bate? {'SIM' if match else 'NAO'}")
			except ValueError:
				progress_print("tokenId invalido; pulando auditoria manual")
	else:
		progress_print("\nUsuario optou por nao aplicar offset")
		progress_print("Dados confirmados do trajeto original:")
		progress_print(f"VIN: {data['vehicle_id']}")
		progress_print(f"Hash original: {data['hash']}")
		progress_print(f"Distancia aprox: {trajectory_distance_km(data['trajectory']):.4f} km")

		direct = send_direct_without_offset(
			deployment_file=args.deployment_file,
			private_key=args.user_private_key,
			recipient=user_address,
			contract_params=data["contract_params"],
			hash_original=data["hash"],
			vehicle_id=data["vehicle_id"],
		)

		progress_print("\nEnvio direto concluido")
		progress_print(f"Carteira do usuario: {user_address}")
		progress_print(f"Monetizacao estimada sem deslocamento: {direct['estimated_e1_reais']:.6f} BRL")
		progress_print(f"Token mintado: {direct['minted_token_id']}")
		progress_print(f"Hash on-chain: {direct['onchain_hash']}")
		progress_print(f"Hash bate? {'SIM' if direct['hash_match'] else 'NAO'}")
		progress_print(f"TX: {', '.join(direct['tx_hashes'])}")


if __name__ == "__main__":
	main()

