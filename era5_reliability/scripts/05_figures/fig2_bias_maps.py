"""
Figure 2 — Spatial relative bias maps: ERA5 vs Xavier (6 panels, one per variable).

Output: outputs/figures/fig2_bias_maps.png
"""
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr

VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
VAR_LABELS = {
    "pr":      "Precipitation (mm/day)",
    "tasmax":  "Tmax (°C)",
    "tasmin":  "Tmin (°C)",
    "rss":     "Solar Radiation (MJ/m²/day)",
    "sfcWind": "Wind Speed (m/s)",
    "hur":     "Relative Humidity (%)",
}

fig, axes = plt.subplots(2, 3, figsize=(15, 10),
                         subplot_kw={"projection": ccrs.PlateCarree()})

for ax, var in zip(axes.flat, VARIABLES):
    sim = xr.open_dataset(f"data/processed/era5/{var}.nc")[var]
    obs = xr.open_dataset(f"data/processed/xavier/{var}.nc")[var]
    bias = ((sim.mean("time") - obs.mean("time")) / obs.mean("time")) * 100

    im = bias.plot(
        ax=ax, transform=ccrs.PlateCarree(),
        cmap="RdBu_r", vmin=-30, vmax=30,
        add_colorbar=False,
    )
    ax.coastlines(linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_title(VAR_LABELS[var])

plt.colorbar(im, ax=axes, label="Relative bias (%)", shrink=0.6)
fig.suptitle("ERA5 vs Xavier 2016 — Relative Bias", fontsize=14)
plt.savefig("outputs/figures/fig2_bias_maps.png", dpi=300, bbox_inches="tight")
print("[OK] outputs/figures/fig2_bias_maps.png")
