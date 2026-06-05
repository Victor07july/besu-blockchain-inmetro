#!/usr/bin/env python3
"""
Mass benchmark script for blockchain performance.

Scenarios:
- direct: send tx with user key
- pseudonym/direct_pseudonym: direct send with pseudonym key
- oracle: offset flow via oracle API
- redeem: redeem ZK proofs in bulk (requires oracle ZK mints)

Edit REPEAT_PER_CSV to control how many times each CSV is used.
"""

import csv
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from eth_account import Account
from web3 import Web3
from web3.exceptions import TimeExhausted

try:
    from web3.middleware import ExtraDataToPOAMiddleware
except ImportError:
    ExtraDataToPOAMiddleware = None

def resolve_repo_root(script_path: Path) -> Path:
    for parent in script_path.parents:
        if (parent / "contracts").is_dir() and (parent / "README.md").exists():
            return parent
    return script_path.parents[1]


REPO_ROOT = resolve_repo_root(Path(__file__).resolve())
SCRIPTS_DIR = REPO_ROOT / "contracts" / "privacy" / "implementacao_offset_zkp" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from blockchain_sender import load_deployment_info  # type: ignore
from usuario import (  # type: ignore
    generate_zk_proof,
    load_csv_first_vehicle,
    resolve_pseudonym_private_key,
    resolve_zk_dir,
    simulate_e1_value,
    strip_aux_fields,
    to_bytes32_hex,
)

# === CONFIG (edit as needed) ===
REPEAT_PER_CSV = 3
MAX_CSV_FILES: Optional[int] = None
SCENARIOS = ["direct", "pseudonym", "oracle"]
# Available: direct, pseudonym, direct_pseudonym, oracle, redeem

DATA_DIR = REPO_ROOT / "contracts" / "privacy" / "implementacao_offset_zkp" / "data" / "trajetos"
DEPLOYMENT_FILE = Path(
    os.environ.get(
        "BENCH_DEPLOYMENT_FILE",
        str(REPO_ROOT / "contracts" / "privacy" / "implementacao_offset_zkp" / "deployment_info.json"),
    )
)
ORACLE_URL = os.environ.get("BENCH_ORACLE_URL", "http://127.0.0.1:5001")

USER_PRIVATE_KEY = os.environ.get("BENCH_USER_PRIVATE_KEY", "").strip()
PSEUDONYM_PRIVATE_KEY = os.environ.get("BENCH_PSEUDONYM_PRIVATE_KEY", "").strip()
PSEUDONYM_SEED_FILE = os.environ.get("BENCH_PSEUDONYM_SEED_FILE", "").strip()
PSEUDONYM_HD_INDEX = int(os.environ.get("BENCH_PSEUDONYM_HD_INDEX", "0"))

ORACLE_OPTION_INDEX = int(os.environ.get("BENCH_ORACLE_OPTION_INDEX", "1"))
MIN_VALUE_MICRO = int(os.environ.get("BENCH_MIN_VALUE_MICRO", "1"))
DIRECT_MIN_VALUE_MICRO = int(os.environ.get("BENCH_DIRECT_MIN_VALUE_MICRO", "0"))
REDEEM_PRIVATE_KEY = os.environ.get("BENCH_REDEEM_PRIVATE_KEY", "").strip()
REDEEM_LIMIT = int(os.environ.get("BENCH_REDEEM_LIMIT", "0"))

TX_GAS_LIMIT = int(os.environ.get("BENCH_GAS_LIMIT", "900000"))
TX_RECEIPT_TIMEOUT = int(os.environ.get("BENCH_RECEIPT_TIMEOUT", "180"))

RESULTS_DIR = REPO_ROOT / "test" / "results"
RESULTS_CSV = RESULTS_DIR / "benchmark_results.csv"
SUMMARY_CSV = RESULTS_DIR / "benchmark_summary.csv"

