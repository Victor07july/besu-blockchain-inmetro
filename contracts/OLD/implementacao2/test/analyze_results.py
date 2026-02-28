#!/usr/bin/env python3
"""
Analisa resultados da Implementação 2 e mostra estatísticas de privacidade
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime

RESULTS_FILE = "e1_gps_send_results.json"

def parse_gps_string(gps_str):
    """Parse string GPS: '(-5.843199, -35.197724)' -> (lat, lon)"""
    try:
        gps_str = gps_str.strip('()')
        parts = gps_str.split(',')
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        return lat, lon
    except:
        return None, None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula distância entre dois pontos GPS usando Haversine (em km)"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Raio da Terra em km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c

def analyze_privacy():
    """Analisa estatísticas de privacidade dos resultados"""
    print("🔍 Analisando Privacidade da Implementação 2\n")
    print("="*60)
    
    # Carregar resultados
    try:
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
    except FileNotFoundError:
        print(f"❌ Arquivo {RESULTS_FILE} não encontrado!")
        print("   Execute primeiro: python3 send_e1_gps_data.py")
        return
    
    success = results.get('success', [])
    
    if not success:
        print("❌ Nenhum resultado encontrado!")
        return
    
    print(f"📊 Total de viagens: {len(success)}")
    print(f"🔐 Privacidade: {results.get('gps_privacy', 'Unknown')}")
    print(f"📐 Epsilon usado: {results.get('epsilon_used', 'inline')}\n")
    
    # Calcular erros de localização
    errors_start = []
    errors_end = []
    
    for trip in success:
        # Parse coordenadas
        start_orig = parse_gps_string(trip['gps_start_original'])
        start_dp = parse_gps_string(trip['gps_start_dp'])
        end_orig = parse_gps_string(trip['gps_end_original'])
        end_dp = parse_gps_string(trip['gps_end_dp'])
        
        if all([start_orig[0], start_dp[0], end_orig[0], end_dp[0]]):
            # Calcular erro em metros
            error_start = haversine_distance(
                start_orig[0], start_orig[1],
                start_dp[0], start_dp[1]
            ) * 1000  # km -> m
            
            error_end = haversine_distance(
                end_orig[0], end_orig[1],
                end_dp[0], end_dp[1]
            ) * 1000
            
            errors_start.append(error_start)
            errors_end.append(error_end)
    
    errors_all = errors_start + errors_end
    
    # Estatísticas
    print("📏 ESTATÍSTICAS DE ERRO (Distância entre Original e DP)")
    print("="*60)
    print(f"Erro médio:      {np.mean(errors_all):.1f} metros")
    print(f"Erro mediano:    {np.median(errors_all):.1f} metros")
    print(f"Erro mínimo:     {np.min(errors_all):.1f} metros")
    print(f"Erro máximo:     {np.max(errors_all):.1f} metros")
    print(f"Desvio padrão:   {np.std(errors_all):.1f} metros")
    
    # Distribuição
    bins = [0, 50, 100, 200, 500, 1000, float('inf')]
    labels = ['0-50m', '50-100m', '100-200m', '200-500m', '500m-1km', '>1km']
    
    print(f"\n📊 DISTRIBUIÇÃO DE ERROS")
    print("="*60)
    
    for i in range(len(labels)):
        count = sum(1 for e in errors_all if bins[i] <= e < bins[i+1])
        pct = (count / len(errors_all)) * 100
        bar = '█' * int(pct / 2)
        print(f"{labels[i]:>10}: {count:3d} ({pct:5.1f}%) {bar}")
    
    # Valores E1
    valores_e1 = [t['valorE1_calculated'] for t in success]
    
    print(f"\n💰 ESTATÍSTICAS DE MONETIZAÇÃO (E1)")
    print("="*60)
    print(f"Total monetizado:  R$ {sum(valores_e1):.2f}")
    print(f"Média por viagem:  R$ {np.mean(valores_e1):.4f}")
    print(f"Mediana:           R$ {np.median(valores_e1):.4f}")
    print(f"Máximo:            R$ {max(valores_e1):.4f}")
    print(f"Mínimo:            R$ {min(valores_e1):.4f}")
    
    # Distâncias GPS
    gps_distances = [t['gpsDistance_calculated'] for t in success]
    
    print(f"\n📍 DISTÂNCIAS GPS (Calculadas pelo Contrato)")
    print("="*60)
    print(f"Distância média:   {np.mean(gps_distances):.2f} km")
    print(f"Distância total:   {sum(gps_distances):.2f} km")
    print(f"Maior distância:   {max(gps_distances):.2f} km")
    print(f"Menor distância:   {min(gps_distances):.2f} km")
    
    # Análise de privacidade
    print(f"\n🔐 ANÁLISE DE PRIVACIDADE")
    print("="*60)
    
    if np.mean(errors_all) < 100:
        privacy_level = "BAIXA (epsilon alto ou DP não aplicado)"
        recommendation = "Considere epsilon < 1.0 para mais privacidade"
    elif np.mean(errors_all) < 300:
        privacy_level = "MODERADA (epsilon ~ 1.0)"
        recommendation = "Bom balanceamento privacidade × utilidade"
    else:
        privacy_level = "ALTA (epsilon baixo)"
        recommendation = "Máxima privacidade, verifique utilidade dos dados"
    
    print(f"Nível de privacidade:  {privacy_level}")
    print(f"Recomendação:          {recommendation}")
    
    # Pseudônimos
    pseudonimos = results.get('pseudonimos', {})
    total_pseudonimos = sum(len(trips) for trips in pseudonimos.values())
    
    print(f"\n👤 PSEUDÔNIMOS HD")
    print("="*60)
    print(f"Total de pseudônimos:   {total_pseudonimos}")
    print(f"VINs únicos:            {len(pseudonimos)}")
    print(f"Média viagens por VIN:  {total_pseudonimos / len(pseudonimos) if pseudonimos else 0:.1f}")
    
    # Mostrar alguns exemplos
    print(f"\n📝 EXEMPLOS (primeiras 3 viagens)")
    print("="*60)
    
    for i, trip in enumerate(success[:3]):
        print(f"\nViagem {i+1}:")
        print(f"  VIN: {trip['vin'][:15]}...")
        print(f"  Pseudônimo: {trip['pseudonimo'][:10]}...{trip['pseudonimo'][-8:]}")
        print(f"  GPS Start Original: {trip['gps_start_original']}")
        print(f"  GPS Start com DP:   {trip['gps_start_dp']}")
        
        start_orig = parse_gps_string(trip['gps_start_original'])
        start_dp = parse_gps_string(trip['gps_start_dp'])
        
        if start_orig[0] and start_dp[0]:
            error = haversine_distance(
                start_orig[0], start_orig[1],
                start_dp[0], start_dp[1]
            ) * 1000
            print(f"  Erro Start: {error:.1f} metros")
        
        print(f"  Valor E1: R$ {trip['valorE1_calculated']:.4f}")
        print(f"  Distância GPS: {trip['gpsDistance_calculated']:.2f} km")
    
    print(f"\n\n✅ Análise concluída!")
    print(f"📁 Dados completos em: {RESULTS_FILE}")

def compare_implementations():
    """Compara Implementação 1 vs 2 (se ambos existirem)"""
    print("\n" + "="*60)
    print("📊 COMPARAÇÃO: Implementação 1 vs 2")
    print("="*60)
    
    impl1_file = "../implementacao1/e1_send_results.json"
    impl2_file = RESULTS_FILE
    
    try:
        with open(impl1_file, 'r') as f:
            impl1 = json.load(f)
    except:
        print("⚠️  Implementação 1 não encontrada, pulando comparação")
        return
    
    try:
        with open(impl2_file, 'r') as f:
            impl2 = json.load(f)
    except:
        print("⚠️  Implementação 2 não encontrada")
        return
    
    print(f"\n| Métrica | Impl 1 | Impl 2 |")
    print(f"|---------|--------|--------|")
    print(f"| Viagens | {len(impl1.get('success', []))} | {len(impl2.get('success', []))} |")
    print(f"| GPS | Não | Sim (DP) |")
    print(f"| Pseudônimos | Sim | Sim |")
    print(f"| Features | E1 básico | E1 + GPS + DP |")

if __name__ == "__main__":
    try:
        analyze_privacy()
        compare_implementations()
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
