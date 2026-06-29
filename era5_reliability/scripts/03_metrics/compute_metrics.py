"""
Compute all validation metrics per grid cell and globally.

Metrics (Section 3.2 of Article 1):
  - Relative bias (%)
  - RMSE, MAE
  - Pearson correlation (r)
  - Kling-Gupta Efficiency (KGE)
  - Percentile bias (P10, P90)
  - CDD / CWD (precipitation only)

Comparisons: ERA5 vs Xavier, ERA5 vs BR-DWGD

Output: outputs/metrics/global_metrics.csv
"""
import xarray as xr
import numpy as np
import pandas as pd

VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
COMPARISONS = [
    ("era5", "xavier", "era5_vs_xavier"),
    ("era5", "brdwgd", "era5_vs_brdwgd"),
]


def relative_bias(obs, sim):
    return ((sim.mean("time") - obs.mean("time")) / obs.mean("time")) * 100


def rmse(obs, sim):
    return float(np.sqrt(((sim - obs) ** 2).mean("time").mean()))


def mae(obs, sim):
    return float(np.abs(sim - obs).mean("time").mean())


def pearson_r(obs, sim):
    return xr.corr(obs, sim, dim="time")


def kge(obs, sim):
    """Kling-Gupta Efficiency (Gupta et al. 2009)."""
    r     = float(xr.corr(obs.stack(z=["lat", "lon"]), sim.stack(z=["lat", "lon"]), dim="time").mean())
    alpha = float(sim.std("time").mean() / obs.std("time").mean())
    beta  = float(sim.mean("time").mean() / obs.mean("time").mean())
    return 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)


def percentile_bias(obs, sim, q_low=0.10, q_high=0.90):
    p10_obs = obs.quantile(q_low,  dim="time")
    p90_obs = obs.quantile(q_high, dim="time")
    p10_sim = sim.quantile(q_low,  dim="time")
    p90_sim = sim.quantile(q_high, dim="time")
    return {
        "bias_p10": float(((p10_sim - p10_obs) / p10_obs.where(p10_obs != 0)).mean() * 100),
        "bias_p90": float(((p90_sim - p90_obs) / p90_obs.where(p90_obs != 0)).mean() * 100),
    }


def cdd_cwd(pr_obs, pr_sim, threshold=1.0):
    """Consecutive Dry Days / Consecutive Wet Days (precipitation only)."""
    def max_run(arr, condition):
        runs, count = [], 0
        for v in arr:
            if condition(v):
                count += 1
            else:
                if count > 0:
                    runs.append(count)
                count = 0
        return max(runs) if runs else 0

    cdd_obs = np.apply_along_axis(lambda x: max_run(x, lambda v: v < threshold), 0, pr_obs.values)
    cdd_sim = np.apply_along_axis(lambda x: max_run(x, lambda v: v < threshold), 0, pr_sim.values)
    cwd_obs = np.apply_along_axis(lambda x: max_run(x, lambda v: v >= threshold), 0, pr_obs.values)
    cwd_sim = np.apply_along_axis(lambda x: max_run(x, lambda v: v >= threshold), 0, pr_sim.values)
    return {
        "cdd_obs_mean": float(cdd_obs.mean()),
        "cdd_sim_mean": float(cdd_sim.mean()),
        "cdd_bias":     float(cdd_sim.mean() - cdd_obs.mean()),
        "cwd_obs_mean": float(cwd_obs.mean()),
        "cwd_sim_mean": float(cwd_sim.mean()),
        "cwd_bias":     float(cwd_sim.mean() - cwd_obs.mean()),
    }


results = []

for var in VARIABLES:
    for sim_name, obs_name, comp_name in COMPARISONS:
        sim = xr.open_dataset(f"data/processed/{sim_name}/{var}.nc")[var]
        obs = xr.open_dataset(f"data/processed/{obs_name}/{var}.nc")[var]

        metrics = {
            "variable":   var,
            "comparison": comp_name,
            "bias_rel":   float(relative_bias(obs, sim).mean()),
            "rmse":       rmse(obs, sim),
            "mae":        mae(obs, sim),
            "r":          float(pearson_r(obs, sim).mean()),
            "kge":        kge(obs, sim),
            **percentile_bias(obs, sim),
        }

        if var == "pr":
            metrics.update(cdd_cwd(obs, sim))

        results.append(metrics)
        print(f"[OK] {comp_name} | {var}")

df = pd.DataFrame(results)
df.to_csv("outputs/metrics/global_metrics.csv", index=False)
print("\n[DONE] outputs/metrics/global_metrics.csv")
