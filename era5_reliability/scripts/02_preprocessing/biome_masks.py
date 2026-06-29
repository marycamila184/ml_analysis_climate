"""
Generate a raster mask of Brazil's 6 biomes from the IBGE shapefile.

Download shapefile from:
  https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html

Output: data/processed/biome_mask.nc
  Variable 'biome': int8 raster aligned to ERA5 grid
  Values: 1=Amazon, 2=Cerrado, 3=Caatinga, 4=Atlantic Forest, 5=Pampa, 6=Pantanal
"""
import geopandas as gpd
import xarray as xr
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_bounds

BIOMES = {
    "Amazônia":       1,
    "Cerrado":        2,
    "Caatinga":       3,
    "Mata Atlântica": 4,
    "Pampa":          5,
    "Pantanal":       6,
}

shp = gpd.read_file("data/raw/biomes/biomas_250mil.shp").to_crs("EPSG:4326")

grid = xr.open_dataset("data/processed/era5/pr.nc").isel(time=0)
lats = grid.lat.values
lons = grid.lon.values

transform = from_bounds(lons.min(), lats.min(), lons.max(), lats.max(), len(lons), len(lats))
mask = np.zeros((len(lats), len(lons)), dtype=np.int8)

for biome_name, biome_id in BIOMES.items():
    geom = shp[shp["Bioma"] == biome_name].geometry
    shapes = [(g, biome_id) for g in geom]
    rasterize(shapes, out=mask, transform=transform, merge_alg="replace")

da = xr.DataArray(mask, coords=[lats, lons], dims=["lat", "lon"], name="biome")
da.attrs["biome_legend"] = "1=Amazon 2=Cerrado 3=Caatinga 4=Atlantic Forest 5=Pampa 6=Pantanal"
da.to_netcdf("data/processed/biome_mask.nc")
print("[OK] Biome mask saved to data/processed/biome_mask.nc")
