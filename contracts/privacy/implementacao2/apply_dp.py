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

def generate_sample_gps_data(num_trips=33):
    """
    Gera dados GPS simulados para Natal/RN
    (substitua por dados reais quando disponíveis)
    """
    print("⚠️  Gerando dados GPS simulados (Natal/RN)")
    print("   Substitua por dados reais quando disponíveis\n")
    
    # Natal/RN aproximado: -5.7945°, -35.2110°
    base_lat = -5.7945
    base_lon = -35.2110
    
    # Gerar coordenadas aleatórias em um raio de ~10km
    np.random.seed(42)  # Para reprodutibilidade
    
    start_lats = base_lat + np.random.uniform(-0.1, 0.1, num_trips)
    start_lons = base_lon + np.random.uniform(-0.1, 0.1, num_trips)
    end_lats = base_lat + np.random.uniform(-0.1, 0.1, num_trips)
    end_lons = base_lon + np.random.uniform(-0.1, 0.1, num_trips)
    
    return pd.DataFrame({
        'trip_id': range(num_trips),
        'start_lat': start_lats,
        'start_lon': start_lons,
        'end_lat': end_lats,
        'end_lon': end_lons
    })

def main():
    parser = argparse.ArgumentParser(description='Aplica Differential Privacy a coordenadas GPS')
    parser.add_argument('--epsilon', type=float, default=1.0, 
                        help='Parâmetro de privacidade (default: 1.0)')
    parser.add_argument('--input', type=str, default=None,
                        help='CSV de entrada com GPS')
    parser.add_argument('--output', type=str, default='dados_gps_dp.csv',
                        help='CSV de saída com DP aplicado')
    parser.add_argument('--generate-sample', action='store_true',
                        help='Gerar dados GPS simulados')
    
    args = parser.parse_args()
    
    print("🚀 Iniciando aplicação de Differential Privacy\n")
    
    # Carregar ou gerar dados
    if args.generate_sample or args.input is None:
        df = generate_sample_gps_data()
    else:
        print(f"📂 Carregando dados de: {args.input}")
        df = pd.read_csv(args.input)
    
    # Verificar colunas necessárias
    required_cols = ['start_lat', 'start_lon', 'end_lat', 'end_lon']
    missing = [col for col in required_cols if col not in df.columns]
    
    if missing:
        print(f"❌ Erro: Colunas faltando no CSV: {missing}")
        print(f"   Colunas encontradas: {list(df.columns)}")
        return
    
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
