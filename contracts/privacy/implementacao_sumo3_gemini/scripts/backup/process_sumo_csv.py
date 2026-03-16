#!/usr/bin/env python3
"""
Script para processar dados SUMO com offset determinístico

Este CSV já contém:
- CO2 calculado por segmento
- Distâncias separadas (city/highway)
- Coordenadas GPS

Novidades nesta versão:
- Offset determinístico (x, y) substituindo privacidade diferencial probabilística
- Limitação de raio máximo com clipping automático
- Offset reversível (chave simétrica)
- Map matching para garantir pontos em vias trafegáveis

Autor: Victor
Data: 2026-03-06
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

# Offset Determinístico (chave de deslocamento)
OFFSET_X = 0.01  # graus de latitude (≈1.1 km)
OFFSET_Y = 0.01  # graus de longitude (≈1.0 km no Rio, varia com latitude)
MAX_RADIUS_KM = 2.0  # Raio máximo de deslocamento (clipping)

# Map matching
ENABLE_MAP_MATCHING = True   # True: Aplicar snap to road | False: Apenas offset
SEARCH_RADIUS = 1500         # Raio de busca da malha viária (metros)
MAX_SNAP_DISTANCE = 100      # Distância máxima preferida para snap (metros)
FORCE_SNAP = True            # Forçar snap mesmo se dist > MAX_SNAP_DISTANCE (evita mar)
GRAPH_CACHE = {}             # Cache de grafos baixados

# Stepping de leitura
ROW_STEP = 1                # Processar a cada N linhas (1=todas, 5=de 5 em 5, etc)

# Blockchain
RPC_URL = "http://localhost:8545"
CHAIN_ID = 1337
# =======================================================


def calculate_offset_distance(offset_x: float, offset_y: float, latitude: float) -> float:
    """
    Calcula a distância real (em km) do deslocamento em graus
    
    Args:
        offset_x: Deslocamento em graus de latitude
        offset_y: Deslocamento em graus de longitude  
        latitude: Latitude original (para correção de longitude)
        
    Returns:
        Distância do deslocamento em km
    """
    # 1 grau de latitude ≈ 111.32 km (constante)
    dlat_km = offset_x * 111.32
    
    # 1 grau de longitude varia com latitude: 111.32 × cos(lat)
    dlon_km = offset_y * 111.32 * np.cos(np.radians(latitude))
    
    # Distância euclidiana
    distance_km = np.sqrt(dlat_km**2 + dlon_km**2)
    
    return distance_km


def clip_offset_to_radius(offset_x: float, offset_y: float, latitude: float, max_radius_km: float = MAX_RADIUS_KM) -> tuple:
    """
    Limita o offset ao raio máximo usando clipping proporcional
    Preserva a direção do deslocamento, apenas reduz a magnitude
    
    Args:
        offset_x: Deslocamento desejado em latitude (graus)
        offset_y: Deslocamento desejado em longitude (graus)
        latitude: Latitude original (para cálculo correto)
        max_radius_km: Raio máximo permitido em km
        
    Returns:
        Tupla (offset_x_clipped, offset_y_clipped, was_clipped, original_distance_km)
    """
    # Calcular distância do offset original
    distance_km = calculate_offset_distance(offset_x, offset_y, latitude)
    
    # Se está dentro do raio, retornar sem modificações
    if distance_km <= max_radius_km:
        return offset_x, offset_y, False, distance_km
    
    # Calcular fator de escala para clipar ao raio máximo
    scale_factor = max_radius_km / distance_km
    
    # Aplicar escala mantendo direção
    offset_x_clipped = offset_x * scale_factor
    offset_y_clipped = offset_y * scale_factor
    
    return offset_x_clipped, offset_y_clipped, True, distance_km


def apply_deterministic_offset(lat: float, lon: float, offset_x: float = OFFSET_X, offset_y: float = OFFSET_Y, max_radius_km: float = MAX_RADIUS_KM) -> tuple:
    """
    Aplica offset determinístico com limitação de raio
    
    Args:
        lat: Latitude original
        lon: Longitude original
        offset_x: Deslocamento em graus de latitude
        offset_y: Deslocamento em graus de longitude
        max_radius_km: Raio máximo de deslocamento
        
    Returns:
        Tupla (lat_offset, lon_offset, was_clipped, original_distance_km, final_distance_km)
    """
    # Clipar offset ao raio máximo
    offset_x_final, offset_y_final, was_clipped, original_distance = clip_offset_to_radius(
        offset_x, offset_y, lat, max_radius_km
    )
    
    # Aplicar offset
    lat_offset = lat + offset_x_final
    lon_offset = lon + offset_y_final
    
    # Calcular distância final (após clipping)
    final_distance = calculate_offset_distance(offset_x_final, offset_y_final, lat)
    
    return lat_offset, lon_offset, was_clipped, original_distance, final_distance


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
        lat: Latitude (com offset)
        lon: Longitude (com offset)
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
                # Rejeitar snap - usar apenas offset
                return lat, lon, False, True
        
        return lat_snapped, lon_snapped, True, False  # success, not rejected
        
    except Exception as e:
        print(f"⚠️  Erro no snap to road: {e}")
        return lat, lon, False, False


def calculate_gps_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distância entre dois pontos GPS usando fórmula de Haversine
    
    Args:
        lat1, lon1: Coordenadas do primeiro ponto
        lat2, lon2: Coordenadas do segundo ponto
        
    Returns:
        Distância em quilômetros
    """
    # Raio da Terra em km
    R = 6371.0
    
    # Converter para radianos
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Diferenças
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c
    return distance


