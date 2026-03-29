#!/usr/bin/env python3
"""
Script para processar dados SUMO e enviar para contrato E1RegistryEuclidean

Este CSV já contém:
- CO2 calculado por segmento
- Distâncias separadas (city/highway)
- Coordenadas GPS

Precisamos:
- Agregar dados por vehicle_id (cada vehicle_id = 1 viagem)
- Calcular meta de CO2 baseado em consumo do fabricante
- Aplicar privacidade diferencial nas coordenadas
- Enviar para blockchain

Autor: Victor
Data: 2026-03-03
"""

import pandas as pd
import numpy as np
import sys
import json
from datetime import datetime
from web3 import Web3
from eth_account import Account
import hashlib

# Map matching e malha viária
try:
    import osmnx as ox
    import networkx as nx
    MAP_MATCHING_AVAILABLE = True
except ImportError:
    MAP_MATCHING_AVAILABLE = False
    print("⚠️  osmnx não instalado. Map matching desabilitado.")
    print("   Instale com: pip install osmnx")

# ==================== CONFIGURAÇÕES ====================
# Consumo do fabricante (km/l)
CONSUMO_FABRICANTE = 12.0

# Fator de emissão gasolina (kg CO2 por litro)
EMISSAO_GASOLINA = 2.31

# Preço do carbono (R$/ton)
CARBON_PRICE = 50.0

# Privacidade diferencial
EPSILON = 0.5
SENSITIVITY = 0.0001  # graus (≈22m de deslocamento médio - próximo do original)

# Map matching
ENABLE_MAP_MATCHING = True   # True: Aplicar snap to road | False: Apenas ruído
SEARCH_RADIUS = 1500         # Raio de busca da malha viária (metros)
MAX_SNAP_DISTANCE = 100      # Distância máxima preferida para snap (metros)
FORCE_SNAP = True            # Forçar snap mesmo se dist > MAX_SNAP_DISTANCE (evita mar)
GRAPH_CACHE = {}             # Cache de grafos baixados

# Stepping de leitura
ROW_STEP = 50                # Processar a cada N linhas (1=todas, 5=de 5 em 5, etc)

# Blockchain
RPC_URL = "http://localhost:8545"
CHAIN_ID = 1337
# =======================================================


def add_laplace_noise(value: float, epsilon: float = EPSILON, sensitivity: float = SENSITIVITY) -> float:
    """
    Adiciona ruído Laplace para privacidade diferencial
    
    Args:
        value: Valor original (coordenada)
        epsilon: Parâmetro de privacidade
        sensitivity: Sensibilidade (0.001 grau ≈ 111 metros)
        
    Returns:
        Valor com ruído
    """
    scale = sensitivity / epsilon
    noise = np.random.laplace(loc=0, scale=scale)
    return value + noise


def get_road_network(lat: float, lon: float, radius: int = SEARCH_RADIUS):
    """
    Baixa malha viária ao redor das coordenadas usando OSMnx
    Tenta com raios crescentes se não encontrar grafo
    
    Args:
        lat: Latitude do ponto central
        lon: Longitude do ponto central
        radius: Raio de busca em metros
        
    Returns:
        Grafo da rede viária ou None se falhar
    """
    if not MAP_MATCHING_AVAILABLE:
        return None
    
    # Cache key baseado em região aproximada (2 casas decimais = ~1km)
    cache_key = (round(lat, 2), round(lon, 2))
    
    if cache_key in GRAPH_CACHE:
        return GRAPH_CACHE[cache_key]
    
    # Tentar com raios crescentes
    radii_to_try = [radius, radius * 2, radius * 3]
    
    for attempt, r in enumerate(radii_to_try, 1):
        try:
            # Baixar grafo de ruas trafegáveis
            G = ox.graph_from_point(
                (lat, lon),
                dist=r,
                network_type='drive',
                simplify=False  # Não simplificar para ter mais nós
            )
            
            if len(G.nodes) > 0:
                GRAPH_CACHE[cache_key] = G
                if attempt > 1:
                    print(f"  🗺️  Grafo encontrado na tentativa {attempt} (raio={r}m): {len(G.nodes)} nós")
                return G
                
        except Exception as e:
            if attempt == len(radii_to_try):
                print(f"⚠️  Erro ao baixar grafo após {attempt} tentativas: {e}")
            continue
    
    return None


