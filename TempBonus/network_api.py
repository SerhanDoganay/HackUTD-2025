# network_api.py
import requests
import pandas as pd
import networkx as nx

BASE = "https://hackutd2025.eog.systems"

def fetch_network_edges() -> list[dict]:
    r = requests.get(f"{BASE}/api/Information/network", timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["edges"] if isinstance(data, dict) and "edges" in data else data

def fetch_cauldrons() -> pd.DataFrame:
    r = requests.get(f"{BASE}/api/Information/cauldrons", timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())

def fetch_market() -> dict:
    r = requests.get(f"{BASE}/api/Information/market", timeout=30)
    r.raise_for_status()
    return r.json()

def fetch_couriers() -> pd.DataFrame:
    r = requests.get(f"{BASE}/api/Information/couriers", timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())

def build_graph(edges: list[dict], directed: bool = True) -> nx.Graph:
    G = nx.DiGraph() if directed else nx.Graph()
    for e in edges:
        u, v = e["from"], e["to"]
        w = float(e["travel_time_minutes"])
        if directed:
            G.add_edge(u, v, travel_time=w)
        else:
            if G.has_edge(u, v):
                G[u][v]["travel_time"] = min(G[u][v]["travel_time"], w)
            else:
                G.add_edge(u, v, travel_time=w)
    return G

def all_pairs_travel_time_matrix(G: nx.Graph) -> pd.DataFrame:
    lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="travel_time"))
    nodes = sorted(G.nodes())
    data = [[lengths.get(i, {}).get(j, float("inf")) for j in nodes] for i in nodes]
    return pd.DataFrame(data, index=nodes, columns=nodes)

def compute_travel_times(directed: bool = True):
    edges = fetch_network_edges()
    cauldrons = fetch_cauldrons()
    market = fetch_market()

    G = build_graph(edges, directed=directed)
    G.add_node(market["id"])
    for cid in cauldrons["id"]:
        G.add_node(cid)

    matrix = all_pairs_travel_time_matrix(G)
    return matrix, cauldrons, market
