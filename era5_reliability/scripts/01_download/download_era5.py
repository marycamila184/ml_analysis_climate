"""
Download ERA5 hourly raw data via CDS API (1980-2013).

Downloads all 24 hours per day, per month, storing raw NetCDF files
without any transformation. Variable names are kept as original ERA5 names.

CDS groups (one request per group per month):
  tp   -> total_precipitation
  temp -> 2m_temperature + 2m_dewpoint_temperature
  wind -> 10m_u_component_of_wind + 10m_v_component_of_wind
  ssr  -> surface_net_solar_radiation

Output: /media/mary-camila/Expansion/era5/raw/{group}/{group}_{year}_{month}.nc
"""
import cdsapi
import os
import time
import calendar

BASE_DIR = "/media/mary-camila/Expansion/era5/raw"

GROUPS = {
    "tp":   ["total_precipitation"],
    "temp": ["2m_temperature", "2m_dewpoint_temperature"],
    "wind": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
    "ssr":  ["surface_net_solar_radiation"],
}

YEARS  = [str(y) for y in range(1980, 2014)]
MONTHS = [f"{m:02d}" for m in range(1, 13)]
HOURS  = [f"{h:02d}:00" for h in range(24)]

# Bounding box: N, W, S, E (Brazil)
AREA = [6, -75, -35, -30]

for group in GROUPS:
    os.makedirs(os.path.join(BASE_DIR, group), exist_ok=True)

client = cdsapi.Client(timeout=600)


def get_days(year, month):
    n_days = calendar.monthrange(int(year), int(month))[1]
    return [f"{d:02d}" for d in range(1, n_days + 1)]


def download_group(group, variables, year, month):
    out_file = os.path.join(BASE_DIR, group, f"{group}_{year}_{month}.nc")

    if os.path.exists(out_file):
        print(f"[SKIP] {group} {year}-{month}")
        return

    days = get_days(year, month)

    for attempt in range(3):
        try:
            print(f"[DOWNLOAD] {group} {year}-{month}")
            client.retrieve(
                "reanalysis-era5-single-levels",
                {
                    "product_type": "reanalysis",
                    "variable":     variables,
                    "year":         year,
                    "month":        month,
                    "day":          days,
                    "time":         HOURS,
                    "area":         AREA,
                    "format":       "netcdf",
                },
                out_file,
            )
            print(f"[OK] {group} {year}-{month}")
            return
        except Exception as e:
            print(f"[RETRY] {group} {year}-{month}, attempt {attempt + 1}: {e}")
            time.sleep(20)

    print(f"[ERROR] {group} {year}-{month} failed after 3 attempts")
    with open(os.path.join(BASE_DIR, "errors.log"), "a") as log:
        log.write(f"{group} {year}-{month}\n")


for year in YEARS:
    print(f"\n=== YEAR {year} ===")
    for month in MONTHS:
        for group, variables in GROUPS.items():
            download_group(group, variables, year, month)
