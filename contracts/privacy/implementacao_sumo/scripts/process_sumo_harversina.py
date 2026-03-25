#!/usr/bin/env python3
"""
Script para processar dados SUMO com Laplace Noise + Haversine (OPÇÃO 1)

DIFERENÇA vs process_sumo_csv.py:
- process_sumo_csv.py: Usa routing OSMnx para distância com ruído (pode colapsar ou criar atalhos)
- process_sumo_harversina.py: Usa Haversine puro para distância com ruído (mostra efeito real)

Este script implementa OPÇÃO 1: Haversine direto SEM map matching para distância
- Map matching usado APENAS para armazenamento (privacidade nas coordenadas salvas)
- Distância calculada com Haversine nos pontos GPS com ruído (SEM snap)
- Mostra o verdadeiro efeito zig-zag do ruído Laplace
- RESULTADO: Distância com ruído reflete o deslocamento real causado pelo Laplace
           (esperado: 2-5 km para trajetos de ~0.3 km com ε=0.5)
- VANTAGENS: Rápido (sem API OSM), offline, mostra impacto real do ruído na utilidade

Autor: Victor
Data: 2026-03-08
"""

import pandas as pd
import numpy as np
import sys
import json
import os
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
ROW_STEP = 1                # Processar a cada N linhas (1=todas, 5=de 5 em 5, etc)

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


def filter_close_points(trajectory_points: list, min_distance_m: float = 10.0) -> tuple:
    """
    Filtra pontos muito próximos para evitar colapso no roteamento
    
    Args:
        trajectory_points: Lista de [lat, lon]
        min_distance_m: Distância mínima entre pontos em metros
        
    Returns:
        Tupla (pontos_filtrados, indices_mantidos)
    """
    if len(trajectory_points) < 2:
        return trajectory_points, list(range(len(trajectory_points)))
    
    filtered_points = [trajectory_points[0]]  # Sempre manter o primeiro
    kept_indices = [0]
    
    for i in range(1, len(trajectory_points)):
        lat_prev, lon_prev = filtered_points[-1]
        lat_curr, lon_curr = trajectory_points[i]
        
        # Calcular distância aproximada em metros
        dlat = (lat_curr - lat_prev) * 111320
        dlon = (lon_curr - lon_prev) * 111320 * np.cos(np.radians(lat_prev))
        distance_m = np.sqrt(dlat**2 + dlon**2)
        
        # Manter apenas se distância >= min_distance_m
        if distance_m >= min_distance_m:
            filtered_points.append(trajectory_points[i])
            kept_indices.append(i)
    
    # SEMPRE manter o último ponto (mesmo que próximo do penúltimo)
    if kept_indices[-1] != len(trajectory_points) - 1:
        filtered_points.append(trajectory_points[-1])
        kept_indices.append(len(trajectory_points) - 1)
    
    return filtered_points, kept_indices