FIELDNAMES = [
    "record_type",
    "run_id",
    "scenario",
    "csv_file",
    "csv_index",
    "repeat_index",
    "tx_method",
    "tx_hash",
    "tx_status",
    "tx_seconds",
    "tx_wait_seconds",
    "gas_used",
    "effective_gas_price",
    "tx_fee_wei",
    "block_number",
    "e1_original_micro",
    "e1_after_micro",
    "e1_original_brl",
    "e1_after_brl",
    "oracle_process_seconds",
    "oracle_confirm_seconds",
    "zkp_enabled",
    "zk_proof_seconds",
    "error",
    "total_sent",
    "success_count",
    "fail_count",
    "duration_seconds",
    "throughput_tps",
    "latency_avg",
    "latency_p95",
    "latency_max",
]


def get_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if ExtraDataToPOAMiddleware is not None:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def list_csv_files(data_dir: Path) -> List[Path]:
    files = sorted(data_dir.glob("vehicles_step_sim_*.csv"))

    def parse_index(path: Path) -> int:
        stem = path.stem
        try:
            return int(stem.split("_")[-1])
        except (ValueError, IndexError):
            return 0

    files.sort(key=parse_index)
    if MAX_CSV_FILES is None:
        return files
    return files[: MAX_CSV_FILES]


def next_nonce(w3: Web3, cache: Dict[str, int], address: str) -> int:
    if address not in cache:
        cache[address] = w3.eth.get_transaction_count(address)
    value = cache[address]
    cache[address] += 1
    return value


def wait_for_receipt(w3: Web3, tx_hash: str, timeout: int) -> Tuple[Dict[str, Any], float]:
    start = time.perf_counter()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
    elapsed = time.perf_counter() - start
    return receipt, elapsed


def send_contract_tx(
    w3: Web3,
    contract,
    method_name: str,
    args: List[Any],
    private_key: str,
    chain_id: Optional[int],
    gas_price_gwei: int,
    nonce_cache: Dict[str, int],
) -> Dict[str, Any]:
    account = Account.from_key(private_key)
    from_addr = account.address

    tx_payload = {
        "from": from_addr,
        "nonce": next_nonce(w3, nonce_cache, from_addr),
        "gas": TX_GAS_LIMIT,
        "gasPrice": w3.to_wei(gas_price_gwei, "gwei"),
    }
    if chain_id is not None:
        tx_payload["chainId"] = int(chain_id)

    fn = getattr(contract.functions, method_name)(*args)
    txn = fn.build_transaction(tx_payload)
    signed = w3.eth.account.sign_transaction(txn, private_key)

    start = time.perf_counter()
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TX_RECEIPT_TIMEOUT)
    elapsed = time.perf_counter() - start

    return {
        "tx_hash": tx_hash.hex(),
        "receipt": receipt,
        "tx_seconds": elapsed,
    }


def direct_or_pseudonym_run(
    scenario: str,
    data: Dict[str, Any],
    deployment: Dict[str, Any],
    w3: Web3,
    contract,
    nonce_cache: Dict[str, int],
    private_key: str,
) -> Dict[str, Any]:
    recipient = Account.from_key(private_key).address
    params = strip_aux_fields(data["contract_params"])
    estimated_value = max(0, simulate_e1_value(data["contract_params"]))
    oracle_value = estimated_value
    if oracle_value <= 0 and DIRECT_MIN_VALUE_MICRO > 0:
        oracle_value = DIRECT_MIN_VALUE_MICRO
    original_hash = to_bytes32_hex(data["hash"])

    method_name = "mintWithOracleValue"
    method_args = [oracle_value, recipient, original_hash]
    if not hasattr(contract.functions, method_name):
        method_name = "calculateAndMintWithHash"
        method_args = [params, recipient, original_hash]

    tx_result = send_contract_tx(
        w3=w3,
        contract=contract,
        method_name=method_name,
        args=method_args,
        private_key=private_key,
        chain_id=deployment.get("chain_id"),
        gas_price_gwei=deployment.get("gas_price_gwei", 0),
        nonce_cache=nonce_cache,
    )

    receipt = tx_result["receipt"]
    status = int(receipt.get("status", 0))
    gas_used = int(receipt.get("gasUsed", 0))
    effective_gas_price = int(receipt.get("effectiveGasPrice", receipt.get("gasPrice", 0)))
    tx_fee = gas_used * effective_gas_price

    return {
        "tx_method": method_name,
        "tx_hash": tx_result["tx_hash"],
        "tx_status": status,
        "tx_seconds": round(tx_result["tx_seconds"], 6),
        "tx_wait_seconds": round(tx_result["tx_seconds"], 6),
        "gas_used": gas_used,
        "effective_gas_price": effective_gas_price,
        "tx_fee_wei": tx_fee,
        "block_number": int(receipt.get("blockNumber", 0)),
        "e1_original_micro": estimated_value,
        "e1_after_micro": oracle_value,
        "e1_original_brl": round(estimated_value / 1e6, 6),
        "e1_after_brl": round(oracle_value / 1e6, 6),
        "oracle_process_seconds": None,
        "oracle_confirm_seconds": None,
        "zkp_enabled": None,
        "zk_proof_seconds": None,
        "error": None,
    }


