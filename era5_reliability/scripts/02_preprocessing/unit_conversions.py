"""
Apply unit conversions to align ERA5 with Xavier and BR-DWGD.

ERA5 raw units -> target units:
  tp  : m/day  -> mm/day  (x1000)
  ssr : J/m2   -> MJ/m2/day  (/1e6)
  hur : derived from 2m_temperature + 2m_dewpoint_temperature via Magnus equation

Note: the downloads in `ingest/` store raw NetCDF untransformed, so these conversions
belong to the hourly deaccumulation path in this stage. Run this script standalone only
if ERA5 was obtained as daily data.
"""
import xarray as xr
import numpy as np

# Precipitation: m -> mm
ds = xr.open_dataset("data/processed/era5/pr.nc")
ds["pr"] = ds["tp"] * 1000
ds.to_netcdf("data/processed/era5/pr.nc")

# Solar radiation: J/m2 -> MJ/m2/day
ds = xr.open_dataset("data/processed/era5/rss.nc")
ds["rss"] = ds["ssr"] / 1e6
ds.to_netcdf("data/processed/era5/rss.nc")

# Relative humidity: Magnus equation from air temp + dewpoint
ds_t  = xr.open_dataset("data/processed/era5/t2m.nc")
ds_td = xr.open_dataset("data/processed/era5/d2m.nc")
T  = ds_t["t2m"] - 273.15
Td = ds_td["d2m"] - 273.15
es = 6.112 * np.exp((17.67 * T)  / (T  + 243.5))
e  = 6.112 * np.exp((17.67 * Td) / (Td + 243.5))
hur = (e / es * 100).clip(0, 100)
hur.name = "hur"
hur.to_netcdf("data/processed/era5/hur.nc")

print("[OK] Unit conversions complete")
