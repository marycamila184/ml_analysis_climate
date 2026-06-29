"""
Figure 1 — Brazil biome map overlaid with ERA5 grid.

Output: outputs/figures/fig1_biome_map.png
"""
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import xarray as xr

BIOME_COLORS = {
    "Amazônia":       "#2d8a2d",
    "Cerrado":        "#c8b400",
    "Caatinga":       "#c87800",
    "Mata Atlântica": "#1a6e1a",
    "Pampa":          "#7ec87e",
    "Pantanal":       "#1464c8",
}

shp = gpd.read_file("data/raw/biomes/biomas_250mil.shp").to_crs("EPSG:4326")
grid = xr.open_dataset("data/processed/era5/pr.nc").isel(time=0)

fig, ax = plt.subplots(figsize=(8, 9), subplot_kw={"projection": ccrs.PlateCarree()})
ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
ax.add_feature(cfeature.BORDERS, linewidth=0.5)

for biome_name, color in BIOME_COLORS.items():
    subset = shp[shp["Bioma"] == biome_name]
    subset.plot(ax=ax, color=color, alpha=0.6, transform=ccrs.PlateCarree(), label=biome_name)

# ERA5 grid overlay
lats = grid.lat.values[::4]
lons = grid.lon.values[::4]
for lat in lats:
    ax.axhline(lat, color="gray", linewidth=0.2, alpha=0.4, transform=ccrs.PlateCarree())
for lon in lons:
    ax.axvline(lon, color="gray", linewidth=0.2, alpha=0.4, transform=ccrs.PlateCarree())

ax.set_title("Brazil Biomes and ERA5 Grid (0.25°)")
ax.legend(loc="lower left", fontsize=7)
plt.savefig("outputs/figures/fig1_biome_map.png", dpi=300, bbox_inches="tight")
print("[OK] outputs/figures/fig1_biome_map.png")
