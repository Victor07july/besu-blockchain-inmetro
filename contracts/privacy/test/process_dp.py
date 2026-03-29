#!/usr/bin/env python3
"""
Processamento de GPS com Privacidade Diferencial + Map-matching (OSMnx)
Entrada: CSV (o formato do anexo).
Saída: CSV com coordenadas ruidosas e "snapped" para a via e distância GPS recalculada.

Uso:
  python process_gps_dp.py --input dados.csv --output dados_dp.csv --epsilon 0.5 --radius 1000

Dependências: see requirements.txt
"""

import argparse
import os
import math
import json
from typing import Tuple, Dict

import pandas as pd
import numpy as np
import osmnx as ox
from shapely.geometry import Point, LineString
from shapely.ops import nearest_points
import networkx as nx

ox.settings.use_cache = True
ox.settings.log_console = False


def parse_coord(coord_str: str) -> Tuple[float, float]:
    # coord_str like "-5.8431992, -35.1977242"
    parts = coord_str.replace('"', '').split(',')
    lat = float(parts[0].strip())
    lon = float(parts[1].strip())
    return lat, lon


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    R = 6371.0
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dlambda = math.radians(b_lon - a_lon)
    x = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


class GraphCache:
    def __init__(self):
        self.cache: Dict[Tuple[int, int, int], object] = {}

    def key(self, lat: float, lon: float, radius: int):
        # round to 3 decimals (~111m) to reuse nearby graphs
        return (int(round(lat * 1000)), int(round(lon * 1000)), radius)

    def get_graph(self, lat: float, lon: float, radius: int = 1000):
        k = self.key(lat, lon, radius)
        if k in self.cache:
            return self.cache[k]
        G = ox.graph_from_point((lat, lon), dist=radius, network_type="drive", simplify=True)
        self.cache[k] = G
        return G


def laplace_mechanism(value: float, epsilon: float, sensitivity: float = 1e-5) -> float:
    # sensitivity expressed in degrees (default 1e-5 deg ~ 1.11 m)
    scale = sensitivity / epsilon
    return value + float(np.random.laplace(0.0, scale))


def snap_to_edge(G, lat: float, lon: float) -> Tuple[float, float]:
    p = Point(lon, lat)
    try:
        # prefer nearest edge API (lon, lat)
        u, v, key = ox.distance.nearest_edges(G, lon, lat)
        edge_data = G.edges[u, v, key]
    except Exception:
        # fallback to nearest node then build simple edge
        node = ox.distance.nearest_nodes(G, lon, lat)
        u = node
        # pick one neighbor
        nbrs = list(G.adj[u])
        if not nbrs:
            return lat, lon
        v = nbrs[0]
        key = 0
        edge_data = G.edges[u, v, 0]

    if 'geometry' in edge_data and edge_data['geometry'] is not None:
        line: LineString = edge_data['geometry']
    else:
        x1 = G.nodes[u]['x']; y1 = G.nodes[u]['y']
        x2 = G.nodes[v]['x']; y2 = G.nodes[v]['y']
        line = LineString([(x1, y1), (x2, y2)])

    # project point to the nearest point on the linestring using shapely's nearest_points
    projected_on_line = nearest_points(line, p)[0]
    return projected_on_line.y, projected_on_line.x


