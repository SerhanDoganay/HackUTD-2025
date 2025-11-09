# job_windows.py
import pandas as pd
import math

def widen_and_shift_windows(
    jobs: pd.DataFrame,
    travel_minutes,
    depot_id: str,
    min_window_min: int = 60,
    add_slack_min: int = 45
) -> pd.DataFrame:
    """
    Ensure each job’s window is at least depot->node travel + service time + slack.
    If not, move earliest earlier and/or latest later (keeping chronological order).
    """
    jobs = jobs.copy()
    for i, r in jobs.iterrows():
        node = r["node_id"]
        t_dep = travel_minutes.loc[depot_id, node]
        if math.isinf(t_dep):
            # leave as-is; solver will still fail (diagnostics will flag)
            continue

        earliest = pd.to_datetime(r["earliest"])
        latest   = pd.to_datetime(r["latest"])
        need = int(round(t_dep + r["service_time"] + add_slack_min))

        # current window
        have = int((latest - earliest).total_seconds() // 60)
        if have < need:
            # widen symmetrically, prefer pulling earlier (preemptive)
            delta = need - have
            earliest = earliest - pd.Timedelta(minutes=delta//2 + add_slack_min//2)
            latest   = latest   + pd.Timedelta(minutes=delta - delta//2 + add_slack_min//2)

        # enforce minimum window
        have = int((latest - earliest).total_seconds() // 60)
        if have < min_window_min:
            grow = min_window_min - have
            earliest = earliest - pd.Timedelta(minutes=grow//2)
            latest   = latest   + pd.Timedelta(minutes=grow - grow//2)

        jobs.at[i, "earliest"] = earliest
        jobs.at[i, "latest"]   = latest
    return jobs