def oracle_offset_run(
    data: Dict[str, Any],
    deployment: Dict[str, Any],
    w3: Web3,
) -> Dict[str, Any]:
    payload = {
        "trajetoria": data["trajectory"],
        "hash_trajetoria_original": data["hash"],
        "vehicle_id": data["vehicle_id"],
        "attempts": 20,
        "top_k": 5,
        "enable_map_matching": False,
        "search_radius_m": 1500,
        "contract_params": strip_aux_fields(data["contract_params"]),
    }

    start_process = time.perf_counter()
    resp = requests.post(f"{ORACLE_URL}/processar_trajeto", json=payload, timeout=None)
    process_seconds = time.perf_counter() - start_process
    if resp.status_code != 200:
        raise RuntimeError(f"oracle /processar_trajeto error: {resp.status_code} - {resp.text}")

    body = resp.json()
    options = body.get("opcoes", [])
    if not options:
        raise RuntimeError("oracle returned no options")

    selected = max(
        options,
        key=lambda opt: int(opt["monetizacao"]["private_final_e1_micro"]),
    )
    final_micro = int(selected["monetizacao"]["private_final_e1_micro"])
    if final_micro <= 0:
        e1_original_micro = int(body["original"].get("e1_micro", 0))
        return {
            "tx_method": "oracle_cancelled",
            "tx_hash": None,
            "tx_status": 0,
            "tx_seconds": round(process_seconds, 6),
            "tx_wait_seconds": None,
            "gas_used": None,
            "effective_gas_price": None,
            "tx_fee_wei": None,
            "block_number": None,
            "e1_original_micro": e1_original_micro,
            "e1_after_micro": 0,
            "e1_original_brl": round(e1_original_micro / 1e6, 6),
            "e1_after_brl": 0.0,
            "oracle_process_seconds": round(process_seconds, 6),
            "oracle_confirm_seconds": None,
            "zkp_enabled": None,
            "zk_proof_seconds": None,
            "error": "oracle_offsets_zero",
            "_redeem_item": None,
        }

    option_index = int(selected.get("option_index", 1))
    confirm_payload = {
        "request_id": body["request_id"],
        "option_index": option_index,
    }
    if final_micro <= 0 and MIN_VALUE_MICRO > 0:
        confirm_payload["min_value_micro"] = MIN_VALUE_MICRO

    start_confirm = time.perf_counter()
    conf = requests.post(f"{ORACLE_URL}/confirmar_opcao", json=confirm_payload, timeout=None)
    confirm_seconds = time.perf_counter() - start_confirm
    if conf.status_code != 200:
        raise RuntimeError(f"oracle /confirmar_opcao error: {conf.status_code} - {conf.text}")

    conf_body = conf.json()
    tx_hash = conf_body["tx_hashes"][0]
    receipt, receipt_wait = wait_for_receipt(w3, tx_hash, TX_RECEIPT_TIMEOUT)

    status = int(receipt.get("status", 0))
    gas_used = int(receipt.get("gasUsed", 0))
    effective_gas_price = int(receipt.get("effectiveGasPrice", receipt.get("gasPrice", 0)))
    tx_fee = gas_used * effective_gas_price

    e1_original_micro = int(body["original"].get("e1_micro", 0))
    e1_after_micro = int(conf_body.get("monetizacao_e1_micro", 0))

    tx_wait_seconds = conf_body.get("tx_wait_seconds")
    if tx_wait_seconds is None:
        tx_wait_seconds = receipt_wait

    redeem_item = None
    poseidon_root = conf_body.get("poseidon_root")
    if poseidon_root and status == 1:
        redeem_item = {
            "poseidon_root": poseidon_root,
            "trajectory": data["trajectory"],
            "vehicle_id": data["vehicle_id"],
        }

    return {
        "tx_method": conf_body.get("poseidon_root") and "mintWithOracleValueZK" or "mintWithOracleValue",
        "tx_hash": tx_hash,
        "tx_status": status,
        "tx_seconds": round(confirm_seconds, 6),
        "tx_wait_seconds": round(float(tx_wait_seconds), 6),
        "gas_used": gas_used,
        "effective_gas_price": effective_gas_price,
        "tx_fee_wei": tx_fee,
        "block_number": int(receipt.get("blockNumber", 0)),
        "e1_original_micro": e1_original_micro,
        "e1_after_micro": e1_after_micro,
        "e1_original_brl": round(e1_original_micro / 1e6, 6),
        "e1_after_brl": round(e1_after_micro / 1e6, 6),
        "oracle_process_seconds": round(process_seconds, 6),
        "oracle_confirm_seconds": round(confirm_seconds, 6),
        "zkp_enabled": conf_body.get("zkp_enabled"),
        "zk_proof_seconds": conf_body.get("zk_proof_seconds"),
        "error": None,
        "_redeem_item": redeem_item,
    }


