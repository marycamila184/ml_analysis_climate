"""
Generate the ERA5 Reliability Map for ML Training (Article 1, Figure 4).

Composite normalized score [0-1] per grid cell and variable.
Components: KGE, relative bias, P90 bias (equal weights — calibrate with supervisor).

Classification:
  >= 0.7  -> High confidence
  0.4-0.7 -> Moderate confidence
  < 0.4   -> Low confidence

Output: outputs/reliability_map/score_{variable}.nc
        outputs/reliability_map/category_{variable}.nc
"""
import xarray as xr
import numpy as np
import os

VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
os.makedirs("outputs/reliability_map", exist_ok=True)


def normalize(value, best, worst):
    """Normalize to [0, 1]: 1 = best, 0 = worst."""
    return np.clip((value - worst) / (best - worst), 0, 1)


for var in VARIABLES:
    sim = xr.open_dataset(f"data/processed/era5/{var}.nc")[var]
    obs = xr.open_dataset(f"data/processed/xavier/{var}.nc")[var]

    r     = xr.corr(obs, sim, dim="time")
    alpha = sim.std("time") / obs.std("time")
    beta  = sim.mean("time") / obs.mean("time")
    kge_map = 1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2)

    bias_map = np.abs((sim.mean("time") - obs.mean("time")) / obs.mean("time")) * 100
    p90_sim  = sim.quantile(0.9, dim="time")
    p90_obs  = obs.quantile(0.9, dim="time")
    bias_p90 = np.abs((p90_sim - p90_obs) / p90_obs) * 100

    score_kge  = normalize(kge_map,  best=1.0, worst=-0.5)
    score_bias = normalize(bias_map, best=0.0, worst=50.0)
    score_p90  = normalize(bias_p90, best=0.0, worst=50.0)

    reliability = (score_kge + score_bias + score_p90) / 3

    # 3 = High, 2 = Moderate, 1 = Low
    category = xr.where(reliability >= 0.7, 3, xr.where(reliability >= 0.4, 2, 1))

    reliability.name = f"reliability_{var}"
    category.name    = f"category_{var}"

    reliability.to_netcdf(f"outputs/reliability_map/score_{var}.nc")
    category.to_netcdf(f"outputs/reliability_map/category_{var}.nc")
    print(f"[OK] {var}")

print("[DONE] Reliability maps saved")
