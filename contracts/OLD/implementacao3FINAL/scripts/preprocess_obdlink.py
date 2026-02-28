#!/usr/bin/env python3
"""
Script para pré-processar dados OBDLink.csv e gerar formato compatível
com o pipeline de Differential Privacy e Blockchain

Entrada: OBDLink.csv (dados brutos de telemetria OBD)
Saída: trips.csv (viagens agregadas prontas para DP + blockchain)

Autor: Victor
Data: 2026-02-23
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Tuple
import sys


def identify_trips(df: pd.DataFrame, max_gap_seconds: float = 300, 
                   min_trip_duration: float = 60) -> List[Tuple[int, int]]:
    """
    Identifica viagens baseado em intervalos de tempo sem registro
    
    Args:
        df: DataFrame com coluna 'Time (sec)'
        max_gap_seconds: Intervalo máximo entre pontos da mesma viagem
        min_trip_duration: Duração mínima de uma viagem válida
        
    Returns:
        Lista de tuplas (índice_início, índice_fim) para cada viagem
    """
    trips = []
    trip_start = 0
    
    for i in range(1, len(df)):
        # Calcular gap entre pontos consecutivos
        time_gap = df.iloc[i]['Time (sec)'] - df.iloc[i-1]['Time (sec)']
        
        # Se gap > threshold, terminar viagem atual
        if time_gap > max_gap_seconds:
            trip_duration = df.iloc[i-1]['Time (sec)'] - df.iloc[trip_start]['Time (sec)']
            
            # Salvar viagem se duração mínima for atendida
            if trip_duration >= min_trip_duration:
                trips.append((trip_start, i-1))
            
            # Iniciar nova viagem
            trip_start = i
    
    # Adicionar última viagem
    trip_duration = df.iloc[-1]['Time (sec)'] - df.iloc[trip_start]['Time (sec)']
    if trip_duration >= min_trip_duration:
        trips.append((trip_start, len(df)-1))
    
    return trips


def classify_road_type(speed_kmh: float) -> str:
    """
    Classifica tipo de via baseado na velocidade média
    
    Args:
        speed_kmh: Velocidade média em km/h
        
    Returns:
        'highway' ou 'city'
    """
    # Threshold: > 60 km/h = rodovia, <= 60 km/h = cidade
    return 'highway' if speed_kmh > 60 else 'city'


def calculate_distance_from_gps(lat1: float, lon1: float, 
                                 lat2: float, lon2: float) -> float:
    """
    Calcula distância entre dois pontos GPS (fórmula de Haversine)
    
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


def process_trip(df_trip: pd.DataFrame, trip_id: int, 
                 start_timestamp: datetime, vin: str = "OBD_VEHICLE_001") -> dict:
    """
    Processa uma viagem e extrai métricas agregadas
    
    Args:
        df_trip: DataFrame com dados da viagem
        trip_id: ID da viagem
        start_timestamp: Timestamp de início da coleta
        vin: Identificador do veículo
        
    Returns:
        Dicionário com dados da viagem processados
    """
    # Coordenadas de início e fim
    start_lat = df_trip.iloc[0][' Latitude (deg)']
    start_lon = df_trip.iloc[0][' Longitude (deg)']
    end_lat = df_trip.iloc[-1][' Latitude (deg)']
    end_lon = df_trip.iloc[-1][' Longitude (deg)']
    
    # Timestamp da viagem
    trip_start_time = start_timestamp + timedelta(seconds=float(df_trip.iloc[0]['Time (sec)']))
    
    # Calcular distância total por segmentos
    highway_distance = 0
    city_distance = 0
    
    for i in range(len(df_trip) - 1):
        # Coordenadas do segmento
        lat1 = df_trip.iloc[i][' Latitude (deg)']
        lon1 = df_trip.iloc[i][' Longitude (deg)']
        lat2 = df_trip.iloc[i+1][' Latitude (deg)']
        lon2 = df_trip.iloc[i+1][' Longitude (deg)']
        
        # Velocidade média do segmento
        speed = (df_trip.iloc[i][' Vehicle speed (km/h)'] + 
                 df_trip.iloc[i+1][' Vehicle speed (km/h)']) / 2
        
        # Distância do segmento
        segment_distance = calculate_distance_from_gps(lat1, lon1, lat2, lon2)
        
        # Classificar e acumular
        if classify_road_type(speed) == 'highway':
            highway_distance += segment_distance
        else:
            city_distance += segment_distance
    
    # Percentual de álcool (média da viagem)
    ethanol_percent = df_trip[' Alcohol fuel percentage (%)'].mean()
    
    # Fuel rate médio (l/hr)
    fuel_rate_avg = df_trip[' Fuel rate (l/hr)'].mean()
    
    # Calcular emissão total
    # Fórmula simplificada: fuel_rate * duração * fator_emissão
    trip_duration_hours = (df_trip.iloc[-1]['Time (sec)'] - 
                           df_trip.iloc[0]['Time (sec)']) / 3600
    
    # Emissão (gCO2): fuel_rate (l/hr) × duração (hr) × densidade_combustível × fator_emissão
    # Gasolina: ~2.31 kg CO2/l, Etanol: ~1.51 kg CO2/l
    # Simplificação: usar proporção de etanol
    eth_ratio = ethanol_percent / 100
    gas_emission_factor = 2310  # g CO2/l
    eth_emission_factor = 1510  # g CO2/l
    
    emission_factor = (gas_emission_factor * (1 - eth_ratio) + 
                      eth_emission_factor * eth_ratio)
    
    total_fuel_liters = fuel_rate_avg * trip_duration_hours
    total_emission = total_fuel_liters * emission_factor
    
    # Tipo de combustível
    if ethanol_percent > 80:
        fuel_type = 'Etanol'
    elif ethanol_percent < 20:
        fuel_type = 'Gasolina'
    else:
        fuel_type = 'Flex'
    
    return {
        'VIN': vin,
        'trip_id': trip_id,
        'start_time': trip_start_time.isoformat(),
        'start_location': f"{start_lat}, {start_lon}",
        'end_location': f"{end_lat}, {end_lon}",
        'highway (distance)': highway_distance,
        'city (distance)': city_distance,
        'total_distance': highway_distance + city_distance,
        'ethanol (%)': ethanol_percent,
        'fuel_type': fuel_type,
        'emission': total_emission,
        'fuel_consumed_liters': total_fuel_liters,
        'trip_duration_seconds': df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']
    }


