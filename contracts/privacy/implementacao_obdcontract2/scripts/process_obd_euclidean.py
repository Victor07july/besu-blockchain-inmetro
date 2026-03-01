#!/usr/bin/env python3
"""
Script para processar OBDLink.csv com distância euclidiana e emissão CO2
Implementa fórmulas de monetização E1 comparativa (meta vs real)

Entrada: OBDLink.csv (dados brutos OBD)
Saída: trips_processed.csv (dados agregados por viagem)

Autor: Victor
Data: 2026-02-28
"""

import pandas as pd
import numpy as np
import sys
import warnings
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import math

warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÕES ====================
# Constantes de emissão CO2
EMISSAO_GASOLINA = 2.31  # kg CO2 por litro
EMISSAO_ETANOL = 1.51    # kg CO2 por litro

# Consumo do fabricante (exemplo - ajustar conforme veículo)
CONSUMO_FABRICANTE = 12.0  # km/l (urbano/misto)

# Preço do carbono
CARBON_PRICE = 50.0  # R$ por tonelada CO2

# ==================== TRIGGERS/MODOS ====================
# Modo de processamento de viagens
SINGLE_TRIP_MODE = True  # True: CSV inteiro = 1 viagem | False: Auto-segmentação por gaps

# Processamento incremental (para CSVs grandes)
INCREMENTAL_READ = False  # True: Ler CSV de X em X linhas | False: Carregar tudo na memória
READ_CHUNK_SIZE = 5       # Quantas linhas ler por vez (usado se INCREMENTAL_READ=True)
                          # Exemplo: 5 = lê 5 linhas, processa, lê mais 5, até o fim
                          # No final, agrega tudo como 1 viagem
# =======================================================


