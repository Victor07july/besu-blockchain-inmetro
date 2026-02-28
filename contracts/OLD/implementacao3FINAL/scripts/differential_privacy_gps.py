#!/usr/bin/env python3
"""
Implementação de Privacidade Diferencial para Coordenadas GPS com Map Matching
Garante que coordenadas protegidas permaneçam em vias trafegáveis

Processo:
1. Preparação do ambiente e extração do contexto geográfico (osmnx)
2. Geração e aplicação de ruído estatístico (diffprivlib/PyDP)
3. Map Matching - vínculo com vias reais
4. Validação e exportação dos dados

Autor: Victor
Data: 2026-02-09
"""

import pandas as pd
import numpy as np
import osmnx as ox
import networkx as nx
from typing import Tuple, Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Bibliotecas de privacidade diferencial
try:
    from diffprivlib.mechanisms import Laplace
    DP_LIB = "diffprivlib"
except ImportError:
    try:
        import pydp as dp
        from pydp.algorithms.laplacian import BoundedMean
        DP_LIB = "pydp"
    except ImportError:
        DP_LIB = None
        print("⚠️  Nenhuma biblioteca de DP encontrada. Usando implementação manual.")

# Biblioteca de elevação (SRTM - NASA)
try:
    import srtm
    ELEVATION_DATA = srtm.get_data()
    print("✓ SRTM carregado (dados de elevação NASA)")
except ImportError:
    ELEVATION_DATA = None
    print("⚠️  Biblioteca srtm não encontrada. Execute: pip install srtm.py")
except Exception as e:
    ELEVATION_DATA = None
    print(f"⚠️  Erro ao carregar SRTM: {e}")

# Configurações
EPSILON = 0.5  # Quanto menor, maior a privacidade (valores típicos: 0.1 a 1.0)
SEARCH_RADIUS = 1000  # Raio de busca em metros para o grafo de ruas
CACHE_GRAPHS = {}  # Cache de grafos baixados


