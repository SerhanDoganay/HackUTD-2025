
import requests
import pandas as pd
import networkx as nx

BASE = "https://hackutd2025.eog.systems"

def fetch_network_edges() -> list[dict]:
    """GET /api/Information/network -> [{'from','to','travel_time_minutes'}, ...]"""
    url = f"{BASE}/api/Information/network"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Some APIs return {"edges":[...]} vs a bare list; normalize:
    edges = data["edges"] if isinstance(data, dict) and "edges" in data else data
    return edges

def fetch_cauldrons() -> pd.DataFrame:
    """GET /api/Information/cauldrons -> id, name, lat, lon, max_volume (for reference)"""
    url = f"{BASE}/api/Information/cauldrons"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())

def fetch_market() -> dict:
    """GET /api/Information/market -> depot node info (id, name, lat, lon)"""
    url = f"{BASE}/api/Information/market"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

def build_graph(edges: list[dict], directed: bool = True) -> nx.Graph:
    """
    Build a NetworkX graph from edge list.
    - directed=True  -> nx.DiGraph with given directed travel times
    - directed=False -> nx.Graph treating edges as bidirectional (min time if both provided)
    """
    G = nx.DiGraph() if directed else nx.Graph()
    for e in edges:
        u = e["from"]; v = e["to"]; w = float(e["travel_time_minutes"])
        if directed:
            G.add_edge(u, v, travel_time=w)
        else:
            # For undirected, if multiple entries exist both ways, keep the smaller weight
            if G.has_edge(u, v):
                G[u][v]["travel_time"] = min(G[u][v]["travel_time"], w)
            else:
                G.add_edge(u, v, travel_time=w)
    return G

def all_pairs_travel_time_matrix(G: nx.Graph) -> pd.DataFrame:
    """
    Compute shortest-path travel times (minutes) between all nodes via Dijkstra.
    Returns a pandas DataFrame with nodes as both index and columns.
    """
    # Dijkstra path lengths with edge weight 'travel_time'
    lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="travel_time"))
    # Collect nodes
    nodes = sorted(G.nodes())
    # Build dense matrix
    data = []
    for i in nodes:
        row = []
        for j in nodes:
            val = lengths.get(i, {}).get(j, float("inf"))
            row.append(val)
        data.append(row)
    df = pd.DataFrame(data, index=nodes, columns=nodes)
    return df

def compute_travel_times(directed: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    High-level convenience:
      - fetch edges/cauldrons/market
      - build graph (directed or undirected)
      - compute all-pairs travel-time matrix (minutes)
    Returns: (matrix_df, cauldrons_df, market_dict)
    """
    edges = fetch_network_edges()
    cauldrons = fetch_cauldrons()
    market = fetch_market()

    # Build graph and ensure market + cauldrons appear as nodes (even if isolated)
    G = build_graph(edges, directed=directed)
    G.add_node(market["id"])
    for cid in cauldrons["id"]:
        G.add_node(cid)

    matrix = all_pairs_travel_time_matrix(G)
    return matrix, cauldrons, market

if __name__ == "__main__":
    # --- Example usage ---
    travel_matrix, cauldrons, market = compute_travel_times(directed=True)

    print("\nMarket node:", market.get("id"), "-", market.get("name"))
    print("\nCauldrons (head):")
    print(cauldrons[["id","name","max_volume"]].head())

    print("\nTravel-time matrix (minutes) — head:")
    # Show a compact view with first few nodes/columns
    head_nodes = travel_matrix.index[:8]
    print(travel_matrix.loc[head_nodes, head_nodes])

    # If you prefer undirected (bidirectional travel assumed), run:
    # travel_matrix_undirected, _, _ = compute_travel_times(directed=False)

