#!/usr/bin/env python3
"""
Script simplificado para processar OBDLink.csv e enviar ao E1RegistryTelemetry
Pipeline direto: OBD → DP → Elevação → Blockchain

Entrada: OBDLink.csv (dados brutos de telemetria)
Saída: Transações no contrato E1RegistryTelemetry

Autor: Victor
Data: 2026-02-23
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import sys
import os

# Importar módulo de DP e elevação
try:
    from differential_privacy_gps import DifferentialPrivacyGPS
    DP_AVAILABLE = True
except ImportError:
    print("⚠️  differential_privacy_gps.py não encontrado. DP desabilitado.")
    DP_AVAILABLE = False


def identify_trips(df: pd.DataFrame, max_gap_seconds: float = 300, 
                   min_trip_duration: float = 60) -> List[Tuple[int, int]]:
    """
    Identifica viagens baseado em gaps de tempo
    
    Args:
        df: DataFrame com coluna 'Time (sec)'
        max_gap_seconds: Gap máximo entre pontos da mesma viagem
        min_trip_duration: Duração mínima de uma viagem
        
    Returns:
        Lista de tuplas (início, fim) de cada viagem
    """
    trips = []
    trip_start = 0
    
    for i in range(1, len(df)):
        time_gap = df.iloc[i]['Time (sec)'] - df.iloc[i-1]['Time (sec)']
        
        if time_gap > max_gap_seconds:
            trip_duration = df.iloc[i-1]['Time (sec)'] - df.iloc[trip_start]['Time (sec)']
            
            if trip_duration >= min_trip_duration:
                trips.append((trip_start, i-1))
            
            trip_start = i
    
    # Última viagem
    trip_duration = df.iloc[-1]['Time (sec)'] - df.iloc[trip_start]['Time (sec)']
    if trip_duration >= min_trip_duration:
        trips.append((trip_start, len(df)-1))
    
    return trips


def calculate_distance_haversine(lat1: float, lon1: float, 
                                 lat2: float, lon2: float) -> float:
    """
    Calcula distância entre dois pontos GPS usando fórmula de Haversine
    
    Args:
        lat1, lon1: Latitude e longitude do ponto 1
        lat2, lon2: Latitude e longitude do ponto 2
        
    Returns:
        Distância em km
    """
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Raio da Terra em km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return distance


def process_trip_telemetry(df_trip: pd.DataFrame, trip_id: int,
                           start_timestamp: datetime, vin: str,
                           epsilon: float = 0.5) -> Dict:
    """
    Processa uma viagem:
    1. Calcula distância REAL somando todos os segmentos ponto-a-ponto (Haversine)
    2. Aplica DP APENAS nas coordenadas de início e fim
    3. Preserva distância real calculada (sem DP)
    
    Args:
        df_trip: DataFrame com dados da viagem
        trip_id: ID da viagem
        start_timestamp: Timestamp de início da coleta
        vin: VIN do veículo
        epsilon: Parâmetro de privacidade diferencial
        
    Returns:
        Dicionário com dados processados
    """
    # Coordenadas originais (início e fim)
    start_lat_orig = df_trip.iloc[0][' Latitude (deg)']
    start_lon_orig = df_trip.iloc[0][' Longitude (deg)']
    end_lat_orig = df_trip.iloc[-1][' Latitude (deg)']
    end_lon_orig = df_trip.iloc[-1][' Longitude (deg)']
    
    # 🔢 CALCULAR DISTÂNCIA REAL somando TODOS os segmentos ponto-a-ponto
    total_distance_km = 0.0
    for i in range(len(df_trip) - 1):
        lat1 = df_trip.iloc[i][' Latitude (deg)']
        lon1 = df_trip.iloc[i][' Longitude (deg)']
        lat2 = df_trip.iloc[i+1][' Latitude (deg)']
        lon2 = df_trip.iloc[i+1][' Longitude (deg)']
        
        # Somar distância do segmento
        segment_distance = calculate_distance_haversine(lat1, lon1, lat2, lon2)
        total_distance_km += segment_distance
    
    # 🔒 Aplicar DP APENAS nas coordenadas de início e fim
    if DP_AVAILABLE:
        dp_processor = DifferentialPrivacyGPS(epsilon=epsilon)
        
        # Processar início
        start_result = dp_processor.process_coordinates(start_lat_orig, start_lon_orig)
        start_lat_private = start_result['lat_private']
        start_lon_private = start_result['lon_private']
        start_elevation = start_result['elevation_private']
        
        # Processar fim
        end_result = dp_processor.process_coordinates(end_lat_orig, end_lon_orig)
        end_lat_private = end_result['lat_private']
        end_lon_private = end_result['lon_private']
        end_elevation = end_result['elevation_private']
        
    else:
        # Sem DP - usar coordenadas originais
        start_lat_private = start_lat_orig
        start_lon_private = start_lon_orig
        end_lat_private = end_lat_orig
        end_lon_private = end_lon_orig
        start_elevation = 0
        end_elevation = 0
    
    # Timestamp da viagem
    trip_start_time = start_timestamp + timedelta(seconds=float(df_trip.iloc[0]['Time (sec)']))
    
    # Velocidade média (calculada dos dados reais)
    avg_speed = df_trip[' Vehicle speed (km/h)'].mean()
    
    # Percentual de etanol (média)
    ethanol_percent = df_trip[' Alcohol fuel percentage (%)'].mean()
    
    # Fuel rate médio (l/hr)
    fuel_rate_avg = df_trip[' Fuel rate (l/hr)'].mean()
    
    # Duração da viagem (segundos)
    trip_duration = df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']
    
    return {
        'vin': vin,
        'trip_id': trip_id,
        'timestamp': int(trip_start_time.timestamp()),
        'start_lat_private': start_lat_private,
        'start_lon_private': start_lon_private,
        'end_lat_private': end_lat_private,
        'end_lon_private': end_lon_private,
        'start_elevation': start_elevation,
        'end_elevation': end_elevation,
        'total_distance_km': total_distance_km,  # ✨ Distância real calculada (sem DP)
        'avg_speed': avg_speed,
        'ethanol_percent': ethanol_percent,
        'fuel_rate_avg': fuel_rate_avg,
        'trip_duration': trip_duration,
        'num_samples': len(df_trip)
    }


def process_obdlink_telemetry(input_csv: str, output_csv: str, 
                               vin: str = "OBD_VEHICLE", 
                               epsilon: float = 0.5):
    """
    Processa OBDLink.csv para formato compatível com E1RegistryTelemetry
    
    Args:
        input_csv: Caminho do OBDLink.csv
        output_csv: Caminho do CSV de saída
        vin: VIN/identificador do veículo
        epsilon: Parâmetro de privacidade diferencial
    """
    print("="*70)
    print("🚗 PROCESSAMENTO SIMPLIFICADO - TELEMETRIA OBD")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"📄 Saída: {output_csv}")
    print(f"🔖 VIN: {vin}")
    print(f"🔐 Epsilon (ε): {epsilon}")
    print(f"📊 Differential Privacy: {'✓ Ativo' if DP_AVAILABLE else '✗ Desabilitado'}")
    print("="*70)
    
    # Ler CSV
    print("\n📊 Carregando dados...")
    df = pd.read_csv(input_csv, skiprows=2)
    
    print(f"   Total de registros: {len(df):,}")
    print(f"   Período: {df['Time (sec)'].min():.1f}s a {df['Time (sec)'].max():.1f}s")
    print(f"   Duração total: {(df['Time (sec)'].max() - df['Time (sec)'].min()) / 3600:.2f}h")
    
    # Extrair timestamp inicial
    with open(input_csv, 'r') as f:
        first_line = f.readline()
        if 'StartTime' in first_line:
            time_str = first_line.split('=')[1].strip().split('.')[0]
            start_timestamp = datetime.strptime(time_str, "%m/%d/%Y %I:%M:%S %p")
        else:
            start_timestamp = datetime.now()
    
    print(f"   Timestamp inicial: {start_timestamp}")
    
    # Identificar viagens
    print("\n🔍 Identificando viagens...")
    trips = identify_trips(df, max_gap_seconds=300, min_trip_duration=60)
    print(f"   Viagens identificadas: {len(trips)}")
    
    # Processar viagens
    print("\n🔄 Processando viagens com Differential Privacy...")
    results = []
    
    for trip_id, (start_idx, end_idx) in enumerate(trips):
        df_trip = df.iloc[start_idx:end_idx+1]
        
        print(f"\n[{trip_id+1}/{len(trips)}] Viagem {trip_id+1}")
        print(f"   Registros: {len(df_trip)}")
        print(f"   Duração: {df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']:.1f}s")
        
        try:
            trip_data = process_trip_telemetry(
                df_trip, trip_id+1, start_timestamp, vin, epsilon
            )
            
            results.append(trip_data)
            
            print(f"   ✓ Distância calculada: {trip_data['total_distance_km']:.3f} km ({trip_data['num_samples']} pontos)")
            print(f"   ✓ Velocidade média: {trip_data['avg_speed']:.1f} km/h")
            print(f"   ✓ Etanol: {trip_data['ethanol_percent']:.1f}%")
            print(f"   ✓ Fuel rate: {trip_data['fuel_rate_avg']:.2f} l/hr")
            print(f"   ✓ Elevação: {trip_data['start_elevation']}m → {trip_data['end_elevation']}m")
            
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    # Criar DataFrame
    df_result = pd.DataFrame(results)
    
    # Salvar
    df_result.to_csv(output_csv, index=False)
    
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*70)
    print(f"Viagens processadas: {len(df_result)}")
    print(f"Distância total percorrida: {df_result['total_distance_km'].sum():.2f} km")
    print(f"Distância média por viagem: {df_result['total_distance_km'].mean():.2f} km")
    print(f"Velocidade média geral: {df_result['avg_speed'].mean():.1f} km/h")
    print(f"Percentual médio de etanol: {df_result['ethanol_percent'].mean():.1f}%")
    print(f"Fuel rate médio: {df_result['fuel_rate_avg'].mean():.2f} l/hr")
    print(f"\n💾 Dados salvos em: {output_csv}")
    print("="*70)
    
    print("\n✅ Próximo passo:")
    print("   Enviar ao blockchain:")
    print(f"   python3 send_telemetry_to_blockchain.py {output_csv}")
    
    return df_result


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 process_obdlink_telemetry.py <OBDLink.csv> [saida.csv] [VIN] [epsilon]")
        print("\nExemplo:")
        print("  python3 process_obdlink_telemetry.py ../data/OBDLink.csv trips_telemetry.csv VEHICLE_001 0.5")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trips_telemetry.csv'
    vin = sys.argv[3] if len(sys.argv) > 3 else 'OBD_VEHICLE'
    epsilon = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    
    process_obdlink_telemetry(input_file, output_file, vin, epsilon)


if __name__ == "__main__":
    main()