class DifferentialPrivacyGPS:
    """
    Implementa privacidade diferencial em coordenadas GPS com garantia de 
    que o resultado permanece em vias trafegáveis
    """
    
    def __init__(self, epsilon: float = EPSILON, search_radius: int = SEARCH_RADIUS):
        """
        Inicializa o processador de privacidade diferencial
        
        Args:
            epsilon: Parâmetro de privacidade (menor = mais privado)
            search_radius: Raio de busca para o grafo de ruas (metros)
        """
        self.epsilon = epsilon
        self.search_radius = search_radius
        self.graphs_cache = {}
        self.elevation_cache = {}  # Cache para elevações
        
    def parse_coordinates(self, coord_str: str) -> Tuple[float, float]:
        """
        Converte string de coordenadas para tupla (lat, lon)
        
        Args:
            coord_str: String no formato "latitude, longitude"
            
        Returns:
            Tupla (latitude, longitude)
        """
        try:
            parts = coord_str.replace('"', '').replace("'", '').strip().split(',')
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return lat, lon
        except Exception as e:
            raise ValueError(f"Erro ao parsear coordenadas '{coord_str}': {e}")
    
    def get_road_network(self, lat: float, lon: float) -> nx.MultiDiGraph:
        """
        ETAPA 1: Preparação do ambiente e extração do contexto geográfico
        
        Baixa dinamicamente a malha viária ao redor das coordenadas usando osmnx.
        Utiliza cache para evitar downloads repetidos da mesma região.
        
        Args:
            lat: Latitude do ponto central
            lon: Longitude do ponto central
            
        Returns:
            Grafo da rede viária (NetworkX MultiDiGraph)
        """
        # Criar chave de cache baseada em região aproximada (para reutilizar grafos)
        cache_key = (round(lat, 3), round(lon, 3))
        
        if cache_key in self.graphs_cache:
            return self.graphs_cache[cache_key]
        
        try:
            print(f"🗺️  Baixando malha viária ao redor de ({lat:.6f}, {lon:.6f})...")
            
            # Baixar grafo de ruas driveable (vias trafegáveis)
            G = ox.graph_from_point(
                (lat, lon),
                dist=self.search_radius,
                network_type='drive',  # Apenas vias trafegáveis por veículos
                simplify=True
            )
            
            self.graphs_cache[cache_key] = G
            print(f"✓ Grafo carregado: {len(G.nodes)} nós, {len(G.edges)} arestas")
            
            return G
            
        except Exception as e:
            print(f"❌ Erro ao baixar grafo: {e}")
            raise
    
    def apply_laplace_noise(self, value: float, epsilon: float, 
                           sensitivity: float = 1.0) -> float:
        """
        ETAPA 2: Geração e aplicação do ruído estatístico
        
        Aplica mecanismo de Laplace para privacidade diferencial.
        O ruído é calibrado com base no parâmetro epsilon e na sensibilidade.
        
        Args:
            value: Valor original (coordenada)
            epsilon: Parâmetro de privacidade
            sensitivity: Sensibilidade da consulta (padrão: 1.0)
            
        Returns:
            Valor com ruído aplicado
        """
        if DP_LIB == "diffprivlib":
            # Usar diffprivlib
            mech = Laplace(epsilon=epsilon, sensitivity=sensitivity)
            return mech.randomise(value)
            
        elif DP_LIB == "pydp":
            # Usar PyDP - implementação do Google
            # PyDP requer bounds, então usamos uma aproximação
            scale = sensitivity / epsilon
            noise = np.random.laplace(0, scale)
            return value + noise
            
        else:
            # Implementação manual do Laplace
            scale = sensitivity / epsilon
            noise = np.random.laplace(0, scale)
            return value + noise
    
    def add_differential_privacy(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Adiciona ruído diferencial às coordenadas
        
        Args:
            lat: Latitude original
            lon: Longitude original
            
        Returns:
            Tupla (lat_noisy, lon_noisy) com ruído aplicado
        """
        # Sensitivity baseada na escala de graus lat/lon
        # ~0.00001 grau ≈ 1.1 metros na linha do equador
        # Sensitivity de 0.001 grau ≈ 111 metros
        lat_sensitivity = 0.001  # Aproximadamente 111 metros
        lon_sensitivity = 0.001  # Aproximadamente 111 metros (varia com latitude)
        
        lat_noisy = self.apply_laplace_noise(lat, self.epsilon, lat_sensitivity)
        lon_noisy = self.apply_laplace_noise(lon, self.epsilon, lon_sensitivity)
        
        return lat_noisy, lon_noisy
    
    def snap_to_nearest_road(self, G: nx.MultiDiGraph, 
                            lat: float, lon: float) -> Tuple[float, float, int]:
        """
        ETAPA 3: Map Matching - Processamento de vínculo
        
        Projeta a coordenada ruidosa para a via trafegável mais próxima.
        "Puxa" o ponto para a superfície asfáltica dentro do grafo.
        
        Args:
            G: Grafo da rede viária
            lat: Latitude (possivelmente com ruído)
            lon: Longitude (possivelmente com ruído)
            
        Returns:
            Tupla (lat_snapped, lon_snapped, node_id)
        """
        try:
            # Projetar o grafo para facilitar cálculos de distância
            # Isso evita a necessidade de scikit-learn em alguns casos
            try:
                G_proj = ox.project_graph(G)
                # Encontrar o nó mais próximo no grafo projetado
                nearest_node = ox.distance.nearest_nodes(G_proj, lon, lat)
            except:
                # Fallback: usar grafo não projetado
                # (requer scikit-learn instalado)
                nearest_node = ox.distance.nearest_nodes(G, lon, lat)
            
            # Obter coordenadas do nó (sempre do grafo original)
            node_data = G.nodes[nearest_node]
            lat_snapped = node_data['y']
            lon_snapped = node_data['x']
            
            return lat_snapped, lon_snapped, nearest_node
            
        except Exception as e:
            print(f"⚠️  Erro no map matching: {e}")
            # Em caso de falha, retornar coordenadas originais
            return lat, lon, -1
    
    def calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """
        Calcula distância entre dois pontos usando fórmula de Haversine
        
        Args:
            lat1, lon1: Coordenadas do ponto 1
            lat2, lon2: Coordenadas do ponto 2
            
        Returns:
            Distância em quilômetros
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0  # Raio da Terra em km
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        return distance
    
    def get_elevation(self, lat: float, lon: float) -> int:
        """
        Obtém elevação em metros usando SRTM (NASA)
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            Elevação em metros (int), ou 0 se não disponível
        """
        if ELEVATION_DATA is None:
            return 0
        
        # Cache com precisão de 4 casas decimais (~11m)
        cache_key = (round(lat, 4), round(lon, 4))
        
        if cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]
        
        try:
            elevation = ELEVATION_DATA.get_elevation(lat, lon)
            elevation_int = int(elevation) if elevation is not None else 0
            self.elevation_cache[cache_key] = elevation_int
            return elevation_int
        except Exception as e:
            print(f"⚠️  Erro ao obter elevação para ({lat}, {lon}): {e}")
            return 0
    
    def process_coordinates(self, lat_orig: float, lon_orig: float) -> Dict:
        """
        Pipeline completo de processamento com privacidade diferencial
        
        Args:
            lat_orig: Latitude original
            lon_orig: Longitude original
            
        Returns:
            Dicionário com coordenadas originais, ruidosas, snapped e elevações
        """
        # Obter elevação ANTES do DP
        elevation_original = self.get_elevation(lat_orig, lon_orig)
        
        # ETAPA 1: Baixar malha viária
        G = self.get_road_network(lat_orig, lon_orig)
        
        # ETAPA 2: Aplicar ruído diferencial
        lat_noisy, lon_noisy = self.add_differential_privacy(lat_orig, lon_orig)
        
        # ETAPA 3: Map matching - snap para via trafegável
        lat_snapped, lon_snapped, node_id = self.snap_to_nearest_road(
            G, lat_noisy, lon_noisy
        )
        
        # Obter elevação DEPOIS do DP (coordenada privada)
        elevation_private = self.get_elevation(lat_snapped, lon_snapped)
        
        # ETAPA 4: Validação - calcular deslocamento
        displacement = self.calculate_distance(
            lat_orig, lon_orig, lat_snapped, lon_snapped
        ) * 1000  # Converter para metros
        
        return {
            'lat_original': lat_orig,
            'lon_original': lon_orig,
            'lat_noisy': lat_noisy,
            'lon_noisy': lon_noisy,
            'lat_private': lat_snapped,  # Coordenada final protegida
            'lon_private': lon_snapped,
            'node_id': node_id,
            'displacement_meters': displacement,
            'elevation_original': elevation_original,
            'elevation_private': elevation_private
        }
    
    def process_trip(self, start_coord: str, end_coord: str) -> Dict:
        """
        Processa uma viagem completa (início e fim)
        
        Args:
            start_coord: Coordenada inicial como string "lat, lon"
            end_coord: Coordenada final como string "lat, lon"
            
        Returns:
            Dicionário com coordenadas processadas de início e fim
        """
        # Parse das coordenadas
        start_lat, start_lon = self.parse_coordinates(start_coord)
        end_lat, end_lon = self.parse_coordinates(end_coord)
        
        print(f"\n🚗 Processando viagem:")
        print(f"   Origem: ({start_lat:.6f}, {start_lon:.6f})")
        print(f"   Destino: ({end_lat:.6f}, {end_lon:.6f})")
        
        # Processar coordenadas de início
        print("\n📍 Processando coordenada de início...")
        start_result = self.process_coordinates(start_lat, start_lon)
        
        # Processar coordenadas de fim
        print("\n📍 Processando coordenada de destino...")
        end_result = self.process_coordinates(end_lat, end_lon)
        
        # Calcular distância da viagem (usando coordenadas protegidas)
        trip_distance = self.calculate_distance(
            start_result['lat_private'], start_result['lon_private'],
            end_result['lat_private'], end_result['lon_private']
        )
        
        print(f"\n✓ Viagem processada:")
        print(f"   Deslocamento início: {start_result['displacement_meters']:.1f}m")
        print(f"   Deslocamento fim: {end_result['displacement_meters']:.1f}m")
        print(f"   Distância viagem (privada): {trip_distance:.3f}km")
        print(f"   Elevação início: {start_result['elevation_original']}m → {start_result['elevation_private']}m")
        print(f"   Elevação fim: {end_result['elevation_original']}m → {end_result['elevation_private']}m")
        
        return {
            'start': start_result,
            'end': end_result,
            'trip_distance_km': trip_distance
        }