def snap_to_nearest_road(G, lat: float, lon: float, lat_orig: float, lon_orig: float, max_distance: float = MAX_SNAP_DISTANCE, force: bool = FORCE_SNAP):
    """
    Projeta coordenada para a via trafegável mais próxima (map matching)
    
    Args:
        G: Grafo da rede viária
        lat: Latitude (com ruído)
        lon: Longitude (com ruído)
        lat_orig: Latitude original (para validar deslocamento)
        lon_orig: Longitude original (para validar deslocamento)
        max_distance: Distância máxima preferida para snap (metros)
        force: Se True, força snap mesmo se dist > max_distance (evita pontos no mar)
        
    Returns:
        Tupla (lat_snapped, lon_snapped, success, rejected_by_distance)
    """
    if G is None or not MAP_MATCHING_AVAILABLE:
        return lat, lon, False, False
    
    try:
        # Usar nearest_edges para projetar na rua mais próxima (não apenas nó)
        # Isso dá mais precisão e variedade de posições
        try:
            nearest_edge = ox.distance.nearest_edges(G, lon, lat)
            # nearest_edge retorna (u, v, key) - os nós da edge mais próxima
            u, v, key = nearest_edge
            
            # Pegar coordenadas dos dois nós da edge
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            
            # Usar ponto médio da edge (aproximação simples)
            lat_snapped = (u_data['y'] + v_data['y']) / 2
            lon_snapped = (u_data['x'] + v_data['x']) / 2
            
        except:
            # Fallback: usar nearest_nodes
            nearest_node = ox.distance.nearest_nodes(G, lon, lat)
            node_data = G.nodes[nearest_node]
            lat_snapped = node_data['y']
            lon_snapped = node_data['x']
        
        # VALIDAÇÃO: Verificar se o snap não moveu muito longe do ponto original
        import numpy as np
        dlat = (lat_snapped - lat_orig) * 111320
        dlon = (lon_snapped - lon_orig) * 111320 * np.cos(np.radians(lat_orig))
        snap_distance = np.sqrt(dlat**2 + dlon**2)
        
        if snap_distance > max_distance:
            if force:
                # Forçar snap mesmo estando longe (evita ponto no mar)
                return lat_snapped, lon_snapped, True, True  # success mas rejected_by_distance
            else:
                # Rejeitar snap - usar apenas ruído
                return lat, lon, False, True
        
        return lat_snapped, lon_snapped, True, False  # success, not rejected
        
    except Exception as e:
        print(f"⚠️  Erro no snap to road: {e}")
        return lat, lon, False, False


def generate_pseudonimo(vehicle_id: str, salt: str = "E1_PRIVACY") -> str:
    """
    Gera endereço pseudônimo a partir do vehicle_id
    
    Args:
        vehicle_id: ID do veículo
        salt: Salt para hash
        
    Returns:
        Endereço Ethereum checksummed
    """
    combined = f"{vehicle_id}{salt}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    account = Account.from_key(hash_bytes)
    return account.address


