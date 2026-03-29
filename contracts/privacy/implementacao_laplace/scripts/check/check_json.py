#!/usr/bin/env python3
"""Script para verificar conteúdo do JSON de trajetos"""

import json
import sys

if len(sys.argv) < 2:
    print("Uso: python3 check_json.py <arquivo.json>")
    sys.exit(1)

json_file = sys.argv[1]

print(f"📂 Lendo: {json_file}")
with open(json_file, 'r') as f:
    data = json.load(f)

print(f"\n✅ Total de viagens: {len(data)}")
print("\n" + "="*70)

for i, traj in enumerate(data, 1):
    print(f"\n🚗 Viagem {i}:")
    print(f"   VIN: {traj['vin']}")
    print(f"   Modelo: {traj['model']}")
    print(f"   Pontos no trajeto original: {len(traj['trajectory_original'])}")
    print(f"   Pontos no trajeto privado: {len(traj['trajectory_private'])}")
    print(f"   num_points registrado: {traj['num_points']}")
    
    # Mostrar primeiros 3 pontos
    print(f"   \n   Primeiros pontos (original):")
    for j, point in enumerate(traj['trajectory_original'][:3]):
        print(f"      {j}: {point}")
    
    if len(traj['trajectory_original']) > 3:
        print(f"   ...")
        print(f"   Último ponto: {traj['trajectory_original'][-1]}")

print("\n" + "="*70)
print("\n💡 Se você vir apenas 2 pontos por viagem, o JSON está errado!")
print("   Execute novamente: python3 process_sumo_csv.py <input> <output> <consumo>")