def calculate_trajectory_distance(trajectory_points: list) -> float:
    """
    Calcula a distância total de um trajeto (soma das distâncias entre pontos consecutivos)
    Usa fórmula de Haversine (linha reta entre pontos)
    
    Args:
        trajectory_points: Lista de [lat, lon]
        
    Returns:
        Distância total em km
    """
    if len(trajectory_points) < 2:
        return 0.0
    
    total_distance = 0.0
    for i in range(len(trajectory_points) - 1):
        lat1, lon1 = trajectory_points[i]
        lat2, lon2 = trajectory_points[i + 1]
        total_distance += calculate_gps_distance(lat1, lon1, lat2, lon2)
    
    return total_distance


def calculate_route_distance(G, node1, node2) -> float:
    """
    Calcula distância seguindo a rede viária entre dois nós
    
    Args:
        G: Grafo da rede viária (OSMnx)
        node1: ID do nó de origem
        node2: ID do nó de destino
        
    Returns:
        Distância em km seguindo as ruas, ou None se não houver rota
    """
    if not MAP_MATCHING_AVAILABLE or G is None:
        return None
    
    try:
        # Encontrar caminho mais curto (peso = comprimento das arestas)
        route = ox.shortest_path(G, node1, node2, weight='length')
        
        if route is None:
            return None
        
        # Somar comprimento de todas as arestas do percurso
        total_distance_m = 0.0
        for i in range(len(route) - 1):
            # Pegar dados da aresta
            edge_data = G[route[i]][route[i + 1]]
            
            # OSMnx pode ter múltiplas arestas entre nós, pegar a primeira
            if isinstance(edge_data, dict):
                # Múltiplas arestas: pegar a de menor comprimento
                edge_lengths = [data.get('length', 0) for data in edge_data.values()]
                edge_length = min(edge_lengths) if edge_lengths else 0
            else:
                edge_length = edge_data.get('length', 0)
            
            total_distance_m += edge_length
        
        # Converter metros para km
        return total_distance_m / 1000.0
        
    except Exception as e:
        # Rota não encontrada ou erro no cálculo
        return None