def euclidean_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância euclidiana aproximada entre dois pontos GPS
    
    Args:
        lat1, lon1: Coordenadas do ponto 1
        lat2, lon2: Coordenadas do ponto 2
        
    Returns:
        Distância em km
    """
    # Latitude média para correção de longitude
    lat_avg = math.radians((lat1 + lat2) / 2)
    
    # Converter diferenças para km
    # 1 grau latitude ≈ 111.32 km
    # 1 grau longitude ≈ 111.32 × cos(latitude) km
    dx = (lon2 - lon1) * 111.32 * math.cos(lat_avg)
    dy = (lat2 - lat1) * 111.32
    
    distance = math.sqrt(dx**2 + dy**2)
    return distance


def add_laplace_noise(value: float, epsilon: float = 0.5, sensitivity: float = 0.001) -> float:
    """
    Adiciona ruído Laplace para privacidade diferencial
    
    Args:
        value: Valor original (coordenada)
        epsilon: Parâmetro de privacidade
        sensitivity: Sensibilidade (0.001 grau ≈ 111 metros)
        
    Returns:
        Valor com ruído
    """
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    return value + noise


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


def process_trip(df_trip: pd.DataFrame, trip_id: int, start_timestamp: datetime, 
                 vin: str, epsilon: float = 0.5) -> Dict:
    """
    Processa uma viagem completa:
    1. Calcula distância euclidiana somando todos segmentos
    2. Calcula emissão CO2 real baseada em fuel rate
    3. Calcula meta CO2 baseada em consumo do fabricante
    4. Calcula valor E1 (diferença × preço carbono)
    5. Aplica DP nas coordenadas de início/fim
    
    Args:
        df_trip: DataFrame com dados da viagem
        trip_id: ID da viagem
        start_timestamp: Timestamp de início da coleta
        vin: VIN do veículo
        epsilon: Parâmetro de privacidade diferencial
        
    Returns:
        Dicionário com todos os dados processados
    """
    # ========== PASSO 1: CALCULAR DISTÂNCIA EUCLIDIANA ==========
    total_distance_km = 0.0
    
    for i in range(len(df_trip) - 1):
        lat1 = df_trip.iloc[i][' Latitude (deg)']
        lon1 = df_trip.iloc[i][' Longitude (deg)']
        lat2 = df_trip.iloc[i+1][' Latitude (deg)']
        lon2 = df_trip.iloc[i+1][' Longitude (deg)']
        
        segment_distance = euclidean_distance_km(lat1, lon1, lat2, lon2)
        total_distance_km += segment_distance
    
    # ========== PASSO 2: CALCULAR EMISSÃO CO2 REAL ==========
    total_co2_kg = 0.0
    total_fuel_liters = 0.0
    
    for i in range(len(df_trip) - 1):
        # Δt em segundos
        delta_t = df_trip.iloc[i+1]['Time (sec)'] - df_trip.iloc[i]['Time (sec)']
        
        # Combustível consumido (l/hr × s / 3600)
        fuel_rate = df_trip.iloc[i][' Fuel rate (l/hr)']
        fuel_consumed = fuel_rate * (delta_t / 3600.0)
        total_fuel_liters += fuel_consumed
        
        # Mix de combustível
        ethanol_pct = df_trip.iloc[i][' Alcohol fuel percentage (%)'] / 100.0
        gasoline_pct = 1.0 - ethanol_pct
        
        # Emissão do segmento
        co2_segment = fuel_consumed * (
            gasoline_pct * EMISSAO_GASOLINA +
            ethanol_pct * EMISSAO_ETANOL
        )
        total_co2_kg += co2_segment
    
    # ========== PASSO 3: CALCULAR META CO2 ==========
    # Combustível meta baseado no consumo do fabricante
    fuel_meta = total_distance_km / CONSUMO_FABRICANTE  # litros
    
    # Usar mix etanol médio da viagem
    avg_ethanol_pct = df_trip[' Alcohol fuel percentage (%)'].mean() / 100.0
    avg_gasoline_pct = 1.0 - avg_ethanol_pct
    
    co2_meta_kg = fuel_meta * (
        avg_gasoline_pct * EMISSAO_GASOLINA +
        avg_ethanol_pct * EMISSAO_ETANOL
    )
    
    # ========== PASSO 4: CALCULAR VALOR E1 ==========
    # Diferença: meta - real (positivo = economizou, negativo = desperdiçou)
    delta_co2 = co2_meta_kg - total_co2_kg
    
    # Monetizar: (kg / 1000) × preço = R$
    valor_e1 = (delta_co2 / 1000.0) * CARBON_PRICE
    
    # ========== PASSO 5: APLICAR PRIVACIDADE DIFERENCIAL ==========
    # Coordenadas originais
    start_lat_orig = df_trip.iloc[0][' Latitude (deg)']
    start_lon_orig = df_trip.iloc[0][' Longitude (deg)']
    end_lat_orig = df_trip.iloc[-1][' Latitude (deg)']
    end_lon_orig = df_trip.iloc[-1][' Longitude (deg)']
    
    # Aplicar DP
    start_lat_private = add_laplace_noise(start_lat_orig, epsilon)
    start_lon_private = add_laplace_noise(start_lon_orig, epsilon)
    end_lat_private = add_laplace_noise(end_lat_orig, epsilon)
    end_lon_private = add_laplace_noise(end_lon_orig, epsilon)
    
    # Calcular deslocamento causado pelo DP
    start_displacement = euclidean_distance_km(start_lat_orig, start_lon_orig, 
                                               start_lat_private, start_lon_private)
    end_displacement = euclidean_distance_km(end_lat_orig, end_lon_orig, 
                                             end_lat_private, end_lon_private)
    
    # ========== DADOS ADICIONAIS ==========
    trip_start_time = start_timestamp + timedelta(seconds=float(df_trip.iloc[0]['Time (sec)']))
    trip_duration = df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']
    avg_speed = df_trip[' Vehicle speed (km/h)'].mean()
    
    return {
        'vin': vin,
        'trip_id': trip_id,
        'timestamp': int(trip_start_time.timestamp()),
        'total_distance_km': total_distance_km,
        'fuel_consumed_liters': total_fuel_liters,
        'co2_real_kg': total_co2_kg,
        'co2_meta_kg': co2_meta_kg,
        'delta_co2_kg': delta_co2,
        'valor_e1_reais': valor_e1,
        'avg_ethanol_percent': avg_ethanol_pct * 100,
        'start_lat_orig': start_lat_orig,
        'start_lon_orig': start_lon_orig,
        'end_lat_orig': end_lat_orig,
        'end_lon_orig': end_lon_orig,
        'start_lat_private': start_lat_private,
        'start_lon_private': start_lon_private,
        'end_lat_private': end_lat_private,
        'end_lon_private': end_lon_private,
        'start_displacement_km': start_displacement,
        'end_displacement_km': end_displacement,
        'trip_duration_sec': trip_duration,
        'avg_speed_kmh': avg_speed,
        'num_samples': len(df_trip)
    }


def process_obdlink_csv(input_csv: str, output_csv: str, vin: str = "OBD_VEHICLE",
                        epsilon: float = 0.5, consumo_fabricante: float = CONSUMO_FABRICANTE):
    """
    Processa OBDLink.csv completo
    
    Args:
        input_csv: Caminho do arquivo de entrada
        output_csv: Caminho do arquivo de saída
        vin: VIN/identificador do veículo
        epsilon: Parâmetro de privacidade diferencial
        consumo_fabricante: Consumo declarado pelo fabricante (km/l)
    """
    global CONSUMO_FABRICANTE
    CONSUMO_FABRICANTE = consumo_fabricante
    
    # Determinar modo de processamento
    if SINGLE_TRIP_MODE and INCREMENTAL_READ:
        mode_desc = f"VIAGEM ÚNICA + LEITURA INCREMENTAL ({READ_CHUNK_SIZE} linhas por vez)"
    elif SINGLE_TRIP_MODE:
        mode_desc = "VIAGEM ÚNICA (CSV inteiro na memória)"
    else:
        mode_desc = "AUTO-SEGMENTAÇÃO (gaps de tempo)"
    
    print("="*70)
    print("🚗 PROCESSAMENTO OBD - DISTÂNCIA EUCLIDIANA + EMISSÃO CO2")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"📄 Saída: {output_csv}")
    print(f"🔖 VIN: {vin}")
    print(f"🔐 Epsilon (ε): {epsilon}")
    print(f"🏭 Consumo fabricante: {consumo_fabricante} km/l")
    print(f"💰 Preço carbono: R$ {CARBON_PRICE}/ton")
    print(f"🚦 Modo: {mode_desc}")
    print("="*70)
    
    # Extrair timestamp inicial
    with open(input_csv, 'r') as f:
        first_line = f.readline()
        if 'StartTime' in first_line:
            try:
                time_str = first_line.split('=')[1].strip()
                parts = time_str.split()
                if len(parts) == 3:
                    date_str = parts[0]
                    time_str_clean = parts[1].split('.')[0]
                    am_pm = parts[2]
                    datetime_str = f"{date_str} {time_str_clean} {am_pm}"
                    start_timestamp = datetime.strptime(datetime_str, "%m/%d/%Y %I:%M:%S %p")
                else:
                    start_timestamp = datetime.now()
            except:
                start_timestamp = datetime.now()
        else:
            start_timestamp = datetime.now()
    
    print(f"   Timestamp inicial: {start_timestamp}")
    
    # Ler CSV (incremental ou completo)
    if INCREMENTAL_READ and SINGLE_TRIP_MODE:
        print(f"\n📊 Carregando dados incrementalmente ({READ_CHUNK_SIZE} linhas por vez)...")
        df_list = []
        chunk_count = 0
        
        # Ler em chunks
        for chunk in pd.read_csv(input_csv, skiprows=2, chunksize=READ_CHUNK_SIZE):
            df_list.append(chunk)
            chunk_count += 1
            if chunk_count % 100 == 0:  # Feedback a cada 100 chunks
                print(f"   Lidos: {chunk_count * READ_CHUNK_SIZE:,} registros...")
        
        # Concatenar todos os chunks
        df = pd.concat(df_list, ignore_index=True)
        print(f"   Total de chunks processados: {chunk_count}")
        print(f"   Total de registros: {len(df):,}")
    else:
        print("\n📊 Carregando dados...")
        df = pd.read_csv(input_csv, skiprows=2)
        print(f"   Total de registros: {len(df):,}")
    
    print(f"   Duração total: {(df['Time (sec)'].max() - df['Time (sec)'].min()) / 3600:.2f}h")
    
    # Identificar viagens baseado no modo configurado
    if SINGLE_TRIP_MODE:
        print("\n🚦 Modo VIAGEM ÚNICA: processando todos os dados como 1 viagem")
        trips = [(0, len(df)-1)]
    else:
        print("\n🔍 Modo AUTO-SEGMENTAÇÃO: identificando viagens por gaps de tempo...")
        trips = identify_trips(df, max_gap_seconds=300, min_trip_duration=60)
    
    print(f"   Viagens identificadas: {len(trips)}")
    
    # Processar viagens
    print("\n🔄 Processando viagens...")
    results = []
    
    for idx, (start_idx, end_idx) in enumerate(trips):
        df_trip = df.iloc[start_idx:end_idx+1]
        
        print(f"\n[{idx+1}/{len(trips)}] Viagem {idx+1}")
        print(f"   Registros: {len(df_trip)}")
        print(f"   Duração: {df_trip.iloc[-1]['Time (sec)'] - df_trip.iloc[0]['Time (sec)']:.1f}s")
        
        try:
            trip_data = process_trip(df_trip, idx+1, start_timestamp, vin, epsilon)
            
            results.append(trip_data)
            
            print(f"   📏 Distância: {trip_data['total_distance_km']:.2f} km")
            print(f"   ⛽ Combustível: {trip_data['fuel_consumed_liters']:.3f} l")
            print(f"   🏭 CO2 real: {trip_data['co2_real_kg']:.3f} kg")
            print(f"   🎯 CO2 meta: {trip_data['co2_meta_kg']:.3f} kg")
            print(f"   📊 Diferença: {trip_data['delta_co2_kg']:+.3f} kg")
            print(f"   💰 Valor E1: R$ {trip_data['valor_e1_reais']:+.4f}")
            
            # Mostrar coordenadas antes e depois da privacidade diferencial
            print(f"\n   🔐 PRIVACIDADE DIFERENCIAL (ε={epsilon}):")
            print(f"   📍 Start Original:  ({trip_data['start_lat_orig']:.6f}, {trip_data['start_lon_orig']:.6f})")
            print(f"   🔒 Start com DP:    ({trip_data['start_lat_private']:.6f}, {trip_data['start_lon_private']:.6f})")
            print(f"   📏 Deslocamento:    {trip_data['start_displacement_km']*1000:.1f} metros")
            print(f"   📍 End Original:    ({trip_data['end_lat_orig']:.6f}, {trip_data['end_lon_orig']:.6f})")
            print(f"   🔒 End com DP:      ({trip_data['end_lat_private']:.6f}, {trip_data['end_lon_private']:.6f})")
            print(f"   📏 Deslocamento:    {trip_data['end_displacement_km']*1000:.1f} metros")
            
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
    print(f"Distância total: {df_result['total_distance_km'].sum():.2f} km")
    print(f"Combustível total: {df_result['fuel_consumed_liters'].sum():.2f} l")
    print(f"CO2 real total: {df_result['co2_real_kg'].sum():.2f} kg")
    print(f"CO2 meta total: {df_result['co2_meta_kg'].sum():.2f} kg")
    print(f"Economia CO2: {df_result['delta_co2_kg'].sum():+.2f} kg")
    print(f"Saldo E1 total: R$ {df_result['valor_e1_reais'].sum():+.2f}")
    
    creditos = df_result[df_result['valor_e1_reais'] > 0]['valor_e1_reais'].sum()
    debitos = abs(df_result[df_result['valor_e1_reais'] < 0]['valor_e1_reais'].sum())
    
    print(f"\n💰 Créditos: R$ {creditos:.2f}")
    print(f"💸 Débitos: R$ {debitos:.2f}")
    print(f"📈 Saldo líquido: R$ {creditos - debitos:+.2f}")
    
    print(f"\n💾 Dados salvos em: {output_csv}")
    print("="*70)
    
    return df_result


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 process_obd_euclidean.py <OBDLink.csv> [saida.csv] [VIN] [epsilon] [consumo_fab]")
        print("\nParâmetros:")
        print("  OBDLink.csv      : Arquivo de entrada (obrigatório)")
        print("  saida.csv        : Arquivo de saída (padrão: trips_processed.csv)")
        print("  VIN              : Identificador do veículo (padrão: OBD_VEHICLE)")
        print("  epsilon          : Parâmetro de privacidade (padrão: 0.5)")
        print("  consumo_fab      : Consumo do fabricante em km/l (padrão: 12.0)")
        print("\nConfiguração do modo de processamento:")
        print("  Edite as variáveis no topo do script:")
        print("    SINGLE_TRIP_MODE  : True=Todo CSV como 1 viagem | False=Auto-segmentação")
        print("    INCREMENTAL_READ  : True=Ler de X em X linhas | False=Carregar tudo")
        print("    READ_CHUNK_SIZE   : Quantas linhas ler por vez (ex: 5)")
        print("\nExemplo:")
        print("  # Leitura incremental (5 em 5 linhas, tudo vira 1 viagem):")
        print("  SINGLE_TRIP_MODE=True, INCREMENTAL_READ=True, READ_CHUNK_SIZE=5")
        print("\n  python3 process_obd_euclidean.py ../data/OBDLink.csv trips.csv VEHICLE_001 0.5 12.0")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trips_processed.csv'
    vin = sys.argv[3] if len(sys.argv) > 3 else 'OBD_VEHICLE'
    epsilon = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    consumo_fab = float(sys.argv[5]) if len(sys.argv) > 5 else 12.0
    
    process_obdlink_csv(input_file, output_file, vin, epsilon, consumo_fab)


if __name__ == "__main__":
    main()