def calculate_trajectory_distance_with_routing(trajectory_points: list, G, min_distance_m: float = 10.0) -> tuple:
    """
    Calcula distância total seguindo a rede viária (como SUMO faz)
    Filtra pontos muito próximos para evitar colapso no roteamento
    
    Args:
        trajectory_points: Lista de [lat, lon]
        G: Grafo da rede viária (OSMnx)
        min_distance_m: Distância mínima entre pontos para roteamento (metros)
        
    Returns:
        Tupla (distância_total_km, sucesso_count, fallback_count, pontos_filtrados)
        - distância_total_km: Distância total em km
        - sucesso_count: Número de segmentos com roteamento bem-sucedido
        - fallback_count: Número de segmentos que usaram Haversine (fallback)
        - pontos_filtrados: Número de pontos após filtro
    """
    if len(trajectory_points) < 2:
        return 0.0, 0, 0, 0
    
    if not MAP_MATCHING_AVAILABLE or G is None:
        # Fallback para Haversine simples
        return calculate_trajectory_distance(trajectory_points), 0, len(trajectory_points) - 1, len(trajectory_points)
    
    # Filtrar pontos muito próximos
    filtered_points, kept_indices = filter_close_points(trajectory_points, min_distance_m)
    
    total_distance = 0.0
    success_count = 0
    fallback_count = 0
    
    for i in range(len(filtered_points) - 1):
        lat1, lon1 = filtered_points[i]
        lat2, lon2 = filtered_points[i + 1]
        
        try:
            # Snap pontos para nós mais próximos
            node1 = ox.nearest_nodes(G, lon1, lat1)
            node2 = ox.nearest_nodes(G, lon2, lat2)
            
            # Se os nós são iguais, usar Haversine (pequena distância)
            if node1 == node2:
                haversine_distance = calculate_gps_distance(lat1, lon1, lat2, lon2)
                total_distance += haversine_distance
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
    
    return total_distance, success_count, fallback_count, len(filtered_points)


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
    print("🚗 PROCESSAMENTO SUMO → E1 REGISTRY (OPÇÃO 1: Haversine)")
    print("="*70)
    print(f"📄 Entrada: {input_csv}")
    print(f"🏭 Consumo fabricante: {consumo_fabricante} km/l")
    print(f"💰 Preço carbono: R$ {CARBON_PRICE}/ton")
    print(f"🔐 Epsilon (ε): {EPSILON}")
    print(f"📏 Método distância com ruído: Haversine direto (sem map matching)")
    
    if row_step > 1:
        print(f"⏭️  Row stepping: Processando 1 a cada {row_step} linhas")
    else:
        print(f"📊 Row stepping: Processando todas as linhas")
    
    if MAP_MATCHING_AVAILABLE and ENABLE_MAP_MATCHING:
        print(f"🗺️  Map matching: ATIVADO apenas para armazenamento (raio {SEARCH_RADIUS}m)")
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
        trajectory_points_noisy = []  # Ruído SEM map matching (para cálculo de distância)
        trajectory_points_priv = []   # Ruído COM map matching (para armazenamento)
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
            
            # Guardar ponto com ruído (SEM map matching) para cálculo de distância preciso
            trajectory_points_noisy.append([seg_lat_noisy, seg_lon_noisy])
            
            # Map matching (apenas para privacidade, não afeta distância)
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
        
        # ========== CALCULAR DISTÂNCIAS DOS TRAJETOS ==========
        # OPÇÃO 1: Haversine direto (linha reta no globo) para mostrar efeito real do ruído
        
        if MAP_MATCHING_AVAILABLE:
            # Obter grafo que cubra toda a trajetória original
            lats_orig = [p[0] for p in trajectory_points_orig]
            lons_orig = [p[1] for p in trajectory_points_orig]
            center_lat_orig = np.mean(lats_orig)
            center_lon_orig = np.mean(lons_orig)
            G_orig = get_road_network(center_lat_orig, center_lon_orig, radius=SEARCH_RADIUS * 2)
            
            # Calcular distância original com roteamento (para comparação justa com SUMO)
            trajectory_distance_orig, orig_success, orig_fallback, orig_filtered = calculate_trajectory_distance_with_routing(
                trajectory_points_orig, G_orig, min_distance_m=10.0
            )
            
            # OPÇÃO 1: Haversine DIRETO nos pontos com ruído (SEM map matching)
            # Usa pontos GPS com ruído puro para mostrar verdadeiro efeito do Laplace
            trajectory_distance_priv = calculate_trajectory_distance(trajectory_points_noisy)
            
            # Mostrar estatísticas
            if orig_fallback > 0 or orig_filtered != len(trajectory_points_orig):
                print(f"  🗺️  {vin}: Cálculo de Distância (OPÇÃO 1: Haversine Direto)")
                print(f"      Original: {len(trajectory_points_orig)} pontos → {orig_filtered} filtrados → {orig_success} rotas OSMnx, {orig_fallback} fallbacks")
                print(f"      Ruído:    {len(trajectory_points_noisy)} pontos → Haversine direto (sem map matching)")
        else:
            # Fallback: usar Haversine para ambos se OSMnx não disponível
            trajectory_distance_orig = calculate_trajectory_distance(trajectory_points_orig)
            trajectory_distance_priv = calculate_trajectory_distance(trajectory_points_noisy)
        
        # DEBUG: Verificar se map matching colapsou pontos (não afeta distância)
        if len(trajectory_points_priv) > 1:
            unique_points_priv = set(tuple(p) for p in trajectory_points_priv)
            if len(unique_points_priv) == 1:
                print(f"  ⚠️  {vin}: Map matching colapsou pontos (NÃO afeta distância)")
                print(f"      Todos os {len(trajectory_points_priv)} pontos privados → 1 único: {trajectory_points_priv[0]}")
        
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
        
        # Mostrar diferença de distância do trajeto
        print(f"\n   📐 ANÁLISE DE DISTÂNCIA DO TRAJETO:")
        print(f"   📍 Trajeto original: {trajectory_distance_orig:.3f} km")
        print(f"   🔒 Trajeto com ruído: {trajectory_distance_priv:.3f} km")
        diff_sign = "+" if trajectory_distance_diff >= 0 else ""
        
        # Calcular percentual (evitar divisão por zero)
        if trajectory_distance_orig > 0:
            percent_diff = trajectory_distance_diff / trajectory_distance_orig * 100
            print(f"   📊 Diferença: {diff_sign}{trajectory_distance_diff:.3f} km ({diff_sign}{percent_diff:.1f}%)")
        else:
            print(f"   📊 Diferença: {diff_sign}{trajectory_distance_diff:.3f} km (N/A - distância original é zero)")
    
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


def save_distance_analysis_csv(df: pd.DataFrame, output_csv: str):
    """
    Salva CSV com análise de diferença de distância entre trajeto original e com ruído
    
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
        'Distancia_Trajeto_com_Ruido_km',
        'Diferenca_Distancia_km',
        'Num_Pontos',
        'Start_Lat_Original',
        'Start_Lon_Original',
        'End_Lat_Original',
        'End_Lon_Original',
        'Start_Lat_com_Ruido',
        'Start_Lon_com_Ruido',
        'End_Lat_com_Ruido',
        'End_Lon_com_Ruido',
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
        print("Uso: python3 process_sumo_csv.py <input.csv> [output.csv] [consumo_fabricante] [row_step]")
        print("\nExemplo:")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv trips_sumo.csv 12.0")
        print("  python3 process_sumo_csv.py ../data/carro_1000.csv trips_sumo.csv 12.0 5  # Processar de 5 em 5")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Obter diretório do script para referência
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Processar output_file
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        # Se for apenas um nome de arquivo (sem caminho), salvar em ../data/
        if not os.path.dirname(output_file):
            output_file = os.path.join(data_dir, output_file)
    else:
        # Padrão: salvar em ../data/
        output_file = os.path.join(data_dir, 'trips_laplace_processed.csv')
    
    consumo_fab = float(sys.argv[3]) if len(sys.argv) > 3 else CONSUMO_FABRICANTE
    step = int(sys.argv[4]) if len(sys.argv) > 4 else ROW_STEP
    
    # Processar
    df_trips, trajectories = process_sumo_csv(input_file, consumo_fab, step)
    
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