def process_csv_with_dp(input_csv: str, output_csv: str, 
                       epsilon: float = EPSILON,
                       sample_size: Optional[int] = None):
    """
    Processa arquivo CSV completo aplicando privacidade diferencial
    
    Args:
        input_csv: Caminho do CSV de entrada
        output_csv: Caminho do CSV de saída
        epsilon: Parâmetro de privacidade diferencial
        sample_size: Número de linhas a processar (None = todas)
    """
    print("="*70)
    print("🔒 PROCESSAMENTO DE PRIVACIDADE DIFERENCIAL GPS")
    print("="*70)
    print(f"📄 Arquivo de entrada: {input_csv}")
    print(f"📄 Arquivo de saída: {output_csv}")
    print(f"🔐 Epsilon (ε): {epsilon}")
    print(f"📏 Raio de busca: {SEARCH_RADIUS}m")
    print("="*70)
    
    # Carregar dados
    print("\n📊 Carregando dados...")
    df = pd.read_csv(input_csv)
    
    if sample_size:
        df = df.head(sample_size)
        print(f"   Processando amostra: {len(df)} viagens")
    else:
        print(f"   Total de viagens: {len(df)}")
    
    # Inicializar processador
    dp_processor = DifferentialPrivacyGPS(epsilon=epsilon, search_radius=SEARCH_RADIUS)
    
    # Preparar novas colunas
    results = []
    
    print("\n🔄 Iniciando processamento...")
    print("-" * 70)
    
    for idx, row in df.iterrows():
        print(f"\n[{idx+1}/{len(df)}] VIN: {row['VIN']}")
        
        try:
            # Processar viagem
            trip_result = dp_processor.process_trip(
                row['start_location'],
                row['end_location']
            )
            
            # Adicionar resultados à linha
            result_row = row.to_dict()
            
            # Coordenadas de início (privadas)
            result_row['start_lat_private'] = trip_result['start']['lat_private']
            result_row['start_lon_private'] = trip_result['start']['lon_private']
            result_row['start_displacement_m'] = trip_result['start']['displacement_meters']
            result_row['start_elevation_original'] = trip_result['start']['elevation_original']
            result_row['start_elevation_private'] = trip_result['start']['elevation_private']
            
            # Coordenadas de fim (privadas)
            result_row['end_lat_private'] = trip_result['end']['lat_private']
            result_row['end_lon_private'] = trip_result['end']['lon_private']
            result_row['end_displacement_m'] = trip_result['end']['displacement_meters']
            result_row['end_elevation_original'] = trip_result['end']['elevation_original']
            result_row['end_elevation_private'] = trip_result['end']['elevation_private']
            
            # Distância calculada (privada)
            result_row['gps_distance_private_km'] = trip_result['trip_distance_km']
            
            # Metadados
            result_row['dp_epsilon'] = epsilon
            result_row['dp_processed'] = True
            
            results.append(result_row)
            
        except Exception as e:
            print(f"❌ Erro ao processar linha {idx}: {e}")
            # Adicionar linha original sem modificações
            result_row = row.to_dict()
            result_row['dp_processed'] = False
            result_row['dp_error'] = str(e)
            results.append(result_row)
    
    # Criar DataFrame final
    df_result = pd.DataFrame(results)
    
    # ETAPA 4: Validação e exportação
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS DE PROCESSAMENTO")
    print("="*70)
    
    if 'start_displacement_m' in df_result.columns:
        print(f"Deslocamento médio (início): {df_result['start_displacement_m'].mean():.1f}m")
        print(f"Deslocamento máximo (início): {df_result['start_displacement_m'].max():.1f}m")
        print(f"Deslocamento médio (fim): {df_result['end_displacement_m'].mean():.1f}m")
        print(f"Deslocamento máximo (fim): {df_result['end_displacement_m'].max():.1f}m")
    
    processed_count = df_result['dp_processed'].sum()
    print(f"\n✓ Viagens processadas com sucesso: {processed_count}/{len(df)}")
    
    # Salvar resultado
    df_result.to_csv(output_csv, index=False)
    print(f"\n💾 Dados salvos em: {output_csv}")
    print("="*70)
    
    return df_result


def main():
    """Função principal para teste do script"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python differential_privacy_gps.py <arquivo.csv> [epsilon] [num_linhas]")
        print("\nExemplo:")
        print("  python differential_privacy_gps.py dados.csv 0.5 10")
        sys.exit(1)
    
    input_file = sys.argv[1]
    epsilon = float(sys.argv[2]) if len(sys.argv) > 2 else EPSILON
    sample_size = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    output_file = input_file.replace('.csv', '_private.csv')
    
    process_csv_with_dp(input_file, output_file, epsilon, sample_size)


if __name__ == "__main__":
    main()