def calculate_trajectory_distance_with_routing(trajectory_points: list, G) -> tuple:
    """
    Calcula distância total seguindo a rede viária (como SUMO faz)
    
    Args:
        trajectory_points: Lista de [lat, lon]
        G: Grafo da rede viária (OSMnx)
        
    Returns:
        Tupla (distância_total_km, sucesso_count, fallback_count)
        - distância_total_km: Distância total em km
        - sucesso_count: Número de segmentos com roteamento bem-sucedido
        - fallback_count: Número de segmentos que usaram Haversine (fallback)
    """
    if len(trajectory_points) < 2:
        return 0.0, 0, 0
    
    if not MAP_MATCHING_AVAILABLE or G is None:
        # Fallback para Haversine simples
        return calculate_trajectory_distance(trajectory_points), 0, len(trajectory_points) - 1
    
    total_distance = 0.0
    success_count = 0
    fallback_count = 0
    
    for i in range(len(trajectory_points) - 1):
        lat1, lon1 = trajectory_points[i]
        lat2, lon2 = trajectory_points[i + 1]
        
        try:
            # Snap pontos para nós mais próximos
            node1 = ox.nearest_nodes(G, lon1, lat1)
            node2 = ox.nearest_nodes(G, lon2, lat2)
            
            # Se os nós são iguais, distância = 0
            if node1 == node2:
                success_count += 1
                continue
            
            # Calcular distância seguindo a rota
            route_distance = calculate_route_distance(G, node1, node2)
            
            if route_distance is not None:
                total_distance += route_distance
                success_count += 1
            else:
                # Fallback: usar Haversine
                haversine_distance = calculate_gps_distance(lat1, lon1, lat2, lon2)
                total_distance += haversine_distance
                fallback_count += 1
                
        except Exception as e:
            # Erro ao fazer snap ou calcular rota: usar Haversine
            haversine_distance = calculate_gps_distance(lat1, lon1, lat2, lon2)
            total_distance += haversine_distance
            fallback_count += 1
    
    return total_distance, success_count, fallback_count


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


