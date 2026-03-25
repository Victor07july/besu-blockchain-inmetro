#!/usr/bin/env python3
"""Script para debugar coordenadas privadas"""

import json
import sys
import numpy as np

if len(sys.argv) < 2:
    print("Uso: python3 debug_private_coords.py <arquivo.json>")
    sys.exit(1)

json_file = sys.argv[1]

print(f"📂 Lendo: {json_file}")
with open(json_file, 'r') as f:
    data = json.load(f)

for i, traj in enumerate(data, 1):
    print("\n" + "="*70)
    print(f"🚗 Viagem {i}: {traj['vin']}")
    print("="*70)
    
    coords_orig = traj['trajectory_original']
    coords_priv = traj['trajectory_private']
    
    # Coordenadas únicas privadas
    unique_priv = []
    for coord in coords_priv:
        coord_tuple = tuple(coord)
        if coord_tuple not in unique_priv:
            unique_priv.append(coord_tuple)
    
    print(f"\n📊 Coordenadas originais:")
    print(f"   Total: {len(coords_orig)}")
    print(f"   Primeiros 5 pontos:")
    for j in range(min(5, len(coords_orig))):
        print(f"      {j}: {coords_orig[j]}")
    
    print(f"\n🔒 Coordenadas privadas:")
    print(f"   Total: {len(coords_priv)}")
    print(f"   Únicas: {len(unique_priv)}")
    print(f"   Primeiros 5 pontos:")
    for j in range(min(5, len(coords_priv))):
        print(f"      {j}: {coords_priv[j]}")
    
    # Verificar se todos os pontos privados são iguais
    if len(unique_priv) == 1:
        print("\n❌ PROBLEMA: Todas as coordenadas privadas são IGUAIS!")
        print(f"   Todos os pontos estão em: {unique_priv[0]}")
    elif len(unique_priv) < 10:
        print(f"\n⚠️  ATENÇÃO: Apenas {len(unique_priv)} coordenadas únicas!")
        print(f"   Coordenadas únicas:")
        for coord in unique_priv:
            print(f"      {coord}")
    else:
        print(f"\n✅ OK: {len(unique_priv)} coordenadas privadas únicas")
    
    # Calcular variação nas coordenadas privadas
    lats_priv = [c[0] for c in coords_priv]
    lons_priv = [c[1] for c in coords_priv]
    
    lat_range = max(lats_priv) - min(lats_priv)
    lon_range = max(lons_priv) - min(lons_priv)
    
    print(f"\n📏 Variação nas coordenadas privadas:")
    print(f"   Latitude:  min={min(lats_priv):.6f}, max={max(lats_priv):.6f}, range={lat_range:.6f}°")
    print(f"   Longitude: min={min(lons_priv):.6f}, max={max(lons_priv):.6f}, range={lon_range:.6f}°")
    
    if lat_range < 0.0001 and lon_range < 0.0001:
        print(f"\n❌ PROBLEMA: Variação muito pequena! Trajeto privado parece uma linha reta ou ponto.")
    
    # Calcular deslocamentos
    print(f"\n📊 Comparação Original vs Privado:")
    displacements = []
    for j in range(min(5, len(coords_orig))):
        lat_o, lon_o = coords_orig[j]
        lat_p, lon_p = coords_priv[j]
        
        dlat = (lat_p - lat_o) * 111320
        dlon = (lon_p - lon_o) * 111320 * np.cos(np.radians(lat_o))
        dist = np.sqrt(dlat**2 + dlon**2)
        displacements.append(dist)
        
        print(f"   Ponto {j}: Original=({lat_o:.6f},{lon_o:.6f}) → Privado=({lat_p:.6f},{lon_p:.6f}) | Desl={dist:.1f}m")
