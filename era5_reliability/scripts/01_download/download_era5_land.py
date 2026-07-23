"""
Download ERA5-Land hourly raw data via CDS API (1980-2013).

ERA5-Land (dataset `reanalysis-era5-land`) is land-only, 0.1 deg (~9 km), hourly.
It has NO `product_type` field (unlike `reanalysis-era5-single-levels`). Downloads all
24 hours per day, per month, storing raw NetCDF without transformation. Original ERA5-Land
variable names are kept.

ERA5-Land does NOT provide ready-made daily max/min temperature nor relative humidity:
  - tasmax / tasmin are derived from hourly 2m_temperature (daily max/min).
  - hur is derived from 2m_temperature + 2m_dewpoint_temperature (Magnus/Tetens).

Variables downloaded (mapped to BR-DWGD for the article's variable-by-variable comparison):
  Level 1 — minimum to run all of v1 with precipitation (Test A + Test B):
    tp    -> total_precipitation                      # pr
  Level 2 — to match the rest of BR-DWGD (Tmax, Tmin, Rs, RH, wind, ET0):
    temp  -> 2m_temperature, 2m_dewpoint_temperature  # tasmax, tasmin, hur
    ssrd  -> surface_solar_radiation_downwards        # Rs (incoming shortwave)
    wind  -> 10m_u_component_of_wind, 10m_v_component_of_wind   # sfcWind = sqrt(u^2+v^2)
    pev   -> potential_evaporation                    # ET0 (optional, see caveat)

Declared caveats (raised with advisor, not silently decided):
  - Wind: ERA5-Land is 10 m, BR-DWGD is 2 m -> log-profile conversion in preprocessing.
  - Radiation: ssrd is downward (incoming) shortwave, matching BR-DWGD "Rs". The project's
    `rss` convention historically meant NET solar radiation; here we use downward to compare
    like-for-like with BR-DWGD.
  - ET0: BR-DWGD ET0 is Penman-Monteith computed from observations, NOT the model's
    potential evaporation. They are not exactly the same quantity -> declare in the article.

Level 3 — hydrological land-state package. NOT downloaded now; recorded for Article 3 /
multivariate state. To enable, add these groups to GROUPS below:
    soil  -> volumetric_soil_water_layer_1 ... _4       # instantaneous
    runf  -> runoff, surface_runoff, sub_surface_runoff # accumulated (deaccumulate)
    evap  -> total_evaporation                          # accumulated (deaccumulate)
    skin  -> skin_temperature                           # instantaneous

Accumulated fields (tp, ssrd, pev) require deaccumulation before daily aggregation.

Output: /media/mary-camila/Expansion/era5land/raw/{group}/{group}_{year}_{month}.nc
"""
import cdsapi
import os
import time
import calendar

BASE_DIR = "/media/mary-camila/Expansion/era5land/raw"

GROUPS = {
    # Level 1 + Level 2 (article variables, match BR-DWGD)
    "tp":   ["total_precipitation"],
    "temp": ["2m_temperature", "2m_dewpoint_temperature"],
    "wind": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
    "ssrd": ["surface_solar_radiation_downwards"],
    "pev":  ["potential_evaporation"],
    # Level 3 (hydrological land state) is documented below but NOT downloaded yet.
}

YEARS  = [str(y) for y in range(1980, 2014)]  # 1980-2013 (BR-DWGD overlap)
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
                "reanalysis-era5-land",
                {
                    # NOTE: ERA5-Land has no "product_type" field.
                    "variable": variables,
                    "year":     year,
                    "month":    month,
                    "day":      days,
                    "time":     HOURS,
                    "area":     AREA,
                    "format":   "netcdf",
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