def process_sumo_csv(input_csv: str, consumo_fabricante: float = CONSUMO_FABRICANTE, row_step: int = ROW_STEP, offset_x: float = OFFSET_X, offset_y: float = OFFSET_Y, max_radius_km: float = MAX_RADIUS_KM) -> pd.DataFrame:
    """
    Processa CSV SUMO agregando por vehicle_id com offset determinístico
    
    Args:
        input_csv: Caminho do arquivo SUMO CSV
        consumo_fabricante: Consumo declarado pelo fabricante (km/l)
        row_step: Processar a cada N linhas (1=todas, 5=de 5 em 5, etc)
        offset_x: Deslocamento em graus de latitude
        offset_y: Deslocamento em graus de longitude
        max_radius_km: Raio máximo de deslocamento
        
    Returns:
        DataFrame com viagens agregadas
    """
    print("="*70)
    print("🚗 PROCESSAMENTO SUMO → E1 REGISTRY (OFFSET DETERMINÍSTICO)")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"🏭 Consumo fabricante: {consumo_fabricante} km/l")
    print(f"💰 Preço carbono: R$ {CARBON_PRICE}/ton")
    print(f"🔑 Offset X (latitude): {offset_x}° ({offset_x * 111.32:.2f} km)")
    print(f"🔑 Offset Y (longitude): {offset_y}° (varia com latitude)")
    print(f"⭕ Raio máximo: {max_radius_km} km")
    
    # Calcular distância do offset (aproximação no equador)
    offset_distance_approx = calculate_offset_distance(offset_x, offset_y, 0)
    print(f"📏 Distância do offset (aprox): {offset_distance_approx:.2f} km")
    
    if offset_distance_approx > max_radius_km:
        print(f"⚠️  AVISO: Offset será reduzido de {offset_distance_approx:.2f} km para {max_radius_km} km (raio máximo)")
    
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
    
    # Estatísticas de map matching e clipping
    total_points_processed = 0
    total_snaps_attempted = 0
    total_snaps_successful = 0
    total_snaps_rejected = 0
    total_offsets_clipped = 0
    
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
        
        # Distâncias em km (SUMO usa valores acumulados, pegar último valor)
        total_distance_km = group['distance'].iloc[-1] if len(group) > 0 else 0
        distance_city_km = group['distance_city'].iloc[-1] if len(group) > 0 else 0
        distance_highway_km = group['distance_highway'].iloc[-1] if len(group) > 0 else 0
        
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
        
        # ========== OFFSET DETERMINÍSTICO + MAP MATCHING ==========
        # ETAPA 1: Aplicar offset com clipping
        start_lat_offset, start_lon_offset, start_clipped, start_orig_dist, start_final_dist = apply_deterministic_offset(
            start_lat_orig, start_lon_orig, offset_x, offset_y, max_radius_km
        )
        end_lat_offset, end_lon_offset, end_clipped, end_orig_dist, end_final_dist = apply_deterministic_offset(
            end_lat_orig, end_lon_orig, offset_x, offset_y, max_radius_km
        )
        
        # Contar clippings
        if start_clipped:
            total_offsets_clipped += 1
        if end_clipped:
            total_offsets_clipped += 1
        
        # ETAPA 2: Map matching (snap to road)
        start_snapped = False
        end_snapped = False
        
        if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE:
            # IMPORTANTE: baixar malha viária do ponto COM OFFSET, não original
            G_start = get_road_network(start_lat_offset, start_lon_offset)
            if G_start is not None:
                start_lat_private, start_lon_private, start_snapped, _ = snap_to_nearest_road(
                    G_start, start_lat_offset, start_lon_offset, start_lat_orig, start_lon_orig
                )
            else:
                start_lat_private = start_lat_offset
                start_lon_private = start_lon_offset
            
            # IMPORTANTE: baixar malha viária do ponto COM OFFSET, não original
            G_end = get_road_network(end_lat_offset, end_lon_offset)
            if G_end is not None:
                end_lat_private, end_lon_private, end_snapped, _ = snap_to_nearest_road(
                    G_end, end_lat_offset, end_lon_offset, end_lat_orig, end_lon_orig
                )
            else:
                end_lat_private = end_lat_offset
                end_lon_private = end_lon_offset
        else:
            # Sem map matching: usar coordenadas com offset
            start_lat_private = start_lat_offset
            start_lon_private = start_lon_offset
            end_lat_private = end_lat_offset
            end_lon_private = end_lon_offset
        
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
            
            # Aplicar offset determinístico
            seg_lat_offset, seg_lon_offset, seg_clipped, seg_orig_dist, seg_final_dist = apply_deterministic_offset(
                seg_lat, seg_lon, offset_x, offset_y, max_radius_km
            )
            
            if seg_clipped:
                total_offsets_clipped += 1
            
            # Map matching
            if ENABLE_MAP_MATCHING and MAP_MATCHING_AVAILABLE:
                total_points_processed += 1
                # IMPORTANTE: baixar grafo em torno das coordenadas COM OFFSET, não originais
                G_seg = get_road_network(seg_lat_offset, seg_lon_offset)
                if G_seg is not None:
                    total_snaps_attempted += 1
                    seg_lat_priv, seg_lon_priv, snap_success, snap_rejected = snap_to_nearest_road(
                        G_seg, seg_lat_offset, seg_lon_offset, seg_lat, seg_lon
                    )
                    if snap_success:
                        total_snaps_successful += 1
                    if snap_rejected:
                        total_snaps_rejected += 1
                else:
                    seg_lat_priv = seg_lat_offset
                    seg_lon_priv = seg_lon_offset
            else:
                seg_lat_priv = seg_lat_offset
                seg_lon_priv = seg_lon_offset
            
            trajectory_points_orig.append([seg_lat, seg_lon])
            trajectory_points_priv.append([seg_lat_priv, seg_lon_priv])
            trajectory_times.append(seg_time.isoformat())
        
        # ========== CALCULAR DISTÂNCIAS DOS TRAJETOS ==========
        # Distância do trajeto original (soma das distâncias GPS entre pontos)
        trajectory_distance_orig = calculate_trajectory_distance(trajectory_points_orig)
        
        # Distância do trajeto com offset (soma das distâncias GPS entre pontos com offset)
        trajectory_distance_priv = calculate_trajectory_distance(trajectory_points_priv)
        
        # DEBUG: Verificar se todos os pontos são idênticos
        if trajectory_distance_priv == 0.0 and len(trajectory_points_priv) > 1:
            unique_points = set(tuple(p) for p in trajectory_points_priv)
            print(f"⚠️  {vin}: Distância do trajeto com offset = 0.0 km!")
            print(f"   Pontos únicos: {len(unique_points)} de {len(trajectory_points_priv)}")
            if len(unique_points) == 1:
                print(f"   Todos os pontos colapsaram para: {trajectory_points_priv[0]}")
            else:
                print(f"   Primeiros 3 pontos: {trajectory_points_priv[:3]}")
                print(f"   Últimos 3 pontos: {trajectory_points_priv[-3:]}")
        
        # Diferença de distância (pode ser positiva ou negativa)
        trajectory_distance_diff = trajectory_distance_priv - trajectory_distance_orig
        
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
            'num_points': len(trajectory_points_orig),
            'trajectory_distance_orig_km': trajectory_distance_orig,
            'trajectory_distance_priv_km': trajectory_distance_priv,
            'trajectory_distance_diff_km': trajectory_distance_diff
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
            'num_segments': len(group),
            'trajectory_distance_orig_km': trajectory_distance_orig,
            'trajectory_distance_priv_km': trajectory_distance_priv,
            'trajectory_distance_diff_km': trajectory_distance_diff
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
        
        # Mostrar offset determinístico
        print(f"\n   🔑 OFFSET DETERMINÍSTICO (x={offset_x}°, y={offset_y}°, max={max_radius_km}km):")
        print(f"   📍 Start Original:  ({start_lat_orig:.6f}, {start_lon_orig:.6f})")
        
        clip_status_start = f"⚠️  CLIPPED {start_orig_dist:.2f}→{start_final_dist:.2f} km" if start_clipped else f"✓ {start_final_dist:.2f} km"
        snap_status_start = "✓ MAP MATCHED" if start_snapped else "⚠ SEM MAP MATCHING"
        print(f"   🔒 Start Protegido: ({start_lat_private:.6f}, {start_lon_private:.6f}) {clip_status_start} | {snap_status_start}")
        print(f"   📏 Deslocamento final: {start_displacement_km*1000:.1f} metros")
        
        print(f"   📍 End Original:    ({end_lat_orig:.6f}, {end_lon_orig:.6f})")
        
        clip_status_end = f"⚠️  CLIPPED {end_orig_dist:.2f}→{end_final_dist:.2f} km" if end_clipped else f"✓ {end_final_dist:.2f} km"
        snap_status_end = "✓ MAP MATCHED" if end_snapped else "⚠ SEM MAP MATCHING"
        print(f"   🔒 End Protegido:   ({end_lat_private:.6f}, {end_lon_private:.6f}) {clip_status_end} | {snap_status_end}")
        print(f"   📏 Deslocamento final: {end_displacement_km*1000:.1f} metros")
        
        # Mostrar diferença de distância do trajeto
        print(f"\n   📐 ANÁLISE DE DISTÂNCIA DO TRAJETO:")
        print(f"   📍 Trajeto original: {trajectory_distance_orig:.3f} km")
        print(f"   🔒 Trajeto com offset: {trajectory_distance_priv:.3f} km")
        diff_sign = "+" if trajectory_distance_diff >= 0 else ""
        
        # Calcular percentual (evitar divisão por zero)
        if trajectory_distance_orig > 0:
            percent_diff = trajectory_distance_diff / trajectory_distance_orig * 100
            print(f"   📊 Diferença: {diff_sign}{trajectory_distance_diff:.3f} km ({diff_sign}{percent_diff:.1f}%)")
        else:
            print(f"   📊 Diferença: {diff_sign}{trajectory_distance_diff:.3f} km (N/A - distância original é zero)")
            if trajectory_distance_priv == 0:
                print(f"   ⚠️  ATENÇÃO: Ambas distâncias são zero - possível problema no roteamento!")
    
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
    
    # Estatísticas de Clipping
    if total_offsets_clipped > 0:
        print(f"\n⭕ CLIPPING DE RAIO:")
        print(f"   Offsets aplicados: {total_points_processed + 2*len(df_result):,}")  # +2 por start/end
        print(f"   Offsets reduzidos (clipped): {total_offsets_clipped:,} ({total_offsets_clipped/(total_points_processed + 2*len(df_result))*100:.1f}%)")
        print(f"   ⚠️  AVISO: {total_offsets_clipped} pontos ultrapassaram o raio de {max_radius_km} km e foram ajustados")
    
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
            print(f"   Apenas offset (sem snap): {total_points_processed - total_snaps_successful:,} ({(total_points_processed - total_snaps_successful)/total_points_processed*100:.1f}%)")
    
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


