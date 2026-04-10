#!/usr/bin/env python3
"""
Servidor API do oraculo de privacidade por offset.

Endpoints:
- POST /processar_trajeto
- POST /confirmar_opcao
- GET /health
"""

import argparse
import hashlib
import json
import math
import os
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple

import uvicorn
from eth_account import Account
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from blockchain_sender import send_oracle_results

try:
    import osmnx as ox
    from shapely.geometry import Point

    MAP_MATCHING_AVAILABLE = True
except ImportError:
    MAP_MATCHING_AVAILABLE = False


EARTH_RADIUS_KM = 6371.0
DEFAULT_ATTEMPTS = 20
DEFAULT_TOP_K = 5

DEFAULT_ROAD_GASOLINE_KM_L = 12.0
DEFAULT_CITY_GASOLINE_KM_L = 11.5
DEFAULT_CARBON_PRICE_BRL_TON = 50.0

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000


class ContractParamsInput(BaseModel):
    highwayDistance: Optional[int] = None
    cityDistance: Optional[int] = None
    ethanolPercent: Optional[int] = 0
    roadGasoline: Optional[int] = None
    roadEthanol: Optional[int] = 0
    cityGasoline: Optional[int] = None
    cityEthanol: Optional[int] = 0
    realCO2Emissions: Optional[int] = None
    carbonPricePerTon: Optional[int] = None


class ProcessarTrajetoRequest(BaseModel):
    trajetoria: List[List[float]] = Field(..., min_length=2)
    hash_trajetoria_original: str
    vehicle_id: Optional[str] = "veh0"
    attempts: int = DEFAULT_ATTEMPTS
    top_k: int = DEFAULT_TOP_K
    max_radius_km: float = 2.0
    enable_map_matching: bool = False
    search_radius_m: int = 1500
    contract_params: Optional[ContractParamsInput] = None


class ConfirmarOpcaoRequest(BaseModel):
    request_id: str
    option_index: int = Field(..., ge=1)


app = FastAPI(title="Oracle Offset API", version="1.0.0")

# Pendencias em memoria: request_id -> dados da proposta
PENDING_SELECTIONS: Dict[str, Dict[str, Any]] = {}


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
        raise ValueError("hash_trajetoria_original deve ter 64 chars hex")
    int(h, 16)
    return "0x" + h


def generate_random_offset(max_radius_km: float, ref_lat: float) -> Tuple[float, float, float, float]:
    angle = random.uniform(0.0, 2.0 * math.pi)
    distance_km = math.sqrt(random.uniform(0.0, 1.0)) * max_radius_km

    dx_km = distance_km * math.cos(angle)
    dy_km = distance_km * math.sin(angle)

    offset_lat = dx_km / 111.32
    cos_lat = math.cos(math.radians(ref_lat))
    offset_lon = dy_km / (111.32 * cos_lat) if cos_lat != 0 else 0.0

    return offset_lat, offset_lon, distance_km, math.degrees(angle)


def apply_offset(points: List[List[float]], offset_lat: float, offset_lon: float) -> List[List[float]]:
    return [[p[0] + offset_lat, p[1] + offset_lon] for p in points]


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


def maybe_map_match(points: List[List[float]], enabled: bool, search_radius_m: int) -> List[List[float]]:
    if not enabled or not points or not MAP_MATCHING_AVAILABLE:
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


def split_city_highway(total_km: float) -> Tuple[float, float]:
    return total_km * 0.4, total_km * 0.6


