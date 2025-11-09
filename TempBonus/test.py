# diagnostics.py
import math
import pandas as pd

def basic_lower_bounds(jobs: pd.DataFrame, vehicle_capacity: float, shift_length_min: int):
    total_demand = float(jobs["demand"].sum())
    cap_lb = max(1, math.ceil(total_demand / vehicle_capacity))

    # naive time bound: travel depot->node->depot for each job + service time
    # (The solver can share travel; this is a conservative bound.)
    return cap_lb

def unreachable_nodes(travel_minutes: pd.DataFrame, depot_id: str, jobs: pd.DataFrame):
    bad = []
    for node in jobs["node_id"].unique():
        t1 = travel_minutes.loc[depot_id, node]
        t2 = travel_minutes.loc[node, depot_id]
        if math.isinf(t1) or math.isinf(t2):
            bad.append(node)
    return bad

def tight_windows(jobs: pd.DataFrame, travel_minutes: pd.DataFrame, depot_id: str, min_service_pad: int = 10):
    """
    Returns rows where window < depot->node travel (can’t even make it from depot),
    or where window < service time.
    """
    rows = []
    for _, r in jobs.iterrows():
        node = r["node_id"]
        window = (pd.to_datetime(r["latest"]) - pd.to_datetime(r["earliest"])).total_seconds() / 60.0
        t_dep = travel_minutes.loc[depot_id, node]
        if math.isinf(t_dep):
            rows.append((node, "UNREACHABLE"))
            continue
        if window < max(t_dep, r["service_time"], min_service_pad):
            rows.append((node, f"too tight: window={window:.1f} < need≈{max(t_dep, r['service_time'], min_service_pad):.1f}"))
    return rows
