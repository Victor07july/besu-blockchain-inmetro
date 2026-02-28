#!/usr/bin/env python3
"""
Aplica Differential Privacy (DP) às coordenadas GPS
Adiciona ruído Laplace para proteger localização exata
"""

import argparse
import numpy as np
import pandas as pd

def add_laplace_noise(value, epsilon, sensitivity=1.0):
    """
    Adiciona ruído Laplace a um valor
    
    Args:
        value: Valor original
        epsilon: Parâmetro de privacidade (menor = mais privacidade)
        sensitivity: Sensibilidade da query (default 1.0 para coordenadas)
    
    Returns:
        Valor com ruído adicionado
    """
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    return value + noise

def apply_dp_to_gps(df, epsilon=1.0):
    """
    Aplica DP às coordenadas GPS do DataFrame
    
    Args:
        df: DataFrame com colunas start_lat, start_lon, end_lat, end_lon
        epsilon: Parâmetro de privacidade
    
    Returns:
        DataFrame com coordenadas privatizadas
    """
    print(f"🔐 Aplicando Differential Privacy com epsilon = {epsilon}")
    print(f"   Menor epsilon = Mais privacidade (mais ruído)")
    print(f"   Maior epsilon = Menos privacidade (menos ruído)\n")
    
    # Criar cópias das coordenadas originais (para comparação)
    df['start_lat_original'] = df['start_lat']
    df['start_lon_original'] = df['start_lon']
    df['end_lat_original'] = df['end_lat']
    df['end_lon_original'] = df['end_lon']
    
    # Aplicar DP
    df['start_lat_dp'] = df['start_lat'].apply(lambda x: add_laplace_noise(x, epsilon))
    df['start_lon_dp'] = df['start_lon'].apply(lambda x: add_laplace_noise(x, epsilon))
    df['end_lat_dp'] = df['end_lat'].apply(lambda x: add_laplace_noise(x, epsilon))
    df['end_lon_dp'] = df['end_lon'].apply(lambda x: add_laplace_noise(x, epsilon))
    
    # Calcular erro médio (em graus)
    error_start_lat = np.abs(df['start_lat_dp'] - df['start_lat']).mean()
    error_start_lon = np.abs(df['start_lon_dp'] - df['start_lon']).mean()
    error_end_lat = np.abs(df['end_lat_dp'] - df['end_lat']).mean()
    error_end_lon = np.abs(df['end_lon_dp'] - df['end_lon']).mean()
    
    # Converter para metros (aproximado: 1° ≈ 111 km)
    error_meters = ((error_start_lat + error_end_lat) / 2) * 111000
    
    print(f"📊 Estatísticas do ruído:")
    print(f"   Erro médio latitude start: {error_start_lat:.6f}°")
    print(f"   Erro médio longitude start: {error_start_lon:.6f}°")
    print(f"   Erro médio latitude end: {error_end_lat:.6f}°")
    print(f"   Erro médio longitude end: {error_end_lon:.6f}°")
    print(f"   Erro aproximado: ±{error_meters:.0f} metros")
    
    return df

def parse_location(location_str):
    """
    Parseia string de localização no formato 'lat, lon'
    Ex: "-5.8431992, -35.1977242" -> (-5.8431992, -35.1977242)
    """
    try:
        parts = location_str.strip().split(',')
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return lat, lon
    except:
        return None, None

def load_csv_with_gps(csv_path):
    """
    Carrega CSV com coordenadas GPS nas colunas start_location e end_location
    """
    print(f"📂 Carregando CSV: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Verificar colunas necessárias
    if 'start_location' not in df.columns or 'end_location' not in df.columns:
        raise ValueError("CSV deve conter colunas 'start_location' e 'end_location'")
    
    # Parsear coordenadas
    print("🔍 Parseando coordenadas GPS...")
    
    start_coords = df['start_location'].apply(parse_location)
    end_coords = df['end_location'].apply(parse_location)
    
    df['start_lat'] = [coord[0] for coord in start_coords]
    df['start_lon'] = [coord[1] for coord in start_coords]
    df['end_lat'] = [coord[0] for coord in end_coords]
    df['end_lon'] = [coord[1] for coord in end_coords]
    
    # Remover linhas com coordenadas inválidas
    df = df.dropna(subset=['start_lat', 'start_lon', 'end_lat', 'end_lon'])
    
    print(f"✅ {len(df)} viagens com coordenadas válidas carregadas\n")
    
    return df

def main():
    parser = argparse.ArgumentParser(description='Aplica Differential Privacy a coordenadas GPS')
    parser.add_argument('--epsilon', type=float, default=1.0, 
                        help='Parâmetro de privacidade (default: 1.0)')
    parser.add_argument('--input', type=str, default='../dados_monetizacao_novas_emissões_etanol_original_gas_1720_v2.csv',
                        help='CSV de entrada com GPS')
    parser.add_argument('--output', type=str, default='dados_gps_dp.csv',
                        help='CSV de saída com DP aplicado')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando aplicação de Differential Privacy\n")
    
    # Carregar dados do CSV
    print(f"📂 Carregando dados de: {args.input}")
    df = load_csv_with_gps(args.input)
    
    # Aplicar DP
    df_dp = apply_dp_to_gps(df, epsilon=args.epsilon)
    
    # Salvar
    df_dp.to_csv(args.output, index=False)
    
    print(f"\n✅ Dados com DP salvos em: {args.output}")
    print(f"   Total de viagens: {len(df_dp)}")
    print(f"   Epsilon usado: {args.epsilon}")
    
    # Exemplo de comparação
    if len(df_dp) > 0:
        print(f"\n📍 Exemplo (primeira viagem):")
        row = df_dp.iloc[0]
        print(f"   Start original: ({row['start_lat_original']:.6f}, {row['start_lon_original']:.6f})")
        print(f"   Start com DP:   ({row['start_lat_dp']:.6f}, {row['start_lon_dp']:.6f})")
        print(f"   End original:   ({row['end_lat_original']:.6f}, {row['end_lon_original']:.6f})")
        print(f"   End com DP:     ({row['end_lat_dp']:.6f}, {row['end_lon_dp']:.6f})")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