def build_contract_params_from_trajectory(
    trajectory: List[List[float]],
    override: Optional[ContractParamsInput],
) -> Dict[str, int]:
    total_km = trajectory_distance_km(trajectory)
    city_km, highway_km = split_city_highway(total_km)

    default_real_co2_g = max(total_km * 120.0, 1.0)

    params = {
        "highwayDistance": int(highway_km * 1e6),
        "cityDistance": int(city_km * 1e6),
        "ethanolPercent": 0,
        "roadGasoline": int(DEFAULT_ROAD_GASOLINE_KM_L * 1e6),
        "roadEthanol": 0,
        "cityGasoline": int(DEFAULT_CITY_GASOLINE_KM_L * 1e6),
        "cityEthanol": 0,
        "realCO2Emissions": int(default_real_co2_g * 1e6),
        "carbonPricePerTon": int(DEFAULT_CARBON_PRICE_BRL_TON * 1e6),
    }

    if override is None:
        return params

    raw = override.model_dump(exclude_none=True)
    params.update({k: int(v) for k, v in raw.items()})
    return params


def derive_private_real_co2(original_real_co2: int, private_km: float, original_km: float) -> int:
    if original_km <= 0:
        return original_real_co2
    ratio = private_km / original_km
    return max(1, int(original_real_co2 * ratio))


def capped_private_value(original_value: int, private_diff_abs_percent: float, private_raw_value: int) -> int:
    base = int(original_value * 0.9)
    bonus_ratio = min(max(private_diff_abs_percent, 0.0), 10.0) / 10.0
    bonus = int(original_value * 0.1 * bonus_ratio)
    cap_rule = min(original_value, base + bonus)
    return max(0, min(private_raw_value, cap_rule))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "pending_requests": len(PENDING_SELECTIONS)}


@app.post("/processar_trajeto")
def processar_trajeto(req: ProcessarTrajetoRequest) -> Dict[str, Any]:
    if req.attempts <= 0:
        raise HTTPException(status_code=400, detail="attempts deve ser > 0")
    if req.top_k <= 0:
        raise HTTPException(status_code=400, detail="top_k deve ser > 0")

    trajectory = [[float(p[0]), float(p[1])] for p in req.trajetoria]
    if len(trajectory) < 2:
        raise HTTPException(status_code=400, detail="trajetoria precisa de ao menos 2 pontos")

    computed_hash = build_trajectory_hash(trajectory)
    provided_hash = req.hash_trajetoria_original.lower().replace("0x", "")
    if computed_hash != provided_hash:
        raise HTTPException(
            status_code=400,
            detail={
                "erro": "hash_trajetoria_original invalido",
                "hash_enviado": req.hash_trajetoria_original,
                "hash_calculado": computed_hash,
            },
        )

    original_km = trajectory_distance_km(trajectory)
    contract_params_original = build_contract_params_from_trajectory(trajectory, req.contract_params)
    original_value = simulate_e1_value(contract_params_original)

    ref_lat = sum(p[0] for p in trajectory) / len(trajectory)
    tries: List[Dict[str, Any]] = []

    for i in range(1, req.attempts + 1):
        offset_lat, offset_lon, offset_dist_km, offset_angle_deg = generate_random_offset(req.max_radius_km, ref_lat)
        offset_points = apply_offset(trajectory, offset_lat, offset_lon)
        private_points = maybe_map_match(offset_points, req.enable_map_matching, req.search_radius_m)

        private_km = trajectory_distance_km(private_points)
        diff_percent = privacy_diff_percent(original_km, private_km)
        abs_diff_percent = abs(diff_percent)

        private_params = dict(contract_params_original)
        private_params["realCO2Emissions"] = derive_private_real_co2(
            contract_params_original["realCO2Emissions"],
            private_km,
            original_km,
        )

        private_raw_value = simulate_e1_value(private_params)
        private_capped_value = capped_private_value(original_value, abs_diff_percent, private_raw_value)

        tries.append(
            {
                "attempt": i,
                "distance": {
                    "original_km": original_km,
                    "private_km": private_km,
                    "diff_percent": diff_percent,
                    "abs_diff_percent": abs_diff_percent,
                },
                "offset": {
                    "offset_lat_deg": offset_lat,
                    "offset_lon_deg": offset_lon,
                    "distance_km": offset_dist_km,
                    "angle_deg": offset_angle_deg,
                },
                "trajectory_private": [normalize_point(p) for p in private_points],
                "contract_params": private_params,
                "monetizacao": {
                    "original_e1_micro": int(original_value),
                    "private_raw_e1_micro": int(private_raw_value),
                    "private_final_e1_micro": int(private_capped_value),
                    "original_e1_reais": round(original_value / 1e6, 6),
                    "private_raw_e1_reais": round(private_raw_value / 1e6, 6),
                    "private_final_e1_reais": round(private_capped_value / 1e6, 6),
                },
            }
        )

    top_k = min(req.top_k, len(tries))
    best_options = sorted(tries, key=lambda x: x["distance"]["abs_diff_percent"])[:top_k]

    request_id = str(uuid.uuid4())
    PENDING_SELECTIONS[request_id] = {
        "request_id": request_id,
        "vehicle_id": req.vehicle_id,
        "original_hash": to_bytes32_hex(req.hash_trajetoria_original),
        "original_trajectory": [normalize_point(p) for p in trajectory],
        "original_contract_params": contract_params_original,
        "original_e1_micro": int(original_value),
        "options": best_options,
    }

    return {
        "request_id": request_id,
        "vehicle_id": req.vehicle_id,
        "original": {
            "hash": req.hash_trajetoria_original,
            "distance_km": original_km,
            "e1_micro": int(original_value),
            "e1_reais": round(original_value / 1e6, 6),
        },
        "opcoes": [
            {
                "option_index": idx,
                "attempt": opt["attempt"],
                "distance": opt["distance"],
                "offset": opt["offset"],
                "monetizacao": opt["monetizacao"],
            }
            for idx, opt in enumerate(best_options, start=1)
        ],
    }


