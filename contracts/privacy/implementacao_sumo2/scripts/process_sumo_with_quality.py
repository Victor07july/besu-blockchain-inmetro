#!/usr/bin/env python3
"""
Script para processar dados SUMO com:
- Privacidade Diferencial
- Map Matching
- Cálculo de Qualidade (redundância + esparsidade)
- Penalização automática de créditos

Entrada: CSV SUMO (vehicle_id, start_lat, start_lon, end_lat, end_lon, CO2...)
Saída: CSV com CO2, qualidade e créditos ajustados

Autor: Victor
Data: 2026-03-03
"""

import pandas as pd
import numpy as np
import sys
import warnings
import math
from typing import List, Tuple, Dict

# Map matching
try:
    import osmnx as ox
    import networkx as nx
    MAP_MATCHING_AVAILABLE = True
except ImportError:
    MAP_MATCHING_AVAILABLE = False
    print("⚠️  osmnx não instalado. Map matching desabilitado.")

warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÕES ====================
# Privacidade Diferencial
EPSILON = 0.5
SENSITIVITY = 0.0002  # graus (≈22m)

# Map Matching
ENABLE_MAP_MATCHING = True
SEARCH_RADIUS = 1500
MAX_SNAP_DISTANCE = 100
FORCE_SNAP = True
GRAPH_CACHE = {}

