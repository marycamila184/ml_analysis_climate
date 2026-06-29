"""
Compute validation metrics stratified by biome (Article 1, Section 4.5).

Output: outputs/metrics/biome_metrics.csv
"""
import xarray as xr
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from metrics.compute_metrics import kge, relative_bias, percentile_bias

VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
BIOMES = {1: "Amazon", 2: "Cerrado", 3: "Caatinga", 4: "Atlantic Forest", 5: "Pampa", 6: "Pantanal"}
COMPARISONS = [
    ("era5", "xavier", "era5_vs_xavier"),
    ("era5", "brdwgd", "era5_vs_brdwgd"),
]

biome_mask = xr.open_dataset("data/processed/biome_mask.nc")["biome"]
results = []

for var in VARIABLES:
    for sim_name, obs_name, comp_name in COMPARISONS:
        sim = xr.open_dataset(f"data/processed/{sim_name}/{var}.nc")[var]
        obs = xr.open_dataset(f"data/processed/{obs_name}/{var}.nc")[var]

        for biome_id, biome_name in BIOMES.items():
            mask = biome_mask == biome_id
            sim_bio = sim.where(mask)
            obs_bio = obs.where(mask)

            results.append({
                "variable":   var,
                "comparison": comp_name,
                "biome":      biome_name,
                "bias_rel":   float(relative_bias(obs_bio, sim_bio).mean()),
                "kge":        kge(obs_bio, sim_bio),
                **percentile_bias(obs_bio, sim_bio),
            })
            print(f"[OK] {comp_name} | {var} | {biome_name}")

df = pd.DataFrame(results)
df.to_csv("outputs/metrics/biome_metrics.csv", index=False)
print("\n[DONE] outputs/metrics/biome_metrics.csv")
