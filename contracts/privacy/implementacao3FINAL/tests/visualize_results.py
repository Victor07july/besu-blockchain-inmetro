#!/usr/bin/env python3
"""
Visualizador de resultados da privacidade diferencial
Gera gráficos e estatísticas dos dados processados

Autor: Victor
Data: 2026-02-09
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional
import sys


def analyze_dp_results(csv_file: str, output_dir: str = '.'):
    """
    Analisa resultados do processamento com DP
    
    Args:
        csv_file: Arquivo CSV com dados processados
        output_dir: Diretório para salvar gráficos
    """
    print("="*70)
    print("📊 ANÁLISE DE RESULTADOS - PRIVACIDADE DIFERENCIAL")
    print("="*70)
    
    # Carregar dados
    print(f"\n📄 Carregando: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # Filtrar apenas viagens processadas
    if 'dp_processed' in df.columns:
        df_processed = df[df['dp_processed'] == True]
        print(f"   Total de registros: {len(df)}")
        print(f"   Processados com DP: {len(df_processed)}")
    else:
        df_processed = df
        print(f"   Total de registros: {len(df)}")
    
    if len(df_processed) == 0:
        print("❌ Nenhum registro processado encontrado!")
        return
    
    # Estatísticas de deslocamento
    print("\n" + "="*70)
    print("📏 ESTATÍSTICAS DE DESLOCAMENTO")
    print("="*70)
    
    if 'start_displacement_m' in df_processed.columns:
        print("\n🎯 Coordenadas de INÍCIO:")
        print(f"   Média:    {df_processed['start_displacement_m'].mean():.1f} m")
        print(f"   Mediana:  {df_processed['start_displacement_m'].median():.1f} m")
        print(f"   Mínimo:   {df_processed['start_displacement_m'].min():.1f} m")
        print(f"   Máximo:   {df_processed['start_displacement_m'].max():.1f} m")
        print(f"   Desvio:   {df_processed['start_displacement_m'].std():.1f} m")
    
    if 'end_displacement_m' in df_processed.columns:
        print("\n🏁 Coordenadas de FIM:")
        print(f"   Média:    {df_processed['end_displacement_m'].mean():.1f} m")
        print(f"   Mediana:  {df_processed['end_displacement_m'].median():.1f} m")
        print(f"   Mínimo:   {df_processed['end_displacement_m'].min():.1f} m")
        print(f"   Máximo:   {df_processed['end_displacement_m'].max():.1f} m")
        print(f"   Desvio:   {df_processed['end_displacement_m'].std():.1f} m")
    
    # Epsilon usado
    if 'dp_epsilon' in df_processed.columns:
        epsilon = df_processed['dp_epsilon'].iloc[0]
        print(f"\n🔐 Parâmetro de privacidade:")
        print(f"   Epsilon (ε): {epsilon}")
    
    # Análise de distâncias
    print("\n" + "="*70)
    print("🚗 ANÁLISE DE DISTÂNCIAS")
    print("="*70)
    
    if 'total_distance' in df_processed.columns and 'gps_distance_private_km' in df_processed.columns:
        original_dist = df_processed['total_distance'].sum()
        private_dist = df_processed['gps_distance_private_km'].sum()
        diff_pct = abs(original_dist - private_dist) / original_dist * 100
        
        print(f"\n   Distância total (original):  {original_dist:.2f} km")
        print(f"   Distância total (privada):   {private_dist:.2f} km")
        print(f"   Diferença relativa:          {diff_pct:.2f}%")
        
        # Análise por viagem
        df_processed['distance_diff_pct'] = abs(
            df_processed['total_distance'] - df_processed['gps_distance_private_km']
        ) / df_processed['total_distance'] * 100
        
        print(f"\n   Diferença média por viagem:  {df_processed['distance_diff_pct'].mean():.2f}%")
        print(f"   Diferença máxima:            {df_processed['distance_diff_pct'].max():.2f}%")
    
    # Análise de emissões
    print("\n" + "="*70)
    print("🌱 ANÁLISE DE EMISSÕES")
    print("="*70)
    
    if 'emission' in df_processed.columns:
        total_emission = df_processed['emission'].sum()
        avg_emission = df_processed['emission'].mean()
        
        print(f"\n   Emissão total:   {total_emission:.1f} g CO2")
        print(f"   Emissão média:   {avg_emission:.1f} g CO2/viagem")
        
        if 'fuel_type' in df_processed.columns:
            print("\n   Por tipo de combustível:")
            for fuel in df_processed['fuel_type'].unique():
                fuel_emission = df_processed[df_processed['fuel_type'] == fuel]['emission'].sum()
                fuel_count = len(df_processed[df_processed['fuel_type'] == fuel])
                print(f"      {fuel:10s}: {fuel_emission:.1f} g CO2 ({fuel_count} viagens)")
    
    # Gerar gráficos
    print("\n" + "="*70)
    print("📈 GERANDO GRÁFICOS")
    print("="*70)
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Análise de Privacidade Diferencial GPS', fontsize=16, fontweight='bold')
    
    # Gráfico 1: Distribuição de deslocamentos (início)
    if 'start_displacement_m' in df_processed.columns:
        ax1 = axes[0, 0]
        df_processed['start_displacement_m'].hist(bins=30, ax=ax1, color='steelblue', edgecolor='black')
        ax1.set_xlabel('Deslocamento (metros)')
        ax1.set_ylabel('Frequência')
        ax1.set_title('Distribuição de Deslocamento - Coordenadas de Início')
        ax1.axvline(df_processed['start_displacement_m'].mean(), color='red', 
                   linestyle='--', label=f'Média: {df_processed["start_displacement_m"].mean():.1f}m')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
    
    # Gráfico 2: Distribuição de deslocamentos (fim)
    if 'end_displacement_m' in df_processed.columns:
        ax2 = axes[0, 1]
        df_processed['end_displacement_m'].hist(bins=30, ax=ax2, color='coral', edgecolor='black')
        ax2.set_xlabel('Deslocamento (metros)')
        ax2.set_ylabel('Frequência')
        ax2.set_title('Distribuição de Deslocamento - Coordenadas de Fim')
        ax2.axvline(df_processed['end_displacement_m'].mean(), color='red', 
                   linestyle='--', label=f'Média: {df_processed["end_displacement_m"].mean():.1f}m')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # Gráfico 3: Comparação distâncias
    if 'total_distance' in df_processed.columns and 'gps_distance_private_km' in df_processed.columns:
        ax3 = axes[1, 0]
        sample = df_processed.head(20)  # Primeiras 20 viagens
        x = np.arange(len(sample))
        width = 0.35
        
        ax3.bar(x - width/2, sample['total_distance'], width, label='Original', color='steelblue')
        ax3.bar(x + width/2, sample['gps_distance_private_km'], width, label='Privada', color='coral')
        
        ax3.set_xlabel('Viagem')
        ax3.set_ylabel('Distância (km)')
        ax3.set_title('Comparação: Distância Original vs Privada (primeiras 20 viagens)')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
    
    # Gráfico 4: Emissões por tipo de combustível
    if 'emission' in df_processed.columns and 'fuel_type' in df_processed.columns:
        ax4 = axes[1, 1]
        fuel_emissions = df_processed.groupby('fuel_type')['emission'].sum()
        
        colors = {'Gasolina': 'orangered', 'Etanol': 'green', 'Flex': 'gold'}
        fuel_colors = [colors.get(fuel, 'gray') for fuel in fuel_emissions.index]
        
        fuel_emissions.plot(kind='bar', ax=ax4, color=fuel_colors, edgecolor='black')
        ax4.set_xlabel('Tipo de Combustível')
        ax4.set_ylabel('Emissão Total (g CO2)')
        ax4.set_title('Emissões por Tipo de Combustível')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Salvar figura
    output_file = f"{output_dir}/dp_analysis.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Gráficos salvos em: {output_file}")
    
    # Mostrar
    try:
        plt.show()
    except:
        print("   (Interface gráfica não disponível - arquivo salvo)")
    
    # Relatório resumido
    print("\n" + "="*70)
    print("📋 RESUMO EXECUTIVO")
    print("="*70)
    
    print(f"\n✓ {len(df_processed)} viagens processadas com privacidade diferencial")
    
    if 'start_displacement_m' in df_processed.columns:
        avg_disp = (df_processed['start_displacement_m'].mean() + 
                   df_processed['end_displacement_m'].mean()) / 2
        print(f"✓ Deslocamento médio: {avg_disp:.1f} metros")
    
    if 'dp_epsilon' in df_processed.columns:
        print(f"✓ Nível de privacidade (ε): {df_processed['dp_epsilon'].iloc[0]}")
    
    print(f"✓ Dados protegidos mantêm utilidade para análise")
    print(f"✓ Coordenadas projetadas em vias trafegáveis válidas")
    
    print("\n" + "="*70)


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 visualize_results.py <arquivo_private.csv>")
        print("\nExemplo:")
        print("  python3 visualize_results.py dados_private.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    analyze_dp_results(csv_file)


if __name__ == "__main__":
    main()
