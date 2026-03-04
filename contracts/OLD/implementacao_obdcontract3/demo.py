#!/usr/bin/env python3
"""
Script de demonstração do sistema de score de qualidade

Testa os 4 cenários:
1. Trajeto ideal (movimento fluido, GPS 5s)
2. Trajeto esparso (GPS a cada 5 minutos)
3. Veículo estacionado (0% movimento)
4. Trajeto ruim (esparso + parado)

Autor: Victor
Data: 2026-03-03
"""

import sys
import os

# Adicionar diretório de scripts ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from process_with_quality import process_csv_with_quality


def run_demo():
    """Executa demonstração de todos os cenários"""
    
    print("\n" + "="*80)
    print(" "*20 + "🎯 DEMONSTRAÇÃO: SISTEMA DE SCORE DE QUALIDADE")
    print("="*80)
    
    scenarios = [
        {
            'name': 'TRAJETO IDEAL',
            'description': 'Movimento fluido, GPS a cada 5 segundos',
            'input': 'data/exemplo_ideal.csv',
            'output': 'data/resultado_ideal.csv',
            'expected_score': '95-100',
            'expected_multiplier': '0.96-1.0'
        },
        {
            'name': 'TRAJETO ESPARSO',
            'description': 'GPS a cada 5 minutos (300 segundos)',
            'input': 'data/exemplo_esparso.csv',
            'output': 'data/resultado_esparso.csv',
            'expected_score': '40-50',
            'expected_multiplier': '0.50-0.60'
        },
        {
            'name': 'VEÍCULO ESTACIONADO',
            'description': 'GPS ligado, veículo parado (0% movimento)',
            'input': 'data/exemplo_estacionado.csv',
            'output': 'data/resultado_estacionado.csv',
            'expected_score': '30-40',
            'expected_multiplier': '0.44-0.52'
        },
        {
            'name': 'TRAJETO RUIM',
            'description': 'Espaçamento irregular + muitos pontos parados',
            'input': 'data/exemplo_ruim.csv',
            'output': 'data/resultado_ruim.csv',
            'expected_score': '20-40',
            'expected_multiplier': '0.36-0.52'
        }
    ]
    
    results = []
    
    for idx, scenario in enumerate(scenarios, 1):
        print("\n" + "="*80)
        print(f"CENÁRIO {idx}/4: {scenario['name']}")
        print(f"Descrição: {scenario['description']}")
        print(f"Expectativa: Score {scenario['expected_score']}, Multiplicador {scenario['expected_multiplier']}")
        print("="*80)
        
        try:
            result = process_csv_with_quality(
                scenario['input'],
                scenario['output'],
                vehicle_id=f"DEMO_{idx}",
                co2_per_km=0.175
            )
            results.append({
                'scenario': scenario['name'],
                'score': result['quality_score'],
                'multiplier': result['quality_multiplier'],
                'grade': result['quality_grade'],
                'co2_raw': result['co2_raw_kg'],
                'co2_credits': result['co2_credits_kg'],
                'reduction': result['credit_reduction_percent']
            })
        except Exception as e:
            print(f"❌ Erro ao processar {scenario['name']}: {e}")
            import traceback
            traceback.print_exc()
    
    # Resumo comparativo
    print("\n" + "="*80)
    print(" "*25 + "📊 RESUMO COMPARATIVO")
    print("="*80)
    print(f"{'Cenário':<25} {'Score':>8} {'Nota':>6} {'Mult':>8} {'Redução':>10}")
    print("-"*80)
    
    for r in results:
        print(f"{r['scenario']:<25} {r['score']:>8.1f} {r['grade']:>6} {r['multiplier']:>8.3f} {r['reduction']:>9.1f}%")
    
    print("="*80)
    
    print("\n💡 INTERPRETAÇÃO:")
    print("   Score: 0-100 (quanto maior, melhor a qualidade)")
    print("   Nota: A (excelente), B (bom), C (aceitável), F (insuficiente)")
    print("   Mult: Multiplicador aplicado nos créditos (0.2 a 1.0)")
    print("   Redução: Percentual de crédito perdido por baixa qualidade")
    
    print("\n💰 EXEMPLO PRÁTICO:")
    print("   Se uma viagem emitiu 2.5 kg de CO2:")
    for r in results:
        credits = 2.5 * r['multiplier']
        loss = 2.5 - credits
        print(f"   • {r['scenario']:<25} → {credits:.3f} kg créditos (-{loss:.3f} kg)")
    
    print("\n✅ Demonstração concluída!")
    print("   Resultados salvos em data/resultado_*.csv")
    print("="*80 + "\n")


if __name__ == "__main__":
    run_demo()