def save_distance_analysis_csv(df: pd.DataFrame, output_csv: str):
    """
    Salva CSV com análise de diferença de distância entre trajeto original e com offset
    
    Args:
        df: DataFrame processado com dados agregados
        output_csv: Caminho do arquivo CSV de saída
    """
    # Selecionar colunas relevantes para análise
    analysis_df = df[[
        'vin',
        'model',
        'total_distance_km',
        'trajectory_distance_orig_km',
        'trajectory_distance_priv_km',
        'trajectory_distance_diff_km',
        'num_segments',
        'start_lat_orig',
        'start_lon_orig',
        'end_lat_orig',
        'end_lon_orig',
        'start_lat_private',
        'start_lon_private',
        'end_lat_private',
        'end_lon_private'
    ]].copy()
    
    # Adicionar coluna de percentual de diferença
    analysis_df['trajectory_distance_diff_percent'] = (
        analysis_df['trajectory_distance_diff_km'] / analysis_df['trajectory_distance_orig_km'] * 100
    )
    
    # Renomear colunas para clareza
    analysis_df.columns = [
        'VIN',
        'Modelo',
        'Distancia_SUMO_km',
        'Distancia_Trajeto_Original_km',
        'Distancia_Trajeto_com_Offset_km',
        'Diferenca_Distancia_km',
        'Num_Pontos',
        'Start_Lat_Original',
        'Start_Lon_Original',
        'End_Lat_Original',
        'End_Lon_Original',
        'Start_Lat_com_Offset',
        'Start_Lon_com_Offset',
        'End_Lat_com_Offset',
        'End_Lon_com_Offset',
        'Diferenca_Distancia_Percentual'
    ]
    
    # Salvar CSV
    analysis_df.to_csv(output_csv, index=False, float_format='%.4f')
    print(f"💾 Análise de distâncias salva em: {output_csv}")
    
    # Mostrar estatísticas
    print(f"\n📊 ESTATÍSTICAS DE DIFERENÇA DE DISTÂNCIA:")
    print(f"   Diferença média: {analysis_df['Diferenca_Distancia_km'].mean():+.3f} km ({analysis_df['Diferenca_Distancia_Percentual'].mean():+.2f}%)")
    print(f"   Diferença máxima: {analysis_df['Diferenca_Distancia_km'].max():+.3f} km")
    print(f"   Diferença mínima: {analysis_df['Diferenca_Distancia_km'].min():+.3f} km")
    print(f"   Desvio padrão: {analysis_df['Diferenca_Distancia_km'].std():.3f} km")


