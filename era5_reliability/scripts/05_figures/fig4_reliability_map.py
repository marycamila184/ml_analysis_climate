"""
Figure 4 — ERA5 Reliability Map for ML Training (6 panels, one per variable).

Color scheme: green=High, yellow=Moderate, red=Low confidence.

Output: outputs/figures/fig4_reliability_map.png
"""
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import xarray as xr
import numpy as np

VARIABLES = ["pr", "tasmax", "tasmin", "rss", "sfcWind", "hur"]
VAR_LABELS = {
    "pr": "Precipitation", "tasmax": "Tmax", "tasmin": "Tmin",
    "rss": "Solar Radiation", "sfcWind": "Wind Speed", "hur": "Relative Humidity",
}

cmap = mcolors.ListedColormap(["#d73027", "#fee090", "#1a9850"])
norm = mcolors.BoundaryNorm([0.5, 1.5, 2.5, 3.5], cmap.N)

fig, axes = plt.subplots(2, 3, figsize=(15, 10),
                         subplot_kw={"projection": ccrs.PlateCarree()})

for ax, var in zip(axes.flat, VARIABLES):
    cat = xr.open_dataset(f"outputs/reliability_map/category_{var}.nc")[f"category_{var}"]
    im = cat.plot(
        ax=ax, transform=ccrs.PlateCarree(),
        cmap=cmap, norm=norm,
        add_colorbar=False,
    )
    ax.coastlines(linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.set_title(VAR_LABELS[var])

cbar = plt.colorbar(im, ax=axes, ticks=[1, 2, 3], shrink=0.6)
cbar.set_ticklabels(["Low", "Moderate", "High"])
cbar.set_label("ERA5 Reliability for ML Training")

fig.suptitle("ERA5 Reliability Map — Brazil (1980–2013)", fontsize=14)
plt.savefig("outputs/figures/fig4_reliability_map.png", dpi=300, bbox_inches="tight")
print("[OK] outputs/figures/fig4_reliability_map.png")
