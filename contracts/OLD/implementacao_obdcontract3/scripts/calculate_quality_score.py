#!/usr/bin/env python3
"""
Módulo para calcular score de qualidade de trajetos baseado em:
1. Redundância espacial (pontos parados/repetitivos)
2. Esparsidade temporal (intervalos entre leituras)

Retorna multiplicador de 0.2 a 1.0 que afeta créditos de CO2

Autor: Victor
Data: 2026-03-03
"""

import math
from typing import List, Dict, Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância entre dois pontos GPS usando fórmula de Haversine
    
    Args:
        lat1, lon1: Coordenadas do ponto 1
        lat2, lon2: Coordenadas do ponto 2
        
    Returns:
        Distância em metros
    """
    R = 6371000  # Raio da Terra em metros
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def calculate_redundancy_penalty(trajectory_points: List[Dict]) -> Tuple[float, Dict]:
    """
    Calcula penalidade por redundância espacial (pontos parados/repetitivos)
    
    Args:
        trajectory_points: Lista de dicts com 'lat', 'lon'
        
    Returns:
        (penalty, details) onde penalty é negativo (-60 a 0)
    """
    if len(trajectory_points) < 2:
        return 0, {'stationary_count': 0, 'total_movements': 0, 'redundancy_ratio': 0}
    
    stationary_count = 0
    total_movements = len(trajectory_points) - 1
    MOVEMENT_THRESHOLD = 5  # metros
    
    for i in range(1, len(trajectory_points)):
        dist = haversine_distance(
            trajectory_points[i-1]['lat'],
            trajectory_points[i-1]['lon'],
            trajectory_points[i]['lat'],
            trajectory_points[i]['lon']
        )
        
        if dist < MOVEMENT_THRESHOLD:
            stationary_count += 1
    
    redundancy_ratio = stationary_count / total_movements
    
    # Aplicar penalidade baseada na proporção de pontos parados
    if redundancy_ratio > 0.8:      # >80% parado (estacionado)
        penalty = -60
    elif redundancy_ratio > 0.6:    # 60-80% parado (congestionamento severo)
        penalty = -40
    elif redundancy_ratio > 0.4:    # 40-60% parado (congestionamento)
        penalty = -20
    elif redundancy_ratio > 0.2:    # 20-40% parado (tráfego com paradas)
        penalty = -10
    else:                           # <20% parado (movimento normal)
        penalty = 0
    
    details = {
        'stationary_count': stationary_count,
        'moving_count': total_movements - stationary_count,
        'total_movements': total_movements,
        'redundancy_ratio': redundancy_ratio,
        'penalty': penalty
    }
    
    return penalty, details


def calculate_sparsity_penalty(trajectory_points: List[Dict]) -> Tuple[float, Dict]:
    """
    Calcula penalidade por esparsidade temporal (dados espaçados no tempo)
    
    Args:
        trajectory_points: Lista de dicts com 'timestamp' (float, em segundos)
        
    Returns:
        (penalty, details) onde penalty é negativo (-70 a 0)
    """
    if len(trajectory_points) < 2:
        return 0, {'avg_interval': 0, 'max_gap': 0, 'total_penalty': 0}
    
    # Calcular intervalos entre pontos consecutivos
    intervals = []
    for i in range(1, len(trajectory_points)):
        interval = trajectory_points[i]['timestamp'] - trajectory_points[i-1]['timestamp']
        intervals.append(interval)
    
    avg_interval = sum(intervals) / len(intervals)
    max_gap = max(intervals)
    
    # Penalidade por intervalo médio
    if avg_interval > 300:          # >5 minutos médio
        penalty_avg = -50
    elif avg_interval > 120:        # 2-5 minutos médio
        penalty_avg = -30
    elif avg_interval > 60:         # 1-2 minutos médio
        penalty_avg = -15
    elif avg_interval > 30:         # 30-60 segundos médio
        penalty_avg = -5
    else:                           # <30 segundos (ideal)
        penalty_avg = 0
    
    # Penalidade adicional por gaps críticos (buracos grandes)
    if max_gap > 600:               # Gap >10 minutos
        penalty_gap = -20
    elif max_gap > 300:             # Gap >5 minutos
        penalty_gap = -10
    else:
        penalty_gap = 0
    
    total_penalty = penalty_avg + penalty_gap
    
    details = {
        'avg_interval': avg_interval,
        'max_gap': max_gap,
        'min_interval': min(intervals),
        'num_intervals': len(intervals),
        'penalty_avg': penalty_avg,
        'penalty_gap': penalty_gap,
        'total_penalty': total_penalty
    }
    
    return total_penalty, details


def calculate_quality_score(trajectory_points: List[Dict]) -> Dict:
    """
    Calcula score de qualidade completo do trajeto
    
    Args:
        trajectory_points: Lista de dicts com:
            - 'lat': latitude (float)
            - 'lon': longitude (float)
            - 'timestamp': timestamp em segundos (float)
    
    Returns:
        Dict com:
            - 'score': score final (0-100)
            - 'multiplier': multiplicador de crédito (0.2-1.0)
            - 'grade': nota (A, B, C, F)
            - 'redundancy': detalhes de redundância
            - 'sparsity': detalhes de esparsidade
    """
    if len(trajectory_points) < 2:
        return {
            'score': 0,
            'multiplier': 0.2,
            'grade': 'F',
            'redundancy': {},
            'sparsity': {},
            'warning': 'Trajeto muito curto (<2 pontos)'
        }
    
    # Calcular penalidades
    redundancy_penalty, redundancy_details = calculate_redundancy_penalty(trajectory_points)
    sparsity_penalty, sparsity_details = calculate_sparsity_penalty(trajectory_points)
    
    # Score final: 100 pontos - penalidades
    score = 100 + redundancy_penalty + sparsity_penalty
    score = max(0, min(100, score))  # Limitar entre 0 e 100
    
    # Converter score em multiplicador (0.2 a 1.0)
    # Formula: multiplier = 0.2 + (score/100) * 0.8
    # Garante mínimo de 20% mesmo com score 0
    multiplier = 0.2 + (score / 100) * 0.8
    
    # Classificar qualidade
    if score >= 80:
        grade = 'A'
        quality_label = 'Excelente'
    elif score >= 60:
        grade = 'B'
        quality_label = 'Bom'
    elif score >= 40:
        grade = 'C'
        quality_label = 'Aceitável'
    else:
        grade = 'F'
        quality_label = 'Insuficiente'
    
    return {
        'score': score,
        'multiplier': multiplier,
        'grade': grade,
        'quality_label': quality_label,
        'redundancy': redundancy_details,
        'sparsity': sparsity_details,
        'num_points': len(trajectory_points)
    }


def format_quality_report(quality_result: Dict) -> str:
    """
    Formata relatório de qualidade em formato legível
    
    Args:
        quality_result: Resultado de calculate_quality_score()
        
    Returns:
        String formatada com relatório
    """
    lines = []
    lines.append("="*60)
    lines.append("📊 RELATÓRIO DE QUALIDADE DOS DADOS")
    lines.append("="*60)
    
    # Score geral
    lines.append(f"\n🎯 SCORE GERAL: {quality_result['score']:.1f}/100 - Nota {quality_result['grade']}")
    lines.append(f"   Qualidade: {quality_result['quality_label']}")
    lines.append(f"   Multiplicador de crédito: {quality_result['multiplier']:.3f} ({quality_result['multiplier']*100:.1f}%)")
    lines.append(f"   Pontos no trajeto: {quality_result['num_points']}")
    
    # Redundância
    if 'redundancy' in quality_result and quality_result['redundancy']:
        red = quality_result['redundancy']
        lines.append(f"\n📍 REDUNDÂNCIA ESPACIAL (Movimento):")
        lines.append(f"   Pontos parados (<5m): {red['stationary_count']}")
        lines.append(f"   Pontos em movimento: {red['moving_count']}")
        lines.append(f"   Proporção parada: {red['redundancy_ratio']*100:.1f}%")
        lines.append(f"   Penalidade: {red['penalty']} pontos")
        
        if red['redundancy_ratio'] > 0.8:
            lines.append(f"   ⚠️  Veículo estacionado ou quase parado")
        elif red['redundancy_ratio'] > 0.4:
            lines.append(f"   ⚠️  Muito congestionamento ou paradas")
        elif red['redundancy_ratio'] > 0.2:
            lines.append(f"   ℹ️  Tráfego com paradas normais")
        else:
            lines.append(f"   ✅ Movimento fluido")
    
    # Esparsidade
    if 'sparsity' in quality_result and quality_result['sparsity']:
        spa = quality_result['sparsity']
        lines.append(f"\n⏱️  ESPARSIDADE TEMPORAL (Frequência):")
        lines.append(f"   Intervalo médio: {spa['avg_interval']:.1f} segundos")
        lines.append(f"   Maior gap: {spa['max_gap']:.1f} segundos")
        lines.append(f"   Menor intervalo: {spa['min_interval']:.1f} segundos")
        lines.append(f"   Penalidade: {spa['total_penalty']} pontos")
        
        if spa['avg_interval'] > 300:
            lines.append(f"   ⚠️  Dados muito espaçados (>{spa['avg_interval']/60:.1f} min)")
        elif spa['avg_interval'] > 60:
            lines.append(f"   ⚠️  Frequência baixa (~{spa['avg_interval']:.0f}s entre leituras)")
        elif spa['avg_interval'] > 30:
            lines.append(f"   ℹ️  Frequência moderada (~{spa['avg_interval']:.0f}s)")
        else:
            lines.append(f"   ✅ Frequência alta ({spa['avg_interval']:.1f}s)")
    
    # Interpretação final
    lines.append(f"\n💰 IMPACTO NOS CRÉDITOS:")
    lines.append(f"   Exemplo: Se CO2 = 2.5 kg")
    lines.append(f"   Créditos finais = 2.5 × {quality_result['multiplier']:.3f} = {2.5 * quality_result['multiplier']:.3f} kg")
    lines.append(f"   Redução: {(1 - quality_result['multiplier'])*100:.1f}%")
    
    lines.append("="*60)
    
    return "\n".join(lines)


# Exemplo de uso
if __name__ == "__main__":
    # Exemplo 1: Trajeto ideal (movimento fluido, frequência alta)
    print("EXEMPLO 1: Trajeto Ideal")
    trajectory_ideal = [
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 0},
        {'lat': -22.9069, 'lon': -43.1730, 'timestamp': 5},
        {'lat': -22.9070, 'lon': -43.1731, 'timestamp': 10},
        {'lat': -22.9071, 'lon': -43.1732, 'timestamp': 15},
        {'lat': -22.9072, 'lon': -43.1733, 'timestamp': 20},
    ]
    result = calculate_quality_score(trajectory_ideal)
    print(format_quality_report(result))
    
    # Exemplo 2: Trajeto com esparsidade (dados a cada 5 minutos)
    print("\n" + "="*60)
    print("EXEMPLO 2: Trajeto Esparso (GPS a cada 5min)")
    trajectory_sparse = [
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 0},
        {'lat': -22.9069, 'lon': -43.1730, 'timestamp': 300},
        {'lat': -22.9070, 'lon': -43.1731, 'timestamp': 600},
        {'lat': -22.9071, 'lon': -43.1732, 'timestamp': 900},
    ]
    result = calculate_quality_score(trajectory_sparse)
    print(format_quality_report(result))
    
    # Exemplo 3: Trajeto redundante (veículo parado)
    print("\n" + "="*60)
    print("EXEMPLO 3: Veículo Estacionado")
    trajectory_stationary = [
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 0},
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 5},
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 10},
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 15},
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 20},
    ]
    result = calculate_quality_score(trajectory_stationary)
    print(format_quality_report(result))
    
    # Exemplo 4: Trajeto misto (esparsidade + redundância)
    print("\n" + "="*60)
    print("EXEMPLO 4: Trajeto Problemático (Esparso + Parado)")
    trajectory_poor = [
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 0},
        {'lat': -22.9068, 'lon': -43.1729, 'timestamp': 180},  # 3min, parado
        {'lat': -22.9068, 'lon': -43.1730, 'timestamp': 360},  # 3min, pequeno movimento
        {'lat': -22.9068, 'lon': -43.1730, 'timestamp': 720},  # 6min gap, parado
    ]
    result = calculate_quality_score(trajectory_poor)
    print(format_quality_report(result))
