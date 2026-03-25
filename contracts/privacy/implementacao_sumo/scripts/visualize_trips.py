#!/usr/bin/env python3
"""
Script para visualizar trajetos comparando coordenadas originais vs. com privacidade diferencial

Autor: Victor
Data: 2026-03-03
"""

import pandas as pd
import sys
import os
import json

# Tentar importar Folium
try:
    import folium
    from folium import plugins
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("⚠️  folium não instalado. Visualização desabilitada.")
    print("   Instale com: pip install folium")
    sys.exit(1)


def create_trip_map(trajectories: list, df: pd.DataFrame = None, output_html: str = "trip_comparison.html", vehicle_id: str = None):
    """
    Cria mapa interativo comparando trajeto original vs. com privacidade diferencial
    
    Args:
        trajectories: Lista com trajetos completos (do JSON)
        df: DataFrame processado com dados agregados (opcional)
        output_html: Nome do arquivo HTML de saída
        vehicle_id: Se especificado, mostra apenas esse veículo. Senão, mostra todos.
    """
    
    # Filtrar veículo se especificado
    if vehicle_id:
        trajectories = [t for t in trajectories if t['vin'] == vehicle_id]
        if len(trajectories) == 0:
            print(f"❌ Veículo {vehicle_id} não encontrado!")
            return
    
    print("="*70)
    print("🗺️  CRIANDO VISUALIZAÇÃO DE TRAJETOS")
    print("="*70)
    print(f"Veículos a visualizar: {len(trajectories)}")
    
    # Calcular centro do mapa (média de todas as coordenadas)
    all_lats = []
    all_lons = []
    for traj in trajectories:
        for point in traj['trajectory_original']:
            all_lats.append(point[0])
            all_lons.append(point[1])
    
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    
    # Criar mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles='OpenStreetMap'
    )
    
    # Adicionar camadas de controle
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    
    # Feature groups para organizar layers
    fg_original = folium.FeatureGroup(name='🔴 Trajeto Original', show=True)
    fg_private = folium.FeatureGroup(name='🔵 Trajeto com DP', show=True)
    fg_displacement = folium.FeatureGroup(name='📏 Deslocamento (linhas)', show=True)
    fg_info = folium.FeatureGroup(name='ℹ️  Informações', show=True)
    fg_waypoints = folium.FeatureGroup(name='📍 Pontos Intermediários', show=False)
    
    # Processar cada viagem
    import numpy as np
    
    for traj in trajectories:
        vin = traj['vin']
        model = traj['model']
        delta_co2 = traj['delta_co2_g']
        valor_e1 = traj['valor_e1_reais']
        total_distance = traj['total_distance_km']
        co2_real = traj['co2_real_g']
        num_points = traj['num_points']
        
        trajectory_orig = traj['trajectory_original']  # Lista de [lat, lon]
        trajectory_priv = traj['trajectory_private']   # Lista de [lat, lon]
        
        # Coordenadas de início e fim
        start_orig = trajectory_orig[0]
        end_orig = trajectory_orig[-1]
        start_priv = trajectory_priv[0]
        end_priv = trajectory_priv[-1]
        
        # Calcular deslocamentos total (média de todos os pontos)
        displacements = []
        for i in range(len(trajectory_orig)):
            lat_orig, lon_orig = trajectory_orig[i]
            lat_priv, lon_priv = trajectory_priv[i]
            
            disp = np.sqrt(
                ((lat_priv - lat_orig) * 111.32)**2 +
                ((lon_priv - lon_orig) * 111.32 * np.cos(np.radians(lat_orig)))**2
            ) * 1000  # metros
            displacements.append(disp)
        
        avg_displacement = np.mean(displacements)
        max_displacement = np.max(displacements)
        
        # ========== TRAJETO ORIGINAL (VERMELHO) ==========
        # Polilinha conectando TODOS os pontos
        folium.PolyLine(
            locations=trajectory_orig,
            color='red',
            weight=4,
            opacity=0.7,
            popup=folium.Popup(f"""
                <b>{vin}</b><br>
                Trajeto Original<br>
                <b>Pontos:</b> {num_points}<br>
                <b>Distância:</b> {total_distance:.2f} km
            """, max_width=250)
        ).add_to(fg_original)
        
        # Marcador START original (maior)
        folium.CircleMarker(
            location=start_orig,
            radius=10,
            color='darkred',
            fill=True,
            fillColor='red',
            fillOpacity=0.9,
            popup=folium.Popup(f"""
                <b>🚗 INÍCIO (Original)</b><br>
                <b>VIN:</b> {vin}<br>
                <b>Modelo:</b> {model}<br>
                <b>Coords:</b> ({start_orig[0]:.6f}, {start_orig[1]:.6f})<br>
                <b>Pontos no trajeto:</b> {num_points}
            """, max_width=300)
        ).add_to(fg_original)
        
        # Marcador END original (maior)
        folium.CircleMarker(
            location=end_orig,
            radius=10,
            color='darkred',
            fill=True,
            fillColor='orange',
            fillOpacity=0.9,
            popup=folium.Popup(f"""
                <b>🏁 FIM (Original)</b><br>
                <b>VIN:</b> {vin}<br>
                <b>Modelo:</b> {model}<br>
                <b>Coords:</b> ({end_orig[0]:.6f}, {end_orig[1]:.6f})<br>
                <b>Distância total:</b> {total_distance:.2f} km
            """, max_width=300)
        ).add_to(fg_original)
        
        # Pontos intermediários (pequenos, opcionais)
        for i, point in enumerate(trajectory_orig[1:-1], 1):  # Pular primeiro e último
            folium.CircleMarker(
                location=point,
                radius=3,
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.4,
                popup=f"Ponto {i} (Original)"
            ).add_to(fg_waypoints)
        
        # ========== TRAJETO COM DP (AZUL) ==========
        # Polilinha conectando TODOS os pontos com DP
        folium.PolyLine(
            locations=trajectory_priv,
            color='blue',
            weight=4,
            opacity=0.7,
            popup=folium.Popup(f"""
                <b>{vin}</b><br>
                Trajeto com DP (ε=0.5)<br>
                <b>Pontos:</b> {num_points}<br>
                <b>Deslocamento médio:</b> {avg_displacement:.1f}m<br>
                <b>Deslocamento máx:</b> {max_displacement:.1f}m
            """, max_width=300)
        ).add_to(fg_private)
        
        # Marcador START privado (maior)
        folium.CircleMarker(
            location=start_priv,
            radius=10,
            color='darkblue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.9,
            popup=folium.Popup(f"""
                <b>🔒 INÍCIO (Com DP)</b><br>
                <b>VIN:</b> {vin}<br>
                <b>Modelo:</b> {model}<br>
                <b>Coords:</b> ({start_priv[0]:.6f}, {start_priv[1]:.6f})<br>
                <b>Deslocamento:</b> {displacements[0]:.1f}m
            """, max_width=300)
        ).add_to(fg_private)
        
        # Marcador END privado (maior)
        folium.CircleMarker(
            location=end_priv,
            radius=10,
            color='darkblue',
            fill=True,
            fillColor='cyan',
            fillOpacity=0.9,
            popup=folium.Popup(f"""
                <b>🔒 FIM (Com DP)</b><br>
                <b>VIN:</b> {vin}<br>
                <b>Modelo:</b> {model}<br>
                <b>Coords:</b> ({end_priv[0]:.6f}, {end_priv[1]:.6f})<br>
                <b>Deslocamento:</b> {displacements[-1]:.1f}m
            """, max_width=300)
        ).add_to(fg_private)
        
        # Pontos intermediários com DP (pequenos, opcionais)
        for i, point in enumerate(trajectory_priv[1:-1], 1):  # Pular primeiro e último
            folium.CircleMarker(
                location=point,
                radius=3,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.4,
                popup=f"Ponto {i} (Com DP)<br>Desl: {displacements[i]:.1f}m"
            ).add_to(fg_waypoints)
        
        # ========== LINHAS DE DESLOCAMENTO (VERDE/ROXO) ==========
        # Desenhar linhas de deslocamento para alguns pontos representativos
        # (todos os pontos seria muito poluído visualmente)
        step_size = max(1, len(trajectory_orig) // 10)  # Mostrar ~10 linhas de deslocamento
        
        for i in range(0, len(trajectory_orig), step_size):
            color = 'green' if i < len(trajectory_orig) // 2 else 'purple'
            folium.PolyLine(
                locations=[trajectory_orig[i], trajectory_priv[i]],
                color=color,
                weight=1,
                opacity=0.4,
                dash_array='5, 5',
                popup=f"<b>Deslocamento ponto {i}:</b> {displacements[i]:.1f}m"
            ).add_to(fg_displacement)
        
        # ========== INFO CARD NO CENTRO ==========
        # Calcular centro da viagem
        center_lat_trip = sum(p[0] for p in trajectory_orig) / len(trajectory_orig)
        center_lon_trip = sum(p[1] for p in trajectory_orig) / len(trajectory_orig)
        
        # Cor baseada no saldo de CO2
        icon_color = 'green' if delta_co2 > 0 else 'red'
        icon_symbol = '✓' if delta_co2 > 0 else '✗'
        
        folium.Marker(
            location=[center_lat_trip, center_lon_trip],
            icon=folium.Icon(color=icon_color, icon='info-sign'),
            popup=folium.Popup(f"""
                <b>📊 RESUMO DA VIAGEM</b><br><br>
                <b>VIN:</b> {vin}<br>
                <b>Modelo:</b> {model}<br>
                <b>Distância:</b> {total_distance:.2f} km<br>
                <b>Pontos registrados:</b> {num_points}<br>
                <b>CO2 Real:</b> {co2_real:.1f} g<br>
                <b>Delta CO2:</b> {delta_co2:+.1f} g {icon_symbol}<br>
                <b>Valor E1:</b> R$ {valor_e1:+.4f}<br><br>
                <b>🔐 Privacidade Diferencial:</b><br>
                <b>Deslocamento médio:</b> {avg_displacement:.1f}m<br>
                <b>Deslocamento máximo:</b> {max_displacement:.1f}m
            """, max_width=350)
        ).add_to(fg_info)
    
    # Adicionar feature groups ao mapa
    fg_original.add_to(m)
    fg_private.add_to(m)
    fg_displacement.add_to(m)
    fg_info.add_to(m)
    fg_waypoints.add_to(m)
    
    # Adicionar controle de camadas
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Adicionar escala
    plugins.MeasureControl(
        position='topright',
        primary_length_unit='kilometers',
        secondary_length_unit='meters'
    ).add_to(m)
    
    # Adicionar fullscreen
    plugins.Fullscreen(
        position='topright',
        title='Tela cheia',
        title_cancel='Sair da tela cheia'
    ).add_to(m)
    
    # Adicionar minimap
    plugins.MiniMap(toggle_display=True).add_to(m)
    
    # Adicionar legenda
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 300px; height: auto; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
        <p style="margin: 0; font-weight: bold; text-align: center;">📊 LEGENDA</p>
        <hr style="margin: 5px 0;">
        <p style="margin: 5px 0;"><span style="color: red;">━━━━━</span> Trajeto Original (completo)</p>
        <p style="margin: 5px 0;"><span style="color: blue;">━━━━━</span> Trajeto com DP (completo)</p>
        <p style="margin: 5px 0;"><span style="color: green;">┈┈┈</span> Linhas de deslocamento</p>
        <hr style="margin: 5px 0;">
        <p style="margin: 5px 0; font-size: 12px;">
            🔴 Início | 🟠 Fim (Original)<br>
            🔵 Início | 🟦 Fim (Com DP)<br>
            ⚫ Pontos intermediários (<i>camada opcional</i>)
        </p>
        <hr style="margin: 5px 0;">
        <p style="margin: 5px 0; font-size: 11px; color: gray;">
            Clique nos elementos para ver detalhes.<br>
            Use as camadas para filtrar visualização.<br>
            Cada linha conecta TODOS os pontos do trajeto.
        </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Salvar mapa
    m.save(output_html)
    print(f"\n✅ Mapa criado: {output_html}")
    print(f"   Abra no navegador para visualizar!")
    print("="*70)
    
    return m


def create_summary_statistics(trajectories: list):
    """
    Cria estatísticas de deslocamento para análise
    """
    import numpy as np
    
    print("\n" + "="*70)
    print("📈 ESTATÍSTICAS DE DESLOCAMENTO (PRIVACIDADE DIFERENCIAL)")
    print("="*70)
    
    # Calcular deslocamentos de todos os pontos de todas as viagens
    all_displacements = []
    total_points = 0
    
    for traj in trajectories:
        trajectory_orig = traj['trajectory_original']
        trajectory_priv = traj['trajectory_private']
        
        for i in range(len(trajectory_orig)):
            lat_orig, lon_orig = trajectory_orig[i]
            lat_priv, lon_priv = trajectory_priv[i]
            
            disp = np.sqrt(
                ((lat_priv - lat_orig) * 111.32)**2 +
                ((lon_priv - lon_orig) * 111.32 * np.cos(np.radians(lat_orig)))**2
            ) * 1000  # em metros
            
            all_displacements.append(disp)
            total_points += 1
    
    print(f"\n📊 Deslocamentos (metros):")
    print(f"   Total de pontos: {total_points}")
    print(f"   Média:     {np.mean(all_displacements):.1f} m")
    print(f"   Mediana:   {np.median(all_displacements):.1f} m")
    print(f"   Mínimo:    {np.min(all_displacements):.1f} m")
    print(f"   Máximo:    {np.max(all_displacements):.1f} m")
    print(f"   Desvio:    {np.std(all_displacements):.1f} m")
    
    # Estatísticas por viagem
    print(f"\n📊 Por viagem:")
    print(f"   Viagens: {len(trajectories)}")
    print(f"   Média de pontos/viagem: {total_points / len(trajectories):.1f}")
    
    print("="*70)


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 visualize_trips.py <trips_trajectories.json>")
        print("\nExemplo:")
        print("  python3 visualize_trips.py ../data/trips_sumo_processed_trajectories.json")
        print("\nO script irá gerar um HTML para cada veículo em ../data/")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Validar input
    if not os.path.exists(input_file):
        print(f"❌ Arquivo não encontrado: {input_file}")
        sys.exit(1)
    
    # Ler dados JSON com trajetos completos
    print(f"📂 Lendo trajetos de {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        trajectories = json.load(f)
    print(f"   {len(trajectories)} viagens encontradas")
    
    # Criar estatísticas gerais
    create_summary_statistics(trajectories)
    
    # Criar diretório de saída se não existir
    output_dir = '../data'
    os.makedirs(output_dir, exist_ok=True)
    
    # Gerar um mapa para cada veículo
    print("\n" + "="*70)
    print("🗺️  GERANDO MAPAS INDIVIDUAIS POR VEÍCULO")
    print("="*70)
    
    generated_files = []
    for traj in trajectories:
        vehicle_id = traj['vin']
        # Criar nome de arquivo limpo (remover caracteres especiais)
        safe_name = vehicle_id.replace('/', '_').replace('\\', '_')
        output_file = os.path.join(output_dir, f"trip_{safe_name}.html")
        
        print(f"\n🚗 Gerando mapa para {vehicle_id}...")
        create_trip_map([traj], None, output_file, vehicle_id)
        generated_files.append(output_file)
    
    # Instruções finais
    print("\n" + "="*70)
    print("✅ MAPAS GERADOS COM SUCESSO")
    print("="*70)
    print(f"\n📁 Arquivos criados em: {output_dir}/")
    for f in generated_files:
        print(f"   - {os.path.basename(f)}")
    
    print("\n💡 COMO USAR:")
    print(f"   1. Navegue até a pasta: {output_dir}/")
    print("   2. Abra cada HTML para ver o trajeto de um veículo específico")
    print("   3. Use o controle de camadas para:")
    print("      - Mostrar/ocultar trajeto original")
    print("      - Mostrar/ocultar trajeto com DP")
    print("      - Mostrar/ocultar linhas de deslocamento")
    print("      - Mostrar/ocultar pontos intermediários")
    print("   4. Clique nos marcadores e linhas para ver detalhes")
    print("\n💡 Cada HTML mostra o TRAJETO COMPLETO de um veículo!")


if __name__ == "__main__":
    main()
