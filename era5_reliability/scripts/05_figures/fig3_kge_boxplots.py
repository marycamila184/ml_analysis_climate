"""
Figure 3 — KGE boxplots by biome and variable.

Output: outputs/figures/fig3_kge_boxplots.png
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("outputs/metrics/biome_metrics.csv")
df_xavier = df[df["comparison"] == "era5_vs_xavier"]

fig, axes = plt.subplots(2, 3, figsize=(15, 10), sharey=True)
VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
VAR_LABELS = {
    "pr": "Precipitation", "tasmax": "Tmax", "tasmin": "Tmin",
    "rss": "Solar Radiation", "sfcWind": "Wind Speed", "hur": "Relative Humidity",
}

for ax, var in zip(axes.flat, VARIABLES):
    subset = df_xavier[df_xavier["variable"] == var]
    sns.boxplot(data=subset, x="biome", y="kge", ax=ax, palette="Set2")
    ax.axhline(0, color="red", linestyle="--", linewidth=0.8)
    ax.set_title(VAR_LABELS[var])
    ax.set_xlabel("")
    ax.set_ylabel("KGE" if ax in axes[:, 0] else "")
    ax.tick_params(axis="x", rotation=30)

fig.suptitle("KGE by Biome — ERA5 vs Xavier 2016", fontsize=14)
plt.tight_layout()
plt.savefig("outputs/figures/fig3_kge_boxplots.png", dpi=300, bbox_inches="tight")
print("[OK] outputs/figures/fig3_kge_boxplots.png")