def get_route_distance_km(G, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Attempt to compute shortest-path distance (meters->km) on graph G between nearest nodes to lat/lon.
    Returns distance in km. Raises if path not found or graph lacks 'length' attributes.
    """
    try:
        # nearest_nodes expects (G, x, y) -> (lon, lat)
        u = ox.distance.nearest_nodes(G, lon1, lat1)
        v = ox.distance.nearest_nodes(G, lon2, lat2)
        # Use networkx shortest path length weighted by 'length' (meters)
        length_m = nx.shortest_path_length(G, u, v, weight='length')
        return float(length_m) / 1000.0
    except Exception:
        raise


def process_row(row, gc: GraphCache, epsilon: float, radius: int, sensitivity: float):
    try:
        s_lat, s_lon = parse_coord(row['start_location'])
        e_lat, e_lon = parse_coord(row['end_location'])
    except Exception as ex:
        return None

    # get graph(s)
    Gs = gc.get_graph(s_lat, s_lon, radius)
    Ge = gc.get_graph(e_lat, e_lon, radius)

    # apply DP noise
    s_lat_noisy = laplace_mechanism(s_lat, epsilon, sensitivity)
    s_lon_noisy = laplace_mechanism(s_lon, epsilon, sensitivity)
    e_lat_noisy = laplace_mechanism(e_lat, epsilon, sensitivity)
    e_lon_noisy = laplace_mechanism(e_lon, epsilon, sensitivity)

    # map-match (snap) each noisy point to nearest edge in corresponding graph
    s_lat_snap, s_lon_snap = snap_to_edge(Gs, s_lat_noisy, s_lon_noisy)
    e_lat_snap, e_lon_snap = snap_to_edge(Ge, e_lat_noisy, e_lon_noisy)

    # straight-line (haversine) between snapped points
    haversine_km_snapped = haversine_km(s_lat_snap, s_lon_snap, e_lat_snap, e_lon_snap)

    # Try to compute route distance along the road graph (preferred). We try Gs, then Ge.
    route_distance_km = None
    route_source = 'none'
    try:
        route_distance_km = get_route_distance_km(Gs, s_lat_snap, s_lon_snap, e_lat_snap, e_lon_snap)
        route_source = 'Gs'
    except Exception:
        try:
            route_distance_km = get_route_distance_km(Ge, s_lat_snap, s_lon_snap, e_lat_snap, e_lon_snap)
            route_source = 'Ge'
        except Exception:
            # fallback: use haversine distance if no graph route available
            route_distance_km = haversine_km_snapped
            route_source = 'haversine_fallback'

    gps_distance_km = route_distance_km

    original_total = float(row.get('total_distance') or 0.0)

    # Try to extract original highway/city distances from possible column names
    def _get_field(r, candidates):
        for k in candidates:
            if k in r and r[k] not in (None, '', 'NaN'):
                try:
                    return float(r[k])
                except Exception:
                    continue
        return 0.0

    orig_highway = _get_field(row, ['highway_distance', 'highwayDistance', 'highway (distance)', 'highway (distance)', 'highway (distance)'.lower(), 'highway'])
    orig_city = _get_field(row, ['city_distance', 'cityDistance', 'city (distance)', 'city (distance)', 'city (distance)'.lower(), 'city'])

    # Preserve original proportion of highway vs city when splitting recomputed route distance
    if (orig_highway + orig_city) > 0:
        highway_ratio = orig_highway / (orig_highway + orig_city)
    else:
        # if original breakdown not available, fall back to 0.5/0.5
        highway_ratio = 0.5

    highway_snapped = float(gps_distance_km) * highway_ratio
    city_snapped = float(gps_distance_km) * (1.0 - highway_ratio)

    out = {
        'vin': row.get('VIN') or row.get('vin') or '',
        'timestamp': row.get('start_time') or row.get('start_time'),
        'total_distance_original_km': float(row.get('total_distance') or 0.0),
        # recomputed distance along roads (km) where possible, else haversine
        'total_distance_snapped_km': float(gps_distance_km),
        # difference original - recomputed (km)
        'distance_diff_km': original_total - float(gps_distance_km),
        'route_distance_source': route_source,
        'original_highway_km': float(orig_highway),
        'original_city_km': float(orig_city),
        'highway_distance_snapped_km': highway_snapped,
        'city_distance_snapped_km': city_snapped,
        'highway_diff_km': float(orig_highway) - highway_snapped,
        'city_diff_km': float(orig_city) - city_snapped,
        'start_lat': s_lat,
        'start_lon': s_lon,
        'end_lat': e_lat,
        'end_lon': e_lon,
        'start_noisy_lat': s_lat_noisy,
        'start_noisy_lon': s_lon_noisy,
        'end_noisy_lat': e_lat_noisy,
        'end_noisy_lon': e_lon_noisy,
        'start_snap_lat': s_lat_snap,
        'start_snap_lon': s_lon_snap,
        'end_snap_lat': e_lat_snap,
        'end_snap_lon': e_lon_snap,
        'gps_distance_snapped_km': haversine_km_snapped,
    }
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o', required=False)
    parser.add_argument('--epsilon', '-e', type=float, default=0.5)
    parser.add_argument('--radius', '-r', type=int, default=1000, help='OSM search radius in meters')
    parser.add_argument('--sensitivity', '-s', type=float, default=1e-5, help='Sensitivity in degrees')
    args = parser.parse_args()

    infile = args.input
    outfile = args.output or (os.path.splitext(infile)[0] + '_dp.csv')

    df = pd.read_csv(infile)

    gc = GraphCache()
    rows = []
    total = len(df)
    for idx, row in df.iterrows():
        out = process_row(row, gc, args.epsilon, args.radius, args.sensitivity)
        if out:
            rows.append(out)
        if (idx + 1) % 50 == 0:
            print(f'Processed {idx+1}/{total}')

    outdf = pd.DataFrame(rows)
    outdf.to_csv(outfile, index=False)
    print('Saved:', outfile)


if __name__ == '__main__':
    main()