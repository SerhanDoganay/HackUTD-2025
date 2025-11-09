# vrptw_solver.py
from __future__ import annotations
import math
import pandas as pd
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

def solve_vrptw_min_vehicles(
    travel_minutes: pd.DataFrame,
    jobs: pd.DataFrame,
    depot_id: str,
    *,
    vehicle_capacity: float,
    unload_time_min: int = 15,
    shift_length_min: int = 8 * 60,
    search_limit_vehicles: tuple[int, int] | None = None,
    time_horizon_pad_min: int = 60
) -> tuple[int, dict] | tuple[None, None]:
    """
    Increment vehicles until feasible; return (min_vehicle_count, solution dict)

    travel_minutes: square DF (nodes x nodes) with minutes; must include depot and all job node_ids
    jobs: DF with ['job_id','node_id','earliest','latest','demand','service_time']
    depot_id: market node id (start/end)
    vehicle_capacity: max carrying capacity per witch
    unload_time_min: service time when visiting depot (unload)
    shift_length_min: max time per route
    search_limit_vehicles: (start, max) for search; if None, compute lower bound then step up
    time_horizon_pad_min: pad the time horizon to keep routing time dimension generous
    """
    # Build node index map
    nodes = list(travel_minutes.index)
    node_to_idx = {n: i for i, n in enumerate(nodes)}
    if depot_id not in node_to_idx:
        raise ValueError("Depot node not found in travel matrix.")

    # Convert jobs to per-node windows/demands/service
    # Multiple jobs may be at the same cauldron node → we model each as a separate customer node
    # by duplicating the base node in a "manager index space".
    # Simplest robust approach: create a synthetic node list for routing index, mapping back to nodes.

    # Base nodes include the depot:
    base_node_idx = [node_to_idx[depot_id]]
    base_node_idx_map = [depot_id]

    # Add one synthetic node per job
    job_rows = []
    for _, r in jobs.iterrows():
        job_rows.append(r.to_dict())

    # Build arrays for OR-Tools
    all_nodes = [depot_id] + [f"JOB::{jr['job_id']}" for jr in job_rows]
    # Travel: we need a function that maps from any two synthetic nodes to their travel time.
    # If either is depot, use depot_id; if job, use its node_id.

    job_lookup = {f"JOB::{jr['job_id']}": jr for jr in job_rows}

    def travel_time(a_name: str, b_name: str) -> int:
        a_node = depot_id if a_name == depot_id else job_lookup[a_name]["node_id"]
        b_node = depot_id if b_name == depot_id else job_lookup[b_name]["node_id"]
        val = travel_minutes.loc[a_node, b_node]
        if math.isinf(val) or pd.isna(val):
            # Large penalty for disconnected graph
            return 10**6
        return int(round(float(val)))

    # Time windows per synthetic node
    tw_earliest = []
    tw_latest = []
    service_time = []

    # Depot time window: from min earliest to max latest plus pad
    if len(job_rows):
        global_start = min(pd.to_datetime([jr["earliest"] for jr in job_rows]))
        global_end = max(pd.to_datetime([jr["latest"] for jr in job_rows])) + pd.Timedelta(minutes=time_horizon_pad_min)
    else:
        global_start = pd.Timestamp.now()
        global_end = global_start + pd.Timedelta(hours=1)

    # convert to minutes offset from global_start
    def to_minutes(ts): return int((pd.to_datetime(ts) - global_start).total_seconds() // 60)

    all_nodes_tuples = []
    # Depot first
    tw_earliest.append(0)
    tw_latest.append(int((global_end - global_start).total_seconds() // 60))
    service_time.append(unload_time_min)  # if they stop at depot, count unload time
    all_nodes_tuples.append(depot_id)

    # Jobs
    for name in all_nodes[1:]:
        jr = job_lookup[name]
        e, l = to_minutes(jr["earliest"]), to_minutes(jr["latest"])
        tw_earliest.append(e)
        tw_latest.append(l)
        service_time.append(int(jr["service_time"]))
        all_nodes_tuples.append(name)

    # Demands
    demands = [0] + [float(job_lookup[n]["demand"]) for n in all_nodes[1:]]

    # Vehicle search bounds
    if search_limit_vehicles is None:
        # Lower bound: capacity-wise per horizon day (simple)
        cap_lb = max(1, math.ceil(sum(demands) / vehicle_capacity))
        start_k = cap_lb
        max_k = max(start_k, start_k + 10)
    else:
        start_k, max_k = search_limit_vehicles

    # Try K = start_k .. max_k
    for K in range(start_k, max_k + 1):
        # Create RoutingIndexManager & RoutingModel
        manager = pywrapcp.RoutingIndexManager(len(all_nodes), K, 0)  # depot is index 0
        routing = pywrapcp.RoutingModel(manager)

        # Transit callback (time)
        def time_cb(from_index, to_index):
            a = all_nodes[manager.IndexToNode(from_index)]
            b = all_nodes[manager.IndexToNode(to_index)]
            # travel + service at origin (common trick to include service time)
            return travel_time(a, b)

        transit_index = routing.RegisterTransitCallback(time_cb)

        # Time dimension
        routing.SetArcCostEvaluatorOfAllVehicles(transit_index)
        routing.AddDimension(
            transit_index,
            60,  # allow waiting
            shift_length_min,  # max per vehicle
            False,
            "Time"
        )
        time_dim = routing.GetDimensionOrDie("Time")

        # Add service times (as separate slack at each node)
        for node_index in range(len(all_nodes)):
            index = manager.NodeToIndex(node_index)
            time_dim.SlackVar(index).SetRange(service_time[node_index], service_time[node_index])

        # Time windows
        for node_index in range(len(all_nodes)):
            index = manager.NodeToIndex(node_index)
            time_dim.CumulVar(index).SetRange(tw_earliest[node_index], tw_latest[node_index])

        # Capacity dimension
        def demand_cb(from_index):
            node_name = all_nodes[manager.IndexToNode(from_index)]
            if node_name == depot_id:
                return 0
            return int(math.ceil(job_lookup[node_name]["demand"]))
        demand_idx = routing.RegisterUnaryTransitCallback(demand_cb)
        routing.AddDimensionWithVehicleCapacity(
            demand_idx, 0, [int(vehicle_capacity)] * K, True, "Capacity"
        )

        # Allow multiple returns to depot; model unload time via depot service time already present.

        # First solution heuristic + guided local search
        search_params = pywrapcp.DefaultRoutingSearchParameters()
        search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        search_params.time_limit.FromSeconds(15)

        solution = routing.SolveWithParameters(search_params)
        if solution:
            # Extract plan
            time_var = time_dim.CumulVar
            cap_dim = routing.GetDimensionOrDie("Capacity")
            routes = []
            for v in range(K):
                idx = routing.Start(v)
                if routing.IsEnd(solution.Value(routing.NextVar(idx))):
                    continue  # empty route
                while not routing.IsEnd(idx):
                    node_id = all_nodes[manager.IndexToNode(idx)]
                    arr = solution.Value(time_var(idx))
                    load = solution.Value(cap_dim.CumulVar(idx))
                    nxt = solution.Value(routing.NextVar(idx))
                    dep = solution.Value(time_var(idx))  # same here; with slack=service time
                    routes.append({
                        "vehicle": v,
                        "node": node_id,
                        "arrive_min": arr,
                        "depart_min": dep,
                        "load": load
                    })
                    idx = nxt
                # add end depot
                node_id = all_nodes[manager.IndexToNode(idx)]
                arr = solution.Value(time_var(idx))
                load = solution.Value(cap_dim.CumulVar(idx))
                routes.append({
                    "vehicle": v,
                    "node": node_id,
                    "arrive_min": arr,
                    "depart_min": arr,
                    "load": load
                })

            # Convert minutes back to timestamps
            start_ts = min(pd.to_datetime(j["earliest"]) for _, j in jobs.iterrows()) if len(jobs) else pd.Timestamp.now()
            def minutes_to_ts(m): return start_ts + pd.Timedelta(minutes=int(m))
            sched = []
            for r in routes:
                node = r["node"]
                is_job = node.startswith("JOB::")
                base_node = node if not is_job else jobs.set_index("job_id").loc[node.replace("JOB::", ""), "node_id"]
                sched.append({
                    "witch_id": f"witch_{r['vehicle']}",
                    "node": base_node,
                    "synthetic_node": node,
                    "arrive_time": minutes_to_ts(r["arrive_min"]),
                    "depart_time": minutes_to_ts(r["depart_min"]),
                    "load": r["load"]
                })
            schedule_df = pd.DataFrame(sched).sort_values(["witch_id", "arrive_time"])
            return K, {"schedule": schedule_df}

    return None, None
