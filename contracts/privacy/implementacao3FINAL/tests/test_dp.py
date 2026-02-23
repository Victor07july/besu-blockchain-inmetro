#!/usr/bin/env python3
"""
Script de teste rápido do pipeline de privacidade diferencial
Testa com uma única viagem para validar funcionamento

Autor: Victor
Data: 2026-02-09
"""

from differential_privacy_gps import DifferentialPrivacyGPS
import warnings
warnings.filterwarnings('ignore')


def test_single_trip():
    """Testa processamento de uma única viagem"""
    
    print("="*70)
    print("🧪 TESTE RÁPIDO - PRIVACIDADE DIFERENCIAL GPS")
    print("="*70)
    
    # Coordenadas de exemplo (Natal/RN)
    start_coord = "-5.8431992, -35.1977242"
    end_coord = "-5.8431281, -35.1975708"
    
    print(f"\n📍 Coordenadas de teste:")
    print(f"   Início: {start_coord}")
    print(f"   Fim: {end_coord}")
    
    # Testar diferentes valores de epsilon
    epsilons = [0.3, 0.5, 1.0]
    
    for epsilon in epsilons:
        print(f"\n{'='*70}")
        print(f"🔐 Testando com ε = {epsilon}")
        print("="*70)
        
        try:
            # Inicializar processador
            dp = DifferentialPrivacyGPS(epsilon=epsilon, search_radius=1000)
            
            # Processar viagem
            result = dp.process_trip(start_coord, end_coord)
            
            # Exibir resultados
            print(f"\n📊 RESULTADOS (ε = {epsilon}):")
            print(f"   {'─'*66}")
            print(f"   Deslocamento início:  {result['start']['displacement_meters']:.1f} metros")
            print(f"   Deslocamento fim:     {result['end']['displacement_meters']:.1f} metros")
            print(f"   Distância viagem:     {result['trip_distance_km']:.3f} km")
            print(f"   {'─'*66}")
            
            print(f"\n   Coordenadas protegidas:")
            print(f"   Início:  ({result['start']['lat_private']:.6f}, {result['start']['lon_private']:.6f})")
            print(f"   Fim:     ({result['end']['lat_private']:.6f}, {result['end']['lon_private']:.6f})")
            
            # Validação
            if result['start']['displacement_meters'] < 2000 and result['end']['displacement_meters'] < 2000:
                print(f"\n   ✅ Teste PASSOU - Deslocamentos dentro do esperado")
            else:
                print(f"\n   ⚠️  ATENÇÃO - Deslocamentos muito grandes")
            
        except Exception as e:
            print(f"\n   ❌ Erro no teste: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print("✅ TESTE CONCLUÍDO")
    print("="*70)
    print("\nPróximos passos:")
    print("1. Se os testes passaram, processar o CSV completo:")
    print("   python3 differential_privacy_gps.py dados.csv 0.5 10")
    print("\n2. Ajustar epsilon conforme necessidade de privacidade")
    print("3. Processar dataset completo")
    print("="*70)


if __name__ == "__main__":
    test_single_trip()