def preprocess_obdlink(input_csv: str, output_csv: str, vin: str = "OBD_VEHICLE_001"):
    """
    Processa arquivo OBDLink.csv e gera arquivo de viagens agregadas
    
    Args:
        input_csv: Caminho do CSV OBDLink
        output_csv: Caminho do CSV de saída
        vin: VIN/identificador do veículo
    """
    print("="*70)
    print("🚗 PRÉ-PROCESSAMENTO DE DADOS OBDLink")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"📄 Saída: {output_csv}")
    print(f"🔖 VIN: {vin}")
    print("="*70)
    
    # Ler CSV pulando linhas de comentário
    print("\n📊 Carregando dados...")
    df = pd.read_csv(input_csv, skiprows=2)
    
    print(f"   Total de registros: {len(df)}")
    print(f"   Período: {df['Time (sec)'].min():.1f}s a {df['Time (sec)'].max():.1f}s")
    print(f"   Duração total: {(df['Time (sec)'].max() - df['Time (sec)'].min()) / 3600:.2f}h")
    
    # Extrair timestamp de início do arquivo
    with open(input_csv, 'r') as f:
        first_line = f.readline()
        # Parse: # StartTime = 01/19/2024 01:25:31.1282 PM
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
    
    # Processar cada viagem
    print("\n🔄 Processando viagens...")
    results = []
    
    for trip_id, (start_idx, end_idx) in enumerate(trips):
        df_trip = df.iloc[start_idx:end_idx+1]
        
        print(f"\n[{trip_id+1}/{len(trips)}] Viagem {trip_id+1}")
        print(f"   Registros: {len(df_trip)}")
        print(f"   Duração: {df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']:.1f}s")
        
        try:
            trip_data = process_trip(df_trip, trip_id+1, start_timestamp, vin)
            results.append(trip_data)
            
            print(f"   ✓ Distância highway: {trip_data['highway (distance)']:.2f} km")
            print(f"   ✓ Distância city: {trip_data['city (distance)']:.2f} km")
            print(f"   ✓ Emissão: {trip_data['emission']:.1f} gCO2")
            
        except Exception as e:
            print(f"   ❌ Erro ao processar: {e}")
    
    # Criar DataFrame final
    df_result = pd.DataFrame(results)
    
    # Salvar
    df_result.to_csv(output_csv, index=False)
    
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*70)
    print(f"Total de viagens processadas: {len(df_result)}")
    print(f"Distância total: {df_result['total_distance'].sum():.2f} km")
    print(f"  Highway: {df_result['highway (distance)'].sum():.2f} km")
    print(f"  City: {df_result['city (distance)'].sum():.2f} km")
    print(f"Emissão total: {df_result['emission'].sum():.1f} gCO2")
    print(f"Percentual médio de etanol: {df_result['ethanol (%)'].mean():.1f}%")
    print(f"\n💾 Dados salvos em: {output_csv}")
    print("="*70)
    
    print("\n✅ Próximos passos:")
    print("   1. Aplicar Differential Privacy:")
    print(f"      python3 differential_privacy_gps.py {output_csv}")
    print("   2. Enviar ao blockchain:")
    print(f"      python3 send_to_blockchain.py {output_csv.replace('.csv', '_private.csv')}")
    
    return df_result


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 preprocess_obdlink.py <OBDLink.csv> [saida.csv] [VIN]")
        print("\nExemplo:")
        print("  python3 preprocess_obdlink.py ../data/OBDLink.csv trips.csv VEHICLE_001")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trips_preprocessed.csv'
    vin = sys.argv[3] if len(sys.argv) > 3 else 'OBD_VEHICLE_001'
    
    preprocess_obdlink(input_file, output_file, vin)


if __name__ == "__main__":
    main()
