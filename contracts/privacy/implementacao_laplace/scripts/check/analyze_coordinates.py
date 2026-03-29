#!/usr/bin/env python3
"""Script para analisar variação de coordenadas no trajeto"""

import json
import sys
import numpy as np

if len(sys.argv) < 2:
    print("Uso: python3 analyze_coordinates.py <arquivo.json>")
    sys.exit(1)

json_file = sys.argv[1]

print(f"📂 Lendo: {json_file}")
with open(json_file, 'r') as f:
    data = json.load(f)

print(f"\n✅ Total de viagens: {len(data)}")

for i, traj in enumerate(data, 1):
    print("\n" + "="*70)
    print(f"🚗 Viagem {i}: {traj['vin']}")
    print("="*70)
    
    coords = traj['trajectory_original']
    
    # Contar pontos únicos
    unique_coords = []
    for coord in coords:
        coord_tuple = tuple(coord)
        if coord_tuple not in unique_coords:
            unique_coords.append(coord_tuple)
    
    print(f"\n📊 Estatísticas:")
    print(f"   Total de pontos: {len(coords)}")
    print(f"   Coordenadas únicas: {len(unique_coords)}")
    print(f"   Pontos duplicados: {len(coords) - len(unique_coords)}")
    
    # Calcular distâncias entre pontos consecutivos
    distances = []
    for j in range(len(coords) - 1):
        lat1, lon1 = coords[j]
        lat2, lon2 = coords[j+1]
        
        # Distância euclidiana aproximada em metros
        dlat = (lat2 - lat1) * 111320
        dlon = (lon2 - lon1) * 111320 * np.cos(np.radians(lat1))
        dist = np.sqrt(dlat**2 + dlon**2)
        distances.append(dist)
    
    print(f"\n📏 Distâncias entre pontos consecutivos (metros):")
    print(f"   Mínima: {min(distances):.2f} m")
    print(f"   Máxima: {max(distances):.2f} m")
    print(f"   Média: {np.mean(distances):.2f} m")
    print(f"   Mediana: {np.median(distances):.2f} m")
    
    # Contar pontos parados (distância < 1m)
    stopped_points = sum(1 for d in distances if d < 1.0)
    print(f"\n⏸️  Pontos com movimento < 1m: {stopped_points}/{len(distances)} ({stopped_points/len(distances)*100:.1f}%)")
    
    # Mostrar segmentos com movimento significativo
    print(f"\n🏃 Segmentos com movimento > 10m:")
    movement_count = 0
    for j, dist in enumerate(distances):
        if dist > 10:
            movement_count += 1
            if movement_count <= 5:  # Mostrar apenas primeiros 5
                lat1, lon1 = coords[j]
                lat2, lon2 = coords[j+1]
                print(f"   {j}→{j+1}: {dist:.1f}m | ({lat1:.6f},{lon1:.6f}) → ({lat2:.6f},{lon2:.6f})")
    
    if movement_count > 5:
        print(f"   ... e mais {movement_count - 5} segmentos")
    
    print(f"\n   Total de segmentos com movimento: {movement_count}")
    
    # Bounding box
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    
    lat_range = max(lats) - min(lats)
    lon_range = max(lons) - min(lons)
    
    print(f"\n🗺️  Área coberta:")
    print(f"   Latitude: {min(lats):.6f} a {max(lats):.6f} (range: {lat_range:.6f}°)")
    print(f"   Longitude: {min(lons):.6f} a {max(lons):.6f} (range: {lon_range:.6f}°)")
    print(f"   Área aproximada: {lat_range * 111:.1f} km × {lon_range * 111:.1f} km")

print("\n" + "="*70)
print("\n💡 ANÁLISE:")
print("   - Se a maioria dos pontos está parada (< 1m), o veículo ficou muito tempo parado")
print("   - Se a área é muito pequena, o trajeto é curto ou concentrado")
print("   - Se há poucos pontos únicos, muitos segmentos repetem coordenadas")