def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("Uso: python3 process_sumo_csv.py <input.csv> [output.csv] [consumo_fabricante] [row_step] [offset_x] [offset_y] [max_radius_km]")
        print("\nExemplos:")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv ../data/trips_sumo.csv 12.0")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv ../data/trips_sumo.csv 12.0 1 0.02 0.02 2.0")
        print("\nParâmetros:")
        print("  offset_x: Deslocamento em graus de latitude (padrão: 0.01)")
        print("  offset_y: Deslocamento em graus de longitude (padrão: 0.01)")
        print("  max_radius_km: Raio máximo de deslocamento em km (padrão: 2.0)")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else '../data/trips_sumo_processed.csv'
    consumo_fab = float(sys.argv[3]) if len(sys.argv) > 3 else CONSUMO_FABRICANTE
    step = int(sys.argv[4]) if len(sys.argv) > 4 else ROW_STEP
    offset_x = float(sys.argv[5]) if len(sys.argv) > 5 else OFFSET_X
    offset_y = float(sys.argv[6]) if len(sys.argv) > 6 else OFFSET_Y
    max_radius = float(sys.argv[7]) if len(sys.argv) > 7 else MAX_RADIUS_KM
    
    # Processar
    df_trips, trajectories = process_sumo_csv(input_file, consumo_fab, step, offset_x, offset_y, max_radius)
    
    # Salvar CSV (dados agregados)
    save_to_csv(df_trips, output_file)
    
    # Salvar JSON (trajetos completos para visualização)
    json_file = output_file.replace('.csv', '_trajectories.json')
    save_trajectories_json(trajectories, json_file)
    
    # Salvar CSV de análise de distâncias
    analysis_file = output_file.replace('.csv', '_distance_analysis.csv')
    save_distance_analysis_csv(df_trips, analysis_file)


if __name__ == "__main__":
    main()