def redeem_zk_run(
    item: Dict[str, Any],
    deployment: Dict[str, Any],
    w3: Web3,
    contract,
    nonce_cache: Dict[str, int],
    private_key: str,
) -> Dict[str, Any]:
    def parse_uint(value: Any) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)
        raise ValueError(f"Valor numerico invalido: {value}")

    if not hasattr(contract.functions, "redeemWithZK"):
        raise RuntimeError("Contrato nao suporta redeemWithZK")

    poseidon_root = item["poseidon_root"]
    trajectory = item["trajectory"]

    if hasattr(contract.functions, "isPoseidonRootRegistered"):
        if not contract.functions.isPoseidonRootRegistered(poseidon_root).call():
            raise RuntimeError("poseidonRoot nao registrado")
    if hasattr(contract.functions, "redeemedPoseidonRoots"):
        if contract.functions.redeemedPoseidonRoots(poseidon_root).call():
            raise RuntimeError("poseidonRoot ja resgatado")

    token_id = None
    amount = None
    if hasattr(contract.functions, "poseidonRootToTokenId"):
        token_id = int(contract.functions.poseidonRootToTokenId(poseidon_root).call())
        if token_id > 0:
            try:
                calc = contract.functions.getCalculationDetails(token_id).call()
                amount = int(calc[5])
            except Exception:
                amount = None

    recipient = Account.from_key(private_key).address
    zk_nonce = int(time.time_ns())
    zk_dir = resolve_zk_dir(None)
    proof_start = time.perf_counter()
    zk_result = generate_zk_proof(
        trajectory=trajectory,
        recipient=recipient,
        nonce=zk_nonce,
        zk_dir=zk_dir,
    )
    zk_proof_seconds = time.perf_counter() - proof_start

    proof = zk_result["proof"]
    proof_a = [parse_uint(x) for x in proof["a"]]
    proof_b = [
        [parse_uint(x) for x in proof["b"][0]],
        [parse_uint(x) for x in proof["b"][1]],
    ]
    proof_c = [parse_uint(x) for x in proof["c"]]

    tx_result = send_contract_tx(
        w3=w3,
        contract=contract,
        method_name="redeemWithZK",
        args=[poseidon_root, zk_nonce, proof_a, proof_b, proof_c],
        private_key=private_key,
        chain_id=deployment.get("chain_id"),
        gas_price_gwei=deployment.get("gas_price_gwei", 0),
        nonce_cache=nonce_cache,
    )

    receipt = tx_result["receipt"]
    status = int(receipt.get("status", 0))
    gas_used = int(receipt.get("gasUsed", 0))
    effective_gas_price = int(receipt.get("effectiveGasPrice", receipt.get("gasPrice", 0)))
    tx_fee = gas_used * effective_gas_price

    if amount is None:
        amount = 0

    return {
        "tx_method": "redeemWithZK",
        "tx_hash": tx_result["tx_hash"],
        "tx_status": status,
        "tx_seconds": round(tx_result["tx_seconds"], 6),
        "tx_wait_seconds": round(tx_result["tx_seconds"], 6),
        "gas_used": gas_used,
        "effective_gas_price": effective_gas_price,
        "tx_fee_wei": tx_fee,
        "block_number": int(receipt.get("blockNumber", 0)),
        "e1_original_micro": int(amount),
        "e1_after_micro": int(amount),
        "e1_original_brl": round(int(amount) / 1e6, 6),
        "e1_after_brl": round(int(amount) / 1e6, 6),
        "oracle_process_seconds": None,
        "oracle_confirm_seconds": None,
        "zkp_enabled": True,
        "zk_proof_seconds": round(zk_proof_seconds, 6),
        "error": None,
    }


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    k = int(round((pct / 100.0) * (len(values) - 1)))
    return float(values[k])


def ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def write_row(path: Path, row: Dict[str, Any]) -> None:
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def build_summary_row(
    run_id: str,
    scenario: str,
    scenario_start: float,
    total_sent: int,
    success_count: int,
    fail_count: int,
    latency_values: List[float],
    interrupted: bool = False,
) -> Dict[str, Any]:
    """Build a summary row from accumulated scenario stats."""
    duration = time.perf_counter() - scenario_start
    latency_avg = sum(latency_values) / len(latency_values) if latency_values else 0.0
    latency_p95 = percentile(latency_values, 95.0) if latency_values else 0.0
    latency_max = max(latency_values) if latency_values else 0.0
    throughput = (success_count / duration) if duration > 0 else 0.0

    return {
        "record_type": "summary",
        "run_id": run_id,
        "scenario": scenario + ("_interrupted" if interrupted else ""),
        "csv_file": None,
        "csv_index": None,
        "repeat_index": None,
        "tx_method": None,
        "tx_hash": None,
        "tx_status": None,
        "tx_seconds": None,
        "tx_wait_seconds": None,
        "gas_used": None,
        "effective_gas_price": None,
        "tx_fee_wei": None,
        "block_number": None,
        "e1_original_micro": None,
        "e1_after_micro": None,
        "e1_original_brl": None,
        "e1_after_brl": None,
        "oracle_process_seconds": None,
        "oracle_confirm_seconds": None,
        "zkp_enabled": None,
        "zk_proof_seconds": None,
        "error": "interrupted" if interrupted else None,
        "total_sent": total_sent,
        "success_count": success_count,
        "fail_count": fail_count,
        "duration_seconds": round(duration, 6),
        "throughput_tps": round(throughput, 6),
        "latency_avg": round(latency_avg, 6),
        "latency_p95": round(latency_p95, 6),
        "latency_max": round(latency_max, 6),
    }


