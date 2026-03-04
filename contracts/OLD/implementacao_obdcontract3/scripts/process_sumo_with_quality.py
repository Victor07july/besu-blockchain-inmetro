#!/usr/bin/env python3
"""
Processa dados OBDLink com cálculo de qualidade integrado

Entrada: OBDLink.csv (formato original)
Saída: CSV com CO2, qualidade e créditos ajustados

Autor: Victor
Data: 2026-03-03
"""

import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from calculate_quality_score import calculate_quality_score, format_quality_report


def process_obdlink_with_quality(input_csv: str, 
                                 output_csv: str,
                                 vehicle_id: str = 'OBD_VEHICLE',
                                 co2_per_km: float = 0.175):
    """
    Processa OBDLink.csv com cálculo de qualidade
    
    Args:
        input_csv: Arquivo OBDLink.csv
        output_csv: Arquivo de saída com resultados
        vehicle_id: ID do veículo
        co2_per_km: Emissão de CO2 em kg/km (padrão: 175g/km)
    """
    
    print("="*70)
    print("🎯 PROCESSAMENTO OBDLINK COM SCORE DE QUALIDADE")
    print("="*70)
    print(f"📂 Entrada: {input_csv}")
    print(f"💾 Saída: {output_csv}")
    print(f"🚗 Veículo: {vehicle_id}")
    print(f"🏭 CO2: {co2_per_km} kg/km")
    print("="*70)
    
    # Ler CSV do OBDLink (pular 2 linhas de cabeçalho)
    print("\n📊 Carregando dados OBDLink...")
    df = pd.read_csv(input_csv, skiprows=2)
    
    print(f"   Registros: {len(df):,}")
    
    # Verificar colunas necessárias
    required_cols = {
        'Time (sec)': 'timestamp',
        'Latitude (deg)': 'lat',
        'Longitude (deg)': 'lon'
    }
    
    missing_cols = [col for col in required_cols.keys() if col not in df.columns]
    if missing_cols:
        print(f"\n❌ Erro: Colunas faltando: {missing_cols}")
        print(f"   Colunas disponíveis: {list(df.columns)[:5]}...")
        sys.exit(1)
    
    # Renomear colunas para formato padrão
    df_clean = df[list(required_cols.keys())].copy()
    df_clean.columns = ['timestamp', 'lat', 'lon']
    
    # Remover pontos com GPS inválido (0,0 ou NaN)
    initial_count = len(df_clean)
    df_clean = df_clean.dropna(subset=['lat', 'lon'])
    df_clean = df_clean[(df_clean['lat'] != 0) & (df_clean['lon'] != 0)]
    
    if len(df_clean) < initial_count:
        print(f"   ⚠️  Removidos {initial_count - len(df_clean)} pontos com GPS inválido")
    
    print(f"   Pontos válidos: {len(df_clean):,}")
    print(f"   Duração: {df_clean['timestamp'].max():.1f} segundos ({df_clean['timestamp'].max()/60:.1f} min)")
    
    # Preparar pontos para cálculo de qualidade
    print(f"\n🔄 Calculando qualidade dos dados...")
    trajectory_points = []
    for _, row in df_clean.iterrows():
        trajectory_points.append({
            'lat': row['lat'],
            'lon': row['lon'],
            'timestamp': row['timestamp']
        })
    
    # Calcular score de qualidade
    quality_result = calculate_quality_score(trajectory_points)
    
    # Calcular distância total usando Haversine
    import math
    total_distance_km = 0
    for i in range(1, len(df_clean)):
        lat1 = df_clean.iloc[i-1]['lat']
        lon1 = df_clean.iloc[i-1]['lon']
        lat2 = df_clean.iloc[i]['lat']
        lon2 = df_clean.iloc[i]['lon']
        
        # Haversine
        R = 6371  # Raio da Terra em km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        total_distance_km += distance
    
    # Calcular CO2 bruto (sem qualidade)
    co2_raw = total_distance_km * co2_per_km
    
    # Aplicar multiplicador de qualidade
    co2_credits = co2_raw * quality_result['multiplier']
    
    # Tempo total
    duration_seconds = df_clean['timestamp'].max() - df_clean['timestamp'].min()
    
    # Montar resultado
    result = {
        'vehicle_id': vehicle_id,
        'num_points': len(df_clean),
        'duration_seconds': duration_seconds,
        'duration_minutes': duration_seconds / 60,
        'total_distance_km': total_distance_km,
        'co2_raw_kg': co2_raw,
        'quality_score': quality_result['score'],
        'quality_grade': quality_result['grade'],
        'quality_multiplier': quality_result['multiplier'],
        'co2_credits_kg': co2_credits,
        'credit_reduction_percent': (1 - quality_result['multiplier']) * 100,
        'redundancy_ratio': quality_result['redundancy'].get('redundancy_ratio', 0),
        'avg_interval_seconds': quality_result['sparsity'].get('avg_interval', 0),
        'max_gap_seconds': quality_result['sparsity'].get('max_gap', 0),
        'start_lat': df_clean.iloc[0]['lat'],
        'start_lon': df_clean.iloc[0]['lon'],
        'end_lat': df_clean.iloc[-1]['lat'],
        'end_lon': df_clean.iloc[-1]['lon'],
    }
    
    # Mostrar resultados
    print(f"\n📏 RESULTADOS:")
    print(f"   Pontos: {result['num_points']:,}")
    print(f"   Duração: {result['duration_minutes']:.1f} minutos")
    print(f"   Distância: {result['total_distance_km']:.2f} km")
    print(f"   CO2 bruto: {result['co2_raw_kg']:.3f} kg")
    
    print(f"\n📊 QUALIDADE:")
    print(f"   Score: {result['quality_score']:.1f}/100")
    print(f"   Nota: {result['quality_grade']}")
    print(f"   Multiplicador: {result['quality_multiplier']:.3f}")
    print(f"   Redundância: {result['redundancy_ratio']*100:.1f}% parado")
    print(f"   Intervalo médio: {result['avg_interval_seconds']:.1f}s")
    print(f"   Maior gap: {result['max_gap_seconds']:.1f}s")
    
    print(f"\n💰 CRÉDITOS:")
    print(f"   CO2 com qualidade: {result['co2_credits_kg']:.3f} kg")
    print(f"   Redução: {result['credit_reduction_percent']:.1f}%")
    print(f"   Diferença: {result['co2_raw_kg'] - result['co2_credits_kg']:.3f} kg perdidos")
    
    # Relatório detalhado
    print(f"\n{format_quality_report(quality_result)}")
    
    # Salvar resultado
    df_result = pd.DataFrame([result])
    df_result.to_csv(output_csv, index=False)
    
    print(f"\n💾 Resultados salvos em: {output_csv}")
    print("="*70)
    
    return result


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 process_obdlink_with_quality.py <OBDLink.csv> [output.csv] [vehicle_id] [co2_per_km]")
        print("\nParâmetros:")
        print("  OBDLink.csv  : Arquivo OBDLink original (obrigatório)")
        print("  output.csv   : Arquivo de saída (padrão: obdlink_quality_results.csv)")
        print("  vehicle_id   : ID do veículo (padrão: OBD_VEHICLE)")
        print("  co2_per_km   : Emissão em kg/km (padrão: 0.175)")
        print("\nExemplo:")
        print("  python3 process_obdlink_with_quality.py ../data/OBDLink.csv results.csv CAR_123 0.175")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'obdlink_quality_results.csv'
    vehicle_id = sys.argv[3] if len(sys.argv) > 3 else 'OBD_VEHICLE'
    co2_per_km = float(sys.argv[4]) if len(sys.argv) > 4 else 0.175
    
    process_obdlink_with_quality(input_file, output_file, vehicle_id, co2_per_km)


if __name__ == "__main__":
    main()