# Qualidade
MOVEMENT_THRESHOLD = 5  # metros para considerar "parado"
# =======================================================


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em metros entre dois pontos GPS"""
    R = 6371000  # Raio da Terra em metros
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def add_laplace_noise(value: float) -> float:
    """Adiciona ruído Laplace para privacidade diferencial"""
    scale = SENSITIVITY / EPSILON
    noise = np.random.laplace(loc=0, scale=scale)
    return value + noise


def get_road_network(lat: float, lon: float) -> nx.MultiDiGraph:
    """Baixa malha viária ao redor das coordenadas"""
    if not MAP_MATCHING_AVAILABLE:
        return None
    
    cache_key = (round(lat, 2), round(lon, 2))
    if cache_key in GRAPH_CACHE:
        return GRAPH_CACHE[cache_key]
    
    for radius in [SEARCH_RADIUS, SEARCH_RADIUS * 2, SEARCH_RADIUS * 3]:
        try:
            G = ox.graph_from_point(
                (lat, lon),
                dist=radius,
                network_type='drive',
                simplify=False
            )
            GRAPH_CACHE[cache_key] = G
            return G
        except:
            continue
    
    return None


def snap_to_nearest_road(G: nx.MultiDiGraph, lat: float, lon: float, 
                        lat_orig: float, lon_orig: float) -> Tuple[float, float, bool]:
    """Projeta coordenada para via mais próxima"""
    if G is None:
        return lat, lon, False
    
    try:
        nearest_edge = ox.distance.nearest_edges(G, lon, lat)
        u, v, key = nearest_edge
        
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        lat_snap = (u_data['y'] + v_data['y']) / 2
        lon_snap = (u_data['x'] + v_data['x']) / 2
        
        dist_to_original = haversine_distance(lat_snap, lon_snap, lat_orig, lon_orig)
        
        if dist_to_original <= MAX_SNAP_DISTANCE or FORCE_SNAP:
            return lat_snap, lon_snap, True
        else:
            return lat, lon, False
            
    except:
        return lat, lon, False


def calculate_quality_score(trajectory_points: List[Dict]) -> Dict:
    """
    Calcula score de qualidade baseado em redundância e esparsidade
    
    Args:
        trajectory_points: Lista de {'lat', 'lon', 'timestamp'}
    
    Returns:
        Dict com score, multiplier, detalhes
    """
    if len(trajectory_points) < 2:
        return {
            'score': 0,
            'multiplier': 0.2,
            'redundancy_ratio': 0,
            'avg_interval': 0
        }
    
    # 1. REDUNDÂNCIA ESPACIAL
    stationary_count = 0
    total_movements = len(trajectory_points) - 1
    
    for i in range(1, len(trajectory_points)):
        dist = haversine_distance(
            trajectory_points[i-1]['lat'],
            trajectory_points[i-1]['lon'],
            trajectory_points[i]['lat'],
            trajectory_points[i]['lon']
        )
        if dist < MOVEMENT_THRESHOLD:
            stationary_count += 1
    
    redundancy_ratio = stationary_count / total_movements
    
    # Penalidade redundância
    if redundancy_ratio > 0.8:
        redundancy_penalty = -60
    elif redundancy_ratio > 0.6:
        redundancy_penalty = -40
    elif redundancy_ratio > 0.4:
        redundancy_penalty = -20
    elif redundancy_ratio > 0.2:
        redundancy_penalty = -10
    else:
        redundancy_penalty = 0
    
    # 2. ESPARSIDADE TEMPORAL
    intervals = [trajectory_points[i]['timestamp'] - trajectory_points[i-1]['timestamp'] 
                 for i in range(1, len(trajectory_points))]
    
    avg_interval = sum(intervals) / len(intervals)
    max_gap = max(intervals)
    
    # Penalidade esparsidade (intervalo médio)
    if avg_interval > 300:
        sparsity_penalty = -50
    elif avg_interval > 120:
        sparsity_penalty = -30
    elif avg_interval > 60:
        sparsity_penalty = -15
    elif avg_interval > 30:
        sparsity_penalty = -5
    else:
        sparsity_penalty = 0
    
    # Penalidade por gap crítico
    if max_gap > 600:
        gap_penalty = -20
    elif max_gap > 300:
        gap_penalty = -10
    else:
        gap_penalty = 0
    
    # 3. SCORE FINAL
    score = 100 + redundancy_penalty + sparsity_penalty + gap_penalty
    score = max(0, min(100, score))
    
    # 4. MULTIPLICADOR (0.2 a 1.0)
    multiplier = 0.2 + (score / 100) * 0.8
    
    return {
        'score': score,
        'multiplier': multiplier,
        'redundancy_ratio': redundancy_ratio,
        'stationary_count': stationary_count,
        'moving_count': total_movements - stationary_count,
        'avg_interval': avg_interval,
        'max_gap': max_gap
    }


def process_vehicle_trajectory(df_vehicle: pd.DataFrame, vehicle_id: str) -> Dict:
    """
    Processa trajeto de um veículo com qualidade, DP e map matching
    
    Args:
        df_vehicle: DataFrame com trajeto do veículo
        vehicle_id: ID do veículo
        
    Returns:
        Dict com resultados
    """
    # Usar end_lat/end_lon (posição atual em cada segmento)
    trajectory_points = []
    trajectory_with_privacy = []
    
    co2_total = df_vehicle['CO2'].sum()
    distance_total = df_vehicle['distance'].sum()
    
    # Timestamps (assumindo 1 segundo por linha se não houver coluna)
    if 'timestamp' in df_vehicle.columns:
        timestamps = df_vehicle['timestamp'].values
    else:
        timestamps = np.arange(len(df_vehicle), dtype=float)
    
    # Processar cada ponto
    for idx, row in df_vehicle.iterrows():
        lat_orig = row['end_lat']
        lon_orig = row['end_lon']
        timestamp = timestamps[idx] if idx < len(timestamps) else idx
        
        # Adicionar ponto original (sem privacidade)
        trajectory_points.append({
            'lat': lat_orig,
            'lon': lon_orig,
            'timestamp': timestamp
        })
        
        # Aplicar privacidade diferencial
        lat_noisy = add_laplace_noise(lat_orig)
        lon_noisy = add_laplace_noise(lon_orig)
        
        # Map matching
        if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE:
            G = get_road_network(lat_orig, lon_orig)
            lat_private, lon_private, snapped = snap_to_nearest_road(
                G, lat_noisy, lon_noisy, lat_orig, lon_orig
            )
        else:
            lat_private, lon_private = lat_noisy, lon_noisy
        
        trajectory_with_privacy.append({
            'lat': lat_private,
            'lon': lon_private,
            'timestamp': timestamp
        })
    
    # Calcular score de qualidade
    quality_result = calculate_quality_score(trajectory_points)
    
    # Aplicar multiplicador de qualidade nos créditos
    co2_credits = co2_total * quality_result['multiplier']
    
    # Coordenadas início/fim
    start_lat = df_vehicle.iloc[0]['end_lat']
    start_lon = df_vehicle.iloc[0]['end_lon']
    end_lat = df_vehicle.iloc[-1]['end_lat']
    end_lon = df_vehicle.iloc[-1]['end_lon']
    
    # Coordenadas privadas início/fim
    start_lat_priv = trajectory_with_privacy[0]['lat']
    start_lon_priv = trajectory_with_privacy[0]['lon']
    end_lat_priv = trajectory_with_privacy[-1]['lat']
    end_lon_priv = trajectory_with_privacy[-1]['lon']
    
    result = {
        'vehicle_id': vehicle_id,
        'num_points': len(df_vehicle),
        'duration_seconds': timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0,
        'total_distance_km': distance_total,
        'co2_raw_kg': co2_total,
        'quality_score': quality_result['score'],
        'quality_multiplier': quality_result['multiplier'],
        'co2_credits_kg': co2_credits,
        'credit_reduction_percent': (1 - quality_result['multiplier']) * 100,
        'redundancy_ratio': quality_result['redundancy_ratio'],
        'stationary_count': quality_result['stationary_count'],
        'moving_count': quality_result['moving_count'],
        'avg_interval_seconds': quality_result['avg_interval'],
        'max_gap_seconds': quality_result['max_gap'],
        'start_lat_orig': start_lat,
        'start_lon_orig': start_lon,
        'end_lat_orig': end_lat,
        'end_lon_orig': end_lon,
        'start_lat_private': start_lat_priv,
        'start_lon_private': start_lon_priv,
        'end_lat_private': end_lat_priv,
        'end_lon_private': end_lon_priv,
    }
    
    return result


def process_sumo_csv(input_csv: str, output_csv: str):
    """
    Processa CSV SUMO com qualidade, DP e map matching
    
    Args:
        input_csv: Arquivo SUMO de entrada
        output_csv: Arquivo de saída com resultados
    """
    print("="*70)
    print("🎯 PROCESSAMENTO SUMO COM QUALIDADE + PRIVACIDADE")
    print("="*70)
    print(f"📂 Entrada: {input_csv}")
    print(f"💾 Saída: {output_csv}")
    print(f"🔐 Epsilon (ε): {EPSILON}")
    print(f"📏 Sensitivity: {SENSITIVITY}° (≈{SENSITIVITY/EPSILON*111320:.0f}m)")
    print(f"🗺️  Map matching: {'ATIVADO' if ENABLE_MAP_MATCHING else 'DESATIVADO'}")
    print("="*70)
    
    # Ler CSV
    print("\n📊 Carregando dados...")
    df = pd.read_csv(input_csv)
    print(f"   Registros: {len(df):,}")
    
    # Processar por veículo
    vehicles = df['vehicle_id'].unique()
    print(f"   Veículos: {len(vehicles)}")
    
    results = []
    
    for idx, vehicle_id in enumerate(vehicles, 1):
        print(f"\n[{idx}/{len(vehicles)}] Processando veículo {vehicle_id}...")
        df_vehicle = df[df['vehicle_id'] == vehicle_id]
        
        result = process_vehicle_trajectory(df_vehicle, vehicle_id)
        results.append(result)
        
        print(f"   📏 Distância: {result['total_distance_km']:.2f} km")
        print(f"   🏭 CO2 bruto: {result['co2_raw_kg']:.3f} kg")
        print(f"   📊 Qualidade: {result['quality_score']:.1f}/100")
        print(f"   💰 Créditos: {result['co2_credits_kg']:.3f} kg ({result['quality_multiplier']:.3f}x)")
        print(f"   ⚠️  Redução: {result['credit_reduction_percent']:.1f}%")
    
    # Salvar resultados
    df_result = pd.DataFrame(results)
    df_result.to_csv(output_csv, index=False)
    
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*70)
    print(f"Veículos processados: {len(df_result)}")
    print(f"CO2 bruto total: {df_result['co2_raw_kg'].sum():.2f} kg")
    print(f"CO2 créditos total: {df_result['co2_credits_kg'].sum():.2f} kg")
    print(f"Perda por qualidade: {df_result['co2_raw_kg'].sum() - df_result['co2_credits_kg'].sum():.2f} kg")
    print(f"Score médio: {df_result['quality_score'].mean():.1f}/100")
    print(f"Multiplicador médio: {df_result['quality_multiplier'].mean():.3f}")
    print(f"\n💾 Resultados salvos em: {output_csv}")
    print("="*70)


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 process_sumo_with_quality.py <input.csv> [output.csv]")
        print("\nParâmetros:")
        print("  input.csv  : CSV SUMO com trajetos (obrigatório)")
        print("  output.csv : Arquivo de saída (padrão: results_with_quality.csv)")
        print("\nExemplo:")
        print("  python3 process_sumo_with_quality.py carro_1000.csv results.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'results_with_quality.csv'
    
    process_sumo_csv(input_file, output_file)


if __name__ == "__main__":
    main()
