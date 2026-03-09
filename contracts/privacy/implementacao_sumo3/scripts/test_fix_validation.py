#!/usr/bin/env python3
"""
Script de validação do fix de map matching
Requer: pandas, numpy
"""

import json
import pandas as pd
import sys
from pathlib import Path

def main():
    # Caminhos dos arquivos
    base_dir = Path(__file__).parent.parent
    csv_file = base_dir / "data" / "trips_distance_analysis.csv"
    json_file = base_dir / "data" / "trips_trajectories.json"
    
    print("=" * 80)
    print("VALIDAÇÃO DO FIX DE MAP MATCHING")
    print("=" * 80)
    
    # 1. Verificar CSV
    print("\n1. Análise do CSV (trips_distance_analysis.csv)")
    print("-" * 80)
    
    if not csv_file.exists():
        print(f"❌ Arquivo não encontrado: {csv_file}")
        print("   Execute primeiro: python3 scripts/process_sumo_csv.py data/vehicles_step.csv")
        sys.exit(1)
    
    df = pd.read_csv(csv_file)
    print(f"Total de veículos: {len(df)}")
    
    # Verificar distâncias zero
    zero_distances = df[df['Distancia_Trajeto_com_Offset_km'] == 0.0]
    if len(zero_distances) > 0:
        print(f"\n❌ PROBLEMA: {len(zero_distances)} veículos com distância zero:")
        for _, row in zero_distances.iterrows():
            print(f"   - {row['VIN']}: {row['Distancia_Trajeto_com_Offset_km']:.4f} km")
        print("\n   Isso indica que o fix não funcionou completamente.")
    else:
        print(f"✅ Todos os veículos têm distância > 0.0 km")
    
    # Verificar coordenadas idênticas
    print("\n2. Verificação de coordenadas idênticas")
    print("-" * 80)
    
    df['coords_start'] = df['Start_Lat_com_Offset'].round(6).astype(str) + "," + df['Start_Lon_com_Offset'].round(6).astype(str)
    df['coords_end'] = df['End_Lat_com_Offset'].round(6).astype(str) + "," + df['End_Lon_com_Offset'].round(6).astype(str)
    
    # Verificar se algum veículo tem start == end
    same_coords = df[df['Start_Lat_com_Offset'] == df['End_Lat_com_Offset']]
    same_coords = same_coords[same_coords['Start_Lon_com_Offset'] == same_coords['End_Lon_com_Offset']]
    
    if len(same_coords) > 0:
        print(f"⚠️  {len(same_coords)} veículos com coordenadas start == end:")
        for _, row in same_coords.iterrows():
            print(f"   - {row['VIN']}: ({row['Start_Lat_com_Offset']:.6f}, {row['Start_Lon_com_Offset']:.6f})")
    else:
        print(f"✅ Todos os veículos têm coordenadas start ≠ end")
    
    # 3. Verificar JSON
    print("\n3. Análise do JSON (trips_trajectories.json)")
    print("-" * 80)
    
    if not json_file.exists():
        print(f"⚠️  Arquivo não encontrado: {json_file}")
        print("   Não foi possível verificar trajetórias completas")
    else:
        with open(json_file, 'r') as f:
            trips = json.load(f)
        
        print(f"Total de veículos no JSON: {len(trips)}")
        
        collapsed_trips = []
        for trip in trips:
            vin = trip['vin']
            traj_priv = trip['trajectory_private']
            
            # Contar pontos únicos
            unique_points = set()
            for point in traj_priv:
                unique_points.add((round(point[0], 8), round(point[1], 8)))
            
            num_unique = len(unique_points)
            num_total = len(traj_priv)
            
            if num_unique == 1 and num_total > 1:
                collapsed_trips.append({
                    'vin': vin,
                    'total_points': num_total,
                    'unique_points': num_unique,
                    'point': list(unique_points)[0]
                })
        
        if len(collapsed_trips) > 0:
            print(f"\n❌ PROBLEMA: {len(collapsed_trips)} veículos com trajetória colapsada:")
            for trip_info in collapsed_trips:
                print(f"   - {trip_info['vin']}: {trip_info['total_points']} pontos → {trip_info['unique_points']} único")
                print(f"     Ponto colapsado: {trip_info['point']}")
            print("\n   Isso indica que o fix não funcionou completamente.")
        else:
            print(f"✅ Nenhuma trajetória colapsada detectada")
            print(f"   Todos os veículos têm múltiplos pontos únicos")
    
    # 4. Estatísticas gerais
    print("\n4. Estatísticas Gerais")
    print("-" * 80)
    
    print(f"\nDistância Trajeto com Offset (km):")
    print(f"  Mínimo:  {df['Distancia_Trajeto_com_Offset_km'].min():.4f}")
    print(f"  Máximo:  {df['Distancia_Trajeto_com_Offset_km'].max():.4f}")
    print(f"  Média:   {df['Distancia_Trajeto_com_Offset_km'].mean():.4f}")
    print(f"  Mediana: {df['Distancia_Trajeto_com_Offset_km'].median():.4f}")
    
    # Comparação com SUMO
    df['diff_sumo'] = (df['Distancia_Trajeto_com_Offset_km'] - df['Distancia_SUMO_km']).abs()
    print(f"\nDiferença absoluta vs SUMO (km):")
    print(f"  Mínimo:  {df['diff_sumo'].min():.4f}")
    print(f"  Máximo:  {df['diff_sumo'].max():.4f}")
    print(f"  Média:   {df['diff_sumo'].mean():.4f}")
    
    # 5. Conclusão
    print("\n" + "=" * 80)
    print("RESULTADO DA VALIDAÇÃO")
    print("=" * 80)
    
    all_ok = True
    
    if len(zero_distances) > 0:
        print("❌ Ainda há veículos com distância zero")
        all_ok = False
    
    if len(collapsed_trips) > 0:
        print("❌ Ainda há trajetórias colapsadas")
        all_ok = False
    
    if all_ok:
        print("✅ FIX FUNCIONOU! Todos os testes passaram.")
        print("\nPróximos passos:")
        print("  1. Revisar visualmente os mapas HTML")
        print("  2. Validar algumas distâncias com Google Maps")
        print("  3. Verificar se os offsets estão dentro do raio máximo")
    else:
        print("\n⚠️  FIX NÃO RESOLVEU COMPLETAMENTE O PROBLEMA")
        print("\nSugestões:")
        print("  1. Verificar se as mudanças foram salvas corretamente")
        print("  2. Revisar as linhas ~470, ~478, ~527 em process_sumo_csv.py")
        print("  3. Confirmar que está usando get_road_network(lat_offset, lon_offset)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
