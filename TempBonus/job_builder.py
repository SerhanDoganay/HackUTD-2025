# job_builder.py
import numpy as np
import pandas as pd

def _interp_cross_time(ts_index: pd.DatetimeIndex, values: np.ndarray, threshold: float):
    """
    Return the first crossing time (linear interpolation) where values cross up through threshold.
    If never crosses, return None.
    """
    for i in range(1, len(values)):
        if values[i-1] < threshold <= values[i]:
            t0, t1 = ts_index[i-1], ts_index[i]
            v0, v1 = values[i-1], values[i]
            if v1 == v0:
                return t1
            frac = (threshold - v0) / (v1 - v0)
            return t0 + (t1 - t0) * frac
    return None

def build_pickup_jobs(
    future_wide: pd.DataFrame,
    cauldrons: pd.DataFrame,
    *,
    overflow_frac: float = 0.90,    # θ
    target_frac: float = 0.20,      # τ
    buffer_min: int = 45,
    service_time_min: int = 8,
    max_job_split_capacity: float | None = None
) -> pd.DataFrame:
    """
    Convert predicted levels into pickup jobs with time windows.

    Params:
      future_wide: index=future timestamps (hourly), columns=cauldron IDs, values=predicted level
      cauldrons: DataFrame with columns ['id','name','max_volume', 'latitude','longitude']
      overflow_frac: fraction of max_volume that triggers a pickup
      target_frac: target level after service (as fraction of max_volume)
      buffer_min: minutes before the crossing to start the time window
      service_time_min: minutes spent at cauldron per pickup
      max_job_split_capacity: if given, split large jobs into chunks with this max demand

    Returns:
      jobs DataFrame with columns:
        ['job_id','node_id','earliest','latest','demand','service_time','target_level',
         'threshold','max_volume','lat','lon']
    """
    jobs = []
    idx = future_wide.index
    # Map cauldron meta
    meta = cauldrons.set_index("id")[["max_volume", "latitude", "longitude"]]

    for cid in future_wide.columns:
        if cid not in meta.index:
            continue
        max_vol = float(meta.loc[cid, "max_volume"])
        lat = float(meta.loc[cid, "latitude"])
        lon = float(meta.loc[cid, "longitude"])
        series = future_wide[cid].astype(float).values

        threshold = overflow_frac * max_vol
        target = target_frac * max_vol

        cross_time = _interp_cross_time(idx, series, threshold)
        if cross_time is None:
            # no job needed in horizon (never hits threshold)
            continue

        earliest = cross_time - pd.Timedelta(minutes=buffer_min)

        # A conservative "latest": the next timestamp after first crossing
        # (you can refine by checking when it would exceed max_volume)
        # If your data only grazes the threshold, widen by one hour
        latest = max(cross_time + pd.Timedelta(minutes=15), earliest + pd.Timedelta(minutes=15))

        # Approximate level at earliest (linear between surrounding points if needed)
        # Find bounding timestamps:
        before = idx[idx <= earliest]
        after = idx[idx >= earliest]
        if len(before) and len(after):
            t0 = before[-1]
            t1 = after[0]
            v0 = future_wide.loc[t0, cid]
            v1 = future_wide.loc[t1, cid]
            if t0 == t1:
                level_at_earliest = float(v0)
            else:
                frac = (earliest - t0) / (t1 - t0)
                level_at_earliest = float(v0 + (v1 - v0) * frac)
        else:
            level_at_earliest = float(future_wide.iloc[0][cid])

        demand = max(0.0, level_at_earliest - target)
        if demand <= 1e-6:
            continue

        def emit_job(d: float, k: int):
            jobs.append({
                "job_id": f"{cid}__{int(earliest.value/1e9)}__{k}",
                "node_id": cid,
                "earliest": earliest,
                "latest": latest,
                "demand": d,
                "service_time": service_time_min,
                "target_level": target,
                "threshold": threshold,
                "max_volume": max_vol,
                "lat": lat,
                "lon": lon
            })

        if max_job_split_capacity and demand > max_job_split_capacity:
            # split into ceil(demand / split_cap) jobs
            n = int(np.ceil(demand / max_job_split_capacity))
            base = demand / n
            for k in range(n):
                emit_job(base, k)
        else:
            emit_job(demand, 0)

    return pd.DataFrame(jobs).sort_values(["earliest", "node_id"]).reset_index(drop=True)