def run_scenario(
    scenario: str,
    csv_files: List[Path],
    deployment: Dict[str, Any],
    w3: Web3,
    contract,
    run_id: str,
    redeem_queue: List[Dict[str, Any]],
) -> None:
    scenario_start = time.perf_counter()
    latency_values: List[float] = []
    total_sent = 0
    success_count = 0
    fail_count = 0
    nonce_cache: Dict[str, int] = {}

    if scenario in ("direct", "pseudonym", "direct_pseudonym"):
        if scenario == "direct" and not USER_PRIVATE_KEY:
            raise ValueError("BENCH_USER_PRIVATE_KEY is required for direct scenario")
        if scenario in ("pseudonym", "direct_pseudonym"):
            if not PSEUDONYM_PRIVATE_KEY and not PSEUDONYM_SEED_FILE:
                raise ValueError("Provide BENCH_PSEUDONYM_PRIVATE_KEY or BENCH_PSEUDONYM_SEED_FILE")

    if scenario == "redeem":
        redeem_key = REDEEM_PRIVATE_KEY or USER_PRIVATE_KEY
        if not redeem_key:
            raise ValueError("BENCH_REDEEM_PRIVATE_KEY or BENCH_USER_PRIVATE_KEY is required for redeem")

        items = list(redeem_queue)
        if REDEEM_LIMIT > 0:
            items = items[:REDEEM_LIMIT]

        if not items:
            summary_row = build_summary_row(
                run_id, scenario, scenario_start,
                total_sent=0, success_count=0, fail_count=0,
                latency_values=[],
            )
            summary_row["error"] = "no_redeem_items"
            write_row(RESULTS_CSV, summary_row)
            write_row(SUMMARY_CSV, summary_row)
            return

        try:
            for idx, item in enumerate(items, start=1):
                total_sent += 1
                row: Dict[str, Any] = {
                    "record_type": "tx",
                    "run_id": run_id,
                    "scenario": scenario,
                    "csv_file": item.get("csv_file"),
                    "csv_index": item.get("csv_index"),
                    "repeat_index": item.get("repeat_index", idx),
                }
                try:
                    result = redeem_zk_run(item, deployment, w3, contract, nonce_cache, redeem_key)
                    row.update(result)
                    status = int(result.get("tx_status", 0))
                    if status == 1:
                        success_count += 1
                        latency_values.append(float(result.get("tx_wait_seconds") or 0.0))
                    else:
                        fail_count += 1
                except Exception as exc:
                    fail_count += 1
                    row.update({
                        "tx_method": None, "tx_hash": None, "tx_status": 0,
                        "tx_seconds": None, "tx_wait_seconds": None,
                        "gas_used": None, "effective_gas_price": None, "tx_fee_wei": None,
                        "block_number": None, "e1_original_micro": None, "e1_after_micro": None,
                        "e1_original_brl": None, "e1_after_brl": None,
                        "oracle_process_seconds": None, "oracle_confirm_seconds": None,
                        "zkp_enabled": None, "zk_proof_seconds": None, "error": str(exc),
                    })
                write_row(RESULTS_CSV, row)

        except KeyboardInterrupt:
            print(f"\n[!] Interrupted during scenario '{scenario}'. Saving partial summary...")
            summary_row = build_summary_row(
                run_id, scenario, scenario_start,
                total_sent, success_count, fail_count,
                latency_values, interrupted=True,
            )
            write_row(RESULTS_CSV, summary_row)
            write_row(SUMMARY_CSV, summary_row)
            raise

        summary_row = build_summary_row(
            run_id, scenario, scenario_start,
            total_sent, success_count, fail_count, latency_values,
        )
        write_row(RESULTS_CSV, summary_row)
        write_row(SUMMARY_CSV, summary_row)
        return

    # --- scenarios: direct, pseudonym, direct_pseudonym, oracle ---
    try:
        for csv_path in csv_files:
            data = load_csv_first_vehicle(str(csv_path))
            csv_index = int(csv_path.stem.split("_")[-1]) if "_" in csv_path.stem else 0

            for rep in range(1, REPEAT_PER_CSV + 1):
                total_sent += 1
                row: Dict[str, Any] = {
                    "record_type": "tx",
                    "run_id": run_id,
                    "scenario": scenario,
                    "csv_file": csv_path.name,
                    "csv_index": csv_index,
                    "repeat_index": rep,
                }
                try:
                    if scenario == "oracle":
                        result = oracle_offset_run(data, deployment, w3)
                        redeem_item = result.pop("_redeem_item", None)
                        if redeem_item:
                            redeem_item["csv_file"] = csv_path.name
                            redeem_item["csv_index"] = csv_index
                            redeem_item["repeat_index"] = rep
                            redeem_queue.append(redeem_item)
                    elif scenario == "direct":
                        result = direct_or_pseudonym_run(
                            scenario, data, deployment, w3, contract, nonce_cache, USER_PRIVATE_KEY,
                        )
                    elif scenario in ("pseudonym", "direct_pseudonym"):
                        key = PSEUDONYM_PRIVATE_KEY
                        if not key:
                            _, key = resolve_pseudonym_private_key(
                                seed_file=PSEUDONYM_SEED_FILE,
                                hd_index=PSEUDONYM_HD_INDEX,
                            )
                        result = direct_or_pseudonym_run(
                            scenario, data, deployment, w3, contract, nonce_cache, key,
                        )
                    else:
                        raise ValueError(f"Unknown scenario: {scenario}")

                    row.update(result)
                    status = int(result.get("tx_status", 0))
                    if status == 1:
                        success_count += 1
                        latency_values.append(float(result.get("tx_wait_seconds") or 0.0))
                    else:
                        if result.get("error") != "oracle_offsets_zero":
                            fail_count += 1
                except Exception as exc:
                    fail_count += 1
                    row.update({
                        "tx_method": None, "tx_hash": None, "tx_status": 0,
                        "tx_seconds": None, "tx_wait_seconds": None,
                        "gas_used": None, "effective_gas_price": None, "tx_fee_wei": None,
                        "block_number": None, "e1_original_micro": None, "e1_after_micro": None,
                        "e1_original_brl": None, "e1_after_brl": None,
                        "oracle_process_seconds": None, "oracle_confirm_seconds": None,
                        "zkp_enabled": None, "zk_proof_seconds": None, "error": str(exc),
                    })

                write_row(RESULTS_CSV, row)

    except KeyboardInterrupt:
        print(f"\n[!] Interrupted during scenario '{scenario}'. Saving partial summary...")
        summary_row = build_summary_row(
            run_id, scenario, scenario_start,
            total_sent, success_count, fail_count,
            latency_values, interrupted=True,
        )
        write_row(RESULTS_CSV, summary_row)
        write_row(SUMMARY_CSV, summary_row)
        raise

    summary_row = build_summary_row(
        run_id, scenario, scenario_start,
        total_sent, success_count, fail_count, latency_values,
    )
    write_row(RESULTS_CSV, summary_row)
    write_row(SUMMARY_CSV, summary_row)