def process_sumo_csv(input_csv: str, consumo_fabricante: float = CONSUMO_FABRICANTE, row_step: int = ROW_STEP) -> pd.DataFrame:
    """
    Processa CSV SUMO agregando por vehicle_id
    
    Args:
        input_csv: Caminho do arquivo SUMO CSV
        consumo_fabricante: Consumo declarado pelo fabricante (km/l)
        row_step: Processar a cada N linhas (1=todas, 5=de 5 em 5, etc)
        
    Returns:
        DataFrame com viagens agregadas
    """
    print("="*70)
    print("🚗 PROCESSAMENTO SUMO → E1 REGISTRY")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"🏭 Consumo fabricante: {consumo_fabricante} km/l")
    print(f"💰 Preço carbono: R$ {CARBON_PRICE}/ton")
    print(f"🔐 Epsilon (ε): {EPSILON}")
    
    if row_step > 1:
        print(f"⏭️  Row stepping: Processando 1 a cada {row_step} linhas")
    else:
        print(f"📊 Row stepping: Processando todas as linhas")
    
    if MAP_MATCHING_AVAILABLE and ENABLE_MAP_MATCHING:
        print(f"🗺️  Map matching: ATIVADO (raio {SEARCH_RADIUS}m)")
    else:
        print(f"🗺️  Map matching: DESATIVADO")
    
    print("="*70)
    
    # Ler CSV
    print("\n📊 Carregando dados SUMO...")
    df = pd.read_csv(input_csv)
    print(f"   Total de registros no arquivo: {len(df):,}")
    
    # Aplicar stepping se configurado
    if row_step > 1:
        df = df.iloc[::row_step]
        print(f"   Após stepping (1 a cada {row_step}): {len(df):,} registros")
    
    print(f"   Veículos únicos: {df['vehicle_id'].nunique()}")
    
    # Agrupar por vehicle_id
    print("\n🔄 Agregando viagens por vehicle_id...")
    results = []
    trajectories = []  # Lista para guardar trajetos completos
    
    # Estatísticas de map matching
    total_points_processed = 0
    total_snaps_attempted = 0
    total_snaps_successful = 0
    total_snaps_rejected = 0
    
    for vehicle_id, group in df.groupby('vehicle_id'):
        # Ordenar por tempo
        group = group.sort_values('start_time')
        
        # ========== DADOS BÁSICOS ==========
        vin = f"SUMO_{vehicle_id}"
        model = group.iloc[0]['model']
        fuel_type = group.iloc[0]['fuel_type']
        
        # Timestamps
        start_time = pd.to_datetime(group.iloc[0]['start_time'])
        end_time = pd.to_datetime(group.iloc[-1]['end_time'])
        timestamp = int(start_time.timestamp())
        
        # GPS original (primeira e última posição)
        start_lat_orig = group.iloc[0]['start_lat']
        start_lon_orig = group.iloc[0]['start_lon']
        end_lat_orig = group.iloc[-1]['end_lat']
        end_lon_orig = group.iloc[-1]['end_lon']
        
        # ========== AGREGAÇÕES ==========
        # CO2 em gramas (soma de todos os segmentos)
        co2_real_g = group['CO2'].sum()
        
        # Distâncias em km
        total_distance_km = group['distance'].sum()
        distance_city_km = group['distance_city'].sum()
        distance_highway_km = group['distance_highway'].sum()
        
        # Outros poluentes
        nox_total = group['NOx'].sum()
        pmx_total = group['PMx'].sum()
        
        # ========== CÁLCULOS E1 ==========
        # Combustível consumido (estimado do CO2)
        # CO2 (g) / fator_emissao (g/l) = litros
        fuel_consumed_liters = co2_real_g / (EMISSAO_GASOLINA * 1000)  # EMISSAO_GASOLINA em kg/l, converter para g/l
        
        # CO2 meta baseado no consumo do fabricante
        fuel_meta_liters = total_distance_km / consumo_fabricante
        co2_meta_g = fuel_meta_liters * EMISSAO_GASOLINA * 1000  # kg → g
        
        # Delta CO2 (meta - real)
        delta_co2_g = co2_meta_g - co2_real_g
        
        # Monetização: (g / 1e6) × preço = R$
        valor_e1_reais = (delta_co2_g / 1_000_000) * CARBON_PRICE
        
        # ========== PRIVACIDADE DIFERENCIAL + MAP MATCHING ==========
        # ETAPA 1: Aplicar ruído Laplaciano
        start_lat_noisy = add_laplace_noise(start_lat_orig, EPSILON)
        start_lon_noisy = add_laplace_noise(start_lon_orig, EPSILON)
        end_lat_noisy = add_laplace_noise(end_lat_orig, EPSILON)
        end_lon_noisy = add_laplace_noise(end_lon_orig, EPSILON)
        
        # ETAPA 2: Map matching (snap to road)
        start_snapped = False
        end_snapped = False
        
        if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE:
            # Baixar malha viária do início
            G_start = get_road_network(start_lat_orig, start_lon_orig)
            if G_start is not None:
                start_lat_private, start_lon_private, start_snapped, _ = snap_to_nearest_road(
                    G_start, start_lat_noisy, start_lon_noisy, start_lat_orig, start_lon_orig
                )
            else:
                start_lat_private = start_lat_noisy
                start_lon_private = start_lon_noisy
            
            # Baixar malha viária do fim
            G_end = get_road_network(end_lat_orig, end_lon_orig)
            if G_end is not None:
                end_lat_private, end_lon_private, end_snapped, _ = snap_to_nearest_road(
                    G_end, end_lat_noisy, end_lon_noisy, end_lat_orig, end_lon_orig
                )
            else:
                end_lat_private = end_lat_noisy
                end_lon_private = end_lon_noisy
        else:
            # Sem map matching: usar coordenadas ruidosas
            start_lat_private = start_lat_noisy
            start_lon_private = start_lon_noisy
            end_lat_private = end_lat_noisy
            end_lon_private = end_lon_noisy
        
        # Pseudônimo
        pseudonimo = generate_pseudonimo(vin)
        
        # ========== PROCESSAR TODOS OS PONTOS DO TRAJETO ==========
        trajectory_points_orig = []
        trajectory_points_priv = []
        trajectory_times = []
        
        # Processar cada segmento do trajeto
        # IMPORTANTE: usar end_lat/end_lon (não start) porque start é sempre o ponto de partida original
        for seg_idx, seg_row in group.iterrows():
            seg_time = pd.to_datetime(seg_row['end_time'])  # Usar end_time
            
            # END point do segmento (onde o veículo chegou nesse momento)
            seg_lat = seg_row['end_lat']
            seg_lon = seg_row['end_lon']
            
            # Aplicar DP
            seg_lat_noisy = add_laplace_noise(seg_lat, EPSILON)
            seg_lon_noisy = add_laplace_noise(seg_lon, EPSILON)
            
            # Map matching
            if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE:
                total_points_processed += 1
                G_seg = get_road_network(seg_lat, seg_lon)
                if G_seg is not None:
                    total_snaps_attempted += 1
                    seg_lat_priv, seg_lon_priv, snap_success, snap_rejected = snap_to_nearest_road(
                        G_seg, seg_lat_noisy, seg_lon_noisy, seg_lat, seg_lon
                    )
                    if snap_success:
                        total_snaps_successful += 1
                    if snap_rejected:
                        total_snaps_rejected += 1
                else:
                    seg_lat_priv = seg_lat_noisy
                    seg_lon_priv = seg_lon_noisy
            else:
                seg_lat_priv = seg_lat_noisy
                seg_lon_priv = seg_lon_noisy
            
            trajectory_points_orig.append([seg_lat, seg_lon])
            trajectory_points_priv.append([seg_lat_priv, seg_lon_priv])
            trajectory_times.append(seg_time.isoformat())
        
        # Guardar trajeto completo
        trajectories.append({
            'vin': vin,
            'model': model,
            'fuel_type': fuel_type,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_distance_km': total_distance_km,
            'co2_real_g': co2_real_g,
            'delta_co2_g': delta_co2_g,
            'valor_e1_reais': valor_e1_reais,
            'trajectory_original': trajectory_points_orig,
            'trajectory_private': trajectory_points_priv,
            'trajectory_times': trajectory_times,
            'num_points': len(trajectory_points_orig)
        })
        
        # ========== ARMAZENAR AGREGAÇÕES ==========
        results.append({
            'vin': vin,
            'model': model,
            'fuel_type': fuel_type,
            'timestamp': timestamp,
            'start_time': start_time,
            'end_time': end_time,
            'duration_seconds': (end_time - start_time).total_seconds(),
            'total_distance_km': total_distance_km,
            'distance_city_km': distance_city_km,
            'distance_highway_km': distance_highway_km,
            'fuel_consumed_liters': fuel_consumed_liters,
            'co2_real_g': co2_real_g,
            'co2_meta_g': co2_meta_g,
            'delta_co2_g': delta_co2_g,
            'valor_e1_reais': valor_e1_reais,
            'nox_total': nox_total,
            'pmx_total': pmx_total,
            'start_lat_orig': start_lat_orig,
            'start_lon_orig': start_lon_orig,
            'end_lat_orig': end_lat_orig,
            'end_lon_orig': end_lon_orig,
            'start_lat_private': start_lat_private,
            'start_lon_private': start_lon_private,
            'end_lat_private': end_lat_private,
            'end_lon_private': end_lon_private,
            'start_map_matched': start_snapped,
            'end_map_matched': end_snapped,
            'pseudonimo': pseudonimo,
            'num_segments': len(group)
        })
        
        # Log
        print(f"\n🚙 Veículo: {vin}")
        print(f"   Modelo: {model}")
        print(f"   Segmentos: {len(group)}")
        print(f"   📏 Distância: {total_distance_km:.3f} km (city: {distance_city_km:.3f}, highway: {distance_highway_km:.3f})")
        print(f"   ⛽ Combustível: {fuel_consumed_liters:.3f} l")
        print(f"   🏭 CO2 real: {co2_real_g:.1f} g")
        print(f"   🎯 CO2 meta: {co2_meta_g:.1f} g")
        print(f"   📊 Delta: {delta_co2_g:+.1f} g")
        print(f"   💰 Valor E1: R$ {valor_e1_reais:+.4f}")
        
        # Calcular deslocamento para mostrar
        start_displacement_km = np.sqrt(
            ((start_lat_private - start_lat_orig) * 111.32)**2 +
            ((start_lon_private - start_lon_orig) * 111.32 * np.cos(np.radians(start_lat_orig)))**2
        )
        end_displacement_km = np.sqrt(
            ((end_lat_private - end_lat_orig) * 111.32)**2 +
            ((end_lon_private - end_lon_orig) * 111.32 * np.cos(np.radians(end_lat_orig)))**2
        )
        
        # Mostrar privacidade diferencial
        print(f"\n   🔐 PRIVACIDADE DIFERENCIAL (ε={EPSILON}):")
        print(f"   📍 Start Original:  ({start_lat_orig:.6f}, {start_lon_orig:.6f})")
        
        snap_status_start = "✓ MAP MATCHED" if start_snapped else "⚠ SEM MAP MATCHING"
        print(f"   🔒 Start Protegido: ({start_lat_private:.6f}, {start_lon_private:.6f}) {snap_status_start}")
        print(f"   📏 Deslocamento:    {start_displacement_km*1000:.1f} metros")
        
        print(f"   📍 End Original:    ({end_lat_orig:.6f}, {end_lon_orig:.6f})")
        
        snap_status_end = "✓ MAP MATCHED" if end_snapped else "⚠ SEM MAP MATCHING"
        print(f"   🔒 End Protegido:   ({end_lat_private:.6f}, {end_lon_private:.6f}) {snap_status_end}")
        print(f"   📏 Deslocamento:    {end_displacement_km*1000:.1f} metros")
    
    # Criar DataFrame
    df_result = pd.DataFrame(results)
    
    # Estatísticas finais
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS FINAIS")
    print("="*70)
    print(f"Viagens processadas: {len(df_result)}")
    print(f"Distância total: {df_result['total_distance_km'].sum():.2f} km")
    print(f"Combustível total: {df_result['fuel_consumed_liters'].sum():.2f} l")
    print(f"CO2 real total: {df_result['co2_real_g'].sum():.1f} g")
    print(f"CO2 meta total: {df_result['co2_meta_g'].sum():.1f} g")
    print(f"Delta CO2: {df_result['delta_co2_g'].sum():+.1f} g")
    print(f"Valor E1 total: R$ {df_result['valor_e1_reais'].sum():+.2f}")
    
    creditos = df_result[df_result['valor_e1_reais'] > 0]['valor_e1_reais'].sum()
    debitos = abs(df_result[df_result['valor_e1_reais'] < 0]['valor_e1_reais'].sum())
    
    print(f"\n💰 Créditos: R$ {creditos:.2f}")
    print(f"💸 Débitos: R$ {debitos:.2f}")
    print(f"📈 Saldo líquido: R$ {creditos - debitos:+.2f}")
    
    # Estatísticas de Map Matching
    if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE and total_points_processed > 0:
        print(f"\n🗺️  MAP MATCHING:")
        print(f"   Pontos processados: {total_points_processed:,}")
        print(f"   Snaps tentados: {total_snaps_attempted:,} ({total_snaps_attempted/total_points_processed*100:.1f}%)")
        print(f"   Snaps bem-sucedidos: {total_snaps_successful:,} ({total_snaps_successful/total_points_processed*100:.1f}%)")
        if FORCE_SNAP:
            print(f"   Snaps forçados (>{MAX_SNAP_DISTANCE}m): {total_snaps_rejected:,} ({total_snaps_rejected/total_points_processed*100:.1f}%)")
            print(f"   ✅ TODOS os pontos estão em ruas (FORCE_SNAP=True)")
        else:
            print(f"   Snaps rejeitados (>{MAX_SNAP_DISTANCE}m): {total_snaps_rejected:,} ({total_snaps_rejected/total_points_processed*100:.1f}%)")
            print(f"   Apenas ruído (sem snap): {total_points_processed - total_snaps_successful:,} ({(total_points_processed - total_snaps_successful)/total_points_processed*100:.1f}%)")
    
    print("="*70)
    
    return df_result, trajectories


