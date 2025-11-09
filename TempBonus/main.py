# Orchestrates: fetch network + meta -> build jobs from your future_wide -> find min witches -> schedule -> plot.

from test import basic_lower_bounds, unreachable_nodes, tight_windows
from job_windows import widen_and_shift_windows

import pandas as pd

from Forecast_model import forecast_all

from network_api import compute_travel_times, fetch_couriers
from job_builder import build_pickup_jobs
from vrptw_solver import solve_vrptw_min_vehicles
from routes import plot_routes_map

# ----------------------------
# 0) Provide or load your forecast (future_wide)
#    REQUIRED SHAPE: index = future hourly timestamps, columns = cauldron IDs, values = predicted volume
# ----------------------------
def get_future_wide():
    future_wide, _ = forecast_all()
    return future_wide

if __name__ == "__main__":
    # 1) Load travel times + cauldrons + market
    travel_matrix, cauldrons, market = compute_travel_times(directed=False)
    depot_id = market["id"]

    # 2) Load courier info (we’ll use a single capacity for the solver; pick min to be safe)
    couriers = fetch_couriers()
    if len(couriers) == 0:
        raise RuntimeError("No couriers returned from API.")
    vehicle_capacity = float(couriers["max_carrying_capacity"].min())

    # 3) Get your predicted levels
    future_wide = get_future_wide()  # <-- REPLACE THIS FUNCTION to return your forecast DF

    # 4) Build pickup jobs (time windows & demands)
    jobs = build_pickup_jobs(
        future_wide,
        cauldrons,
        overflow_frac=0.90,      # θ: 90% capacity triggers a pickup
        target_frac=0.20,        # τ: aim to leave at 20% capacity
        buffer_min=45,           # arrive ~45 min before the threshold crossing
        service_time_min=8,      # minutes at cauldron
        max_job_split_capacity=vehicle_capacity   # split if one job exceeds vehicle capacity
    )

    # --- Diagnostics before solving ---
    lb_cap = basic_lower_bounds(jobs, vehicle_capacity, shift_length_min=8*60)
    bad_nodes = unreachable_nodes(travel_matrix, depot_id, jobs)
    too_tight = tight_windows(jobs, travel_matrix, depot_id)

    print(f"\n[Diagnostics] Capacity lower bound K >= {lb_cap}")
    if bad_nodes:
        print(f"[Diagnostics] Unreachable from depot: {bad_nodes}")
    if too_tight:
        print(f"[Diagnostics] Tight windows ({len(too_tight)}): {too_tight[:10]}{' ...' if len(too_tight)>10 else ''}")

    # --- Make windows solver-friendly ---
    jobs = widen_and_shift_windows(jobs, travel_matrix, depot_id, min_window_min=60, add_slack_min=45)


    if jobs.empty:
        print("No pickups needed in the forecast horizon. 🎉")
        exit(0)

    # 5) Solve for minimum witches and build schedule
    K, solution = solve_vrptw_min_vehicles(
        travel_minutes=travel_matrix,
        jobs=jobs,
        depot_id=depot_id,
        vehicle_capacity=vehicle_capacity,
        unload_time_min=15,      # market unload time
        shift_length_min=8*60,   # 8-hour shift
        search_limit_vehicles=None  # let the solver start from a computed lower bound
    )

    if K is None:
        print("❌ No feasible plan within search limits. Consider increasing buffers or K.")
        exit(1)

    print(f"✅ Minimum witches required: {K}")
    schedule = solution["schedule"]
    # Keep only meaningful columns
    schedule = schedule[["witch_id","node","arrive_time","depart_time","load"]].reset_index(drop=True)
    print("\n--- Schedule (head) ---")
    print(schedule.head())

    # 6) Plot all routes on the map
    plot_routes_map(schedule, cauldrons, market, title=f"VRPTW routes — minimal witches: {K}")