def main() -> None:
    if not DEPLOYMENT_FILE.exists():
        raise FileNotFoundError(f"deployment file not found: {DEPLOYMENT_FILE}")

    csv_files = list_csv_files(DATA_DIR)
    if not csv_files:
        raise FileNotFoundError(f"no CSV files found in {DATA_DIR}")

    deployment = load_deployment_info(str(DEPLOYMENT_FILE))
    rpc_url = deployment.get("rpc_url", "http://localhost:8545")
    w3 = get_web3(rpc_url)
    _ = w3.eth.chain_id
    _ = w3.eth.block_number

    contract = w3.eth.contract(address=deployment["contract_address"], abi=deployment["abi"])

    ensure_results_dir()
    run_id = uuid.uuid4().hex
    redeem_queue: List[Dict[str, Any]] = []

    try:
        for scenario in SCENARIOS:
            run_scenario(
                scenario=scenario,
                csv_files=csv_files,
                deployment=deployment,
                w3=w3,
                contract=contract,
                run_id=run_id,
                redeem_queue=redeem_queue,
            )
    except KeyboardInterrupt:
        print(f"\n[!] Benchmark cancelled. Partial results saved to: {RESULTS_CSV}")
        print(f"[!] Partial summary saved to: {SUMMARY_CSV}")
        sys.exit(1)

    print(f"Done. Results: {RESULTS_CSV} | Summary: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()