def save_to_csv(df: pd.DataFrame, output_csv: str):
    """Salva DataFrame processado em CSV"""
    df.to_csv(output_csv, index=False)
    print(f"\n💾 Dados agregados salvos em: {output_csv}")


def save_trajectories_json(trajectories: list, output_json: str):
    """Salva trajetos completos em JSON para visualização"""
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(trajectories, f, indent=2, ensure_ascii=False)
    print(f"💾 Trajetos completos salvos em: {output_json}")


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 process_sumo_csv.py <input.csv> [output.csv] [consumo_fabricante] [row_step]")
        print("\nExemplo:")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv trips_sumo.csv 12.0")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv trips_sumo.csv 12.0 5  # Processar de 5 em 5")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'trips_sumo_processed.csv'
    consumo_fab = float(sys.argv[3]) if len(sys.argv) > 3 else CONSUMO_FABRICANTE
    step = int(sys.argv[4]) if len(sys.argv) > 4 else ROW_STEP
    
    # Processar
    df_trips, trajectories = process_sumo_csv(input_file, consumo_fab, step)
    
    # Salvar CSV (dados agregados)
    save_to_csv(df_trips, output_file)
    
    # Salvar JSON (trajetos completos para visualização)
    json_file = output_file.replace('.csv', '_trajectories.json')
    save_trajectories_json(trajectories, json_file)


if __name__ == "__main__":
    main()