@app.post("/confirmar_opcao")
def confirmar_opcao(req: ConfirmarOpcaoRequest) -> Dict[str, Any]:
    if req.request_id not in PENDING_SELECTIONS:
        raise HTTPException(status_code=404, detail="request_id nao encontrado")

    pending = PENDING_SELECTIONS[req.request_id]
    options = pending["options"]
    if req.option_index < 1 or req.option_index > len(options):
        raise HTTPException(status_code=400, detail="option_index invalido")

    selected = options[req.option_index - 1]

    deployment_file = os.environ.get("ORACLE_DEPLOYMENT_FILE")
    oracle_private_key = os.environ.get("ORACLE_PRIVATE_KEY")
    if not deployment_file or not oracle_private_key:
        raise HTTPException(
            status_code=500,
            detail="Configurar ORACLE_DEPLOYMENT_FILE e ORACLE_PRIVATE_KEY no ambiente",
        )

    oracle_address = Account.from_key(oracle_private_key).address
    final_micro = int(selected["monetizacao"]["private_final_e1_micro"])
    if final_micro <= 0:
        raise HTTPException(status_code=400, detail="Valor final de monetizacao nao pode ser zero")

    payload = [
        {
            "vehicle_id": pending.get("vehicle_id", "veh0"),
            "oracle_value": final_micro,
            "recipient": oracle_address,
            "original_hash": pending["original_hash"],
        }
    ]

    try:
        tx_hashes = send_oracle_results(
            results=payload,
            deployment_file=deployment_file,
            private_key=oracle_private_key,
            method_name="mintWithOracleValue",
            method_args_spec=["$.oracle_value", "$.recipient", "$.original_hash"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar transacao: {exc}") from exc

    PENDING_SELECTIONS.pop(req.request_id, None)

    return {
        "status": "confirmado",
        "request_id": req.request_id,
        "option_index": req.option_index,
        "carteira_oraculo": oracle_address,
        "hash_original": pending["original_hash"],
        "monetizacao_e1_micro": final_micro,
        "monetizacao_e1_reais": round(final_micro / 1e6, 6),
        "tx_hashes": tx_hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor API do Oraculo ( )")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host bind da API")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta da API")
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
