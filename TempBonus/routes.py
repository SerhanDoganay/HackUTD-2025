# viz_routes.py
import matplotlib.pyplot as plt
import pandas as pd

def plot_routes_map(schedule: pd.DataFrame, cauldrons: pd.DataFrame, market: dict, title="Routes: all witches"):
    # Position lookups
    pos = {row["id"]: (row["longitude"], row["latitude"]) for _, row in cauldrons.iterrows()}
    pos[market["id"]] = (market["longitude"], market["latitude"])

    plt.figure(figsize=(12, 8))
    # Base nodes
    xs = [pos[c][0] for c in cauldrons["id"]]
    ys = [pos[c][1] for c in cauldrons["id"]]
    plt.scatter(xs, ys, s=40, label="Cauldrons", zorder=2)
    plt.scatter([pos[market["id"]][0]], [pos[market["id"]][1]], s=120, marker="*", label="Market (Depot)", zorder=3)

    # Draw polylines per witch, in time order
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
    for i, (witch, grp) in enumerate(schedule.groupby("witch_id")):
        color = colors[i % len(colors)]
        # Select only real nodes (not synthetic ids)
        nodes = grp["node"].tolist()
        pts = [pos.get(n) for n in nodes if n in pos]
        # draw segments between consecutive points
        for a, b in zip(pts[:-1], pts[1:]):
            if a is None or b is None:
                continue
            plt.plot([a[0], b[0]], [a[1], b[1]], "-", color=color, alpha=0.7, linewidth=2)
        # label first/last
        if pts:
            plt.scatter([pts[0][0]], [pts[0][1]], color=color, s=60, zorder=4)
            plt.text(pts[0][0], pts[0][1], f"{witch} start", fontsize=8, color=color)
            plt.scatter([pts[-1][0]], [pts[-1][1]], color=color, s=60, zorder=4)

    plt.legend()
    plt.title(title)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.show()
