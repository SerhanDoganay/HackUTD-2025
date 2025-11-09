import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from xgboost import XGBRegressor
from live_data import get_potion_levels

SEED = 42
HORIZON_HOURS = 24 * 7
LAGS = [1, 2, 3, 6, 12, 24]
N_JOBS = 1

def build_features(series: pd.Series):
    s = series.astype(float).resample("h").mean().to_frame("volume")
    s["hour"]  = s.index.hour
    s["dow"]   = s.index.dayofweek
    s["sin_h"] = np.sin(2*np.pi*s["hour"]/24)
    s["cos_h"] = np.cos(2*np.pi*s["hour"]/24)
    for lag in LAGS:
        s[f"lag_{lag}"] = s["volume"].shift(lag)
    s = s.dropna()
    return s.drop(columns=["volume"]), s["volume"], s.index

def fit_model(X, y):
    m = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=SEED,
        n_jobs=N_JOBS,
        tree_method="hist",
    )
    m.fit(X, y)
    return m

def forecast_recursive(model, X_hist, idx_hist, horizon=HORIZON_HOURS) -> pd.Series:
    cur = X_hist.iloc[-1].copy()
    feats = X_hist.columns
    last = idx_hist[-1]
    lag_cols = sorted([c for c in feats if c.startswith("lag_")], key=lambda c: int(c.split("_")[1]))
    ts_out, preds = [], []

    for h in range(1, horizon+1):
        ts = last + pd.Timedelta(hours=h)
        yhat = model.predict(pd.DataFrame([cur], columns=feats))[0]
        preds.append(yhat); ts_out.append(ts)

        # roll lags and update time features
        for i in reversed(range(len(lag_cols))):
            cur[lag_cols[i]] = yhat if i == 0 else cur[lag_cols[i-1]]
        hr, dow = ts.hour, ts.dayofweek
        cur["hour"], cur["dow"] = hr, dow
        cur["sin_h"], cur["cos_h"] = np.sin(2*np.pi*hr/24), np.cos(2*np.pi*hr/24)

    return pd.Series(preds, index=pd.DatetimeIndex(ts_out))

def forecast_all() -> tuple[pd.DataFrame, pd.DataFrame]:
    wide = get_potion_levels().sort_index()        # index=timestamp, cols=cauldrons
    hist_hr = wide.resample("h").mean()            # hourly historical (for plotting)
    last_week = hist_hr.iloc[-HORIZON_HOURS:]      # last week for the plot

    forecasts = {}
    future_index = None

    for col in wide.columns:
        X, y, idx = build_features(wide[col])
        if len(X) == 0:
            continue
        model = fit_model(X, y)
        fc = forecast_recursive(model, X, idx, horizon=HORIZON_HOURS)
        forecasts[col] = fc
        if future_index is None:
            future_index = fc.index

    future_wide = pd.DataFrame(index=future_index)
    for col, s in forecasts.items():
        future_wide[col] = s.reindex(future_index)

    return future_wide, last_week

if __name__ == "__main__":
    future_wide, last_week = forecast_all()

    print("\n--- Future (wide) head ---")
    print(future_wide.head())
    print(f"\nRows: {len(future_wide)}  |  Cauldrons: {len(future_wide.columns)}")

    # ---- one plot for all cauldrons ----
    plt.figure(figsize=(14, 6))
    colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

    for i, col in enumerate(future_wide.columns):
        color = colors[i % len(colors)]
        # historical last week (solid)
        if col in last_week.columns:
            plt.plot(last_week.index, last_week[col], color=color, linewidth=1.6)
        # forecast next week (dashed)
        plt.plot(future_wide.index, future_wide[col], "--", color=color, linewidth=1.8)

    # vertical line marking the boundary between history and forecast
    if len(last_week.index):
        plt.axvline(last_week.index[-1], color="k", linestyle=":", alpha=0.5)

    # legend: one entry per cauldron (color only; solid/dashed explained in title)
    legend_handles = [Line2D([0], [0], color=colors[i % len(colors)], lw=2, label=col)
                      for i, col in enumerate(future_wide.columns)]
    plt.legend(handles=legend_handles, title="Cauldrons", ncol=2)
    plt.title("All Cauldrons — Hourly: last week (solid) vs next week (dashed)")
    plt.xlabel("Time"); plt.ylabel("Potion Volume")
    plt.grid(alpha=0.3); plt.tight_layout()
    plt.show()
