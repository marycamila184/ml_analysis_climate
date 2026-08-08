"""Download ERA5-Land hourly raw data via CDS API (1980-2025).

Consumer: `era5_reliability/` (Article 1) - this is the evaluated product.

ERA5-Land (dataset `reanalysis-era5-land`) is land-only, 0.1 deg (~9 km), hourly.
It has NO `product_type` field (unlike `reanalysis-era5-single-levels`). Downloads all
24 hours per day, per month, storing raw NetCDF without transformation. Original
ERA5-Land variable names are kept.

ERA5-Land does NOT provide ready-made daily max/min temperature nor relative humidity:
  - tasmax / tasmin are derived from hourly 2m_temperature (daily max/min).
  - hur is derived from 2m_temperature + 2m_dewpoint_temperature (Magnus/Tetens).

Variables downloaded (mapped to BR-DWGD for the article's variable-by-variable
comparison):
  Level 1 - minimum to run all of v1 with precipitation (Test A + Test B):
    tp    -> total_precipitation                      # pr
  Level 2 - to match the rest of BR-DWGD (Tmax, Tmin, Rs, RH, wind, ET0):
    temp  -> 2m_temperature, 2m_dewpoint_temperature  # tasmax, tasmin, hur
    ssrd  -> surface_solar_radiation_downwards        # Rs (incoming shortwave)
    wind  -> 10m_u_component_of_wind, 10m_v_component_of_wind  # sfcWind = sqrt(u^2+v^2)
    pev   -> potential_evaporation                    # ET0 (optional, see caveat)

Declared caveats (raised with advisor, not silently decided):
  - Wind: ERA5-Land is 10 m, BR-DWGD is 2 m -> log-profile conversion in preprocessing.
  - Radiation: ssrd is downward (incoming) shortwave, matching BR-DWGD "Rs". The
    project's `rss` convention historically meant NET solar radiation; here we use
    downward to compare like-for-like with BR-DWGD.
  - ET0: BR-DWGD ET0 is Penman-Monteith computed from observations, NOT the model's
    potential evaporation. They are not exactly the same quantity -> declare in the
    article.

Level 3 - hydrological land-state package. NOT downloaded now; recorded for Article 3 /
multivariate state. To enable, add these groups to GROUPS below:
    soil  -> volumetric_soil_water_layer_1 ... _4       # instantaneous
    runf  -> runoff, surface_runoff, sub_surface_runoff # accumulated (deaccumulate)
    evap  -> total_evaporation                          # accumulated (deaccumulate)
    skin  -> skin_temperature                           # instantaneous

Accumulated fields (tp, ssrd, pev) require deaccumulation before daily aggregation.

Output: {ERA5_LAND}/{group}/{group}_{year}_{month}.nc

Usage:
    uv run python -m ingest.era5.download_era5_land --workers 3
"""
import argparse

from ingest.common.cds_client import add_common_args, downloader_from_args
from ingest.era5.monthly import HOURLY, monthly_requests
from ingest.paths import ERA5_LAND

DATASET = "reanalysis-era5-land"

GROUPS = {
    # Level 1 + Level 2 (article variables, match BR-DWGD)
    "tp":   ["total_precipitation"],
    "temp": ["2m_temperature", "2m_dewpoint_temperature"],
    "wind": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
    "ssrd": ["surface_solar_radiation_downwards"],
    "pev":  ["potential_evaporation"],
    # Level 3 (hydrological land state) is documented above but NOT downloaded yet.
}

# 1980-2025, the BR-DWGD overlap - https://rmets.onlinelibrary.wiley.com/doi/10.1002/joc.7731
YEARS = [str(y) for y in range(1980, 2026)]

# Bounding box: N, W, S, E (Brazil)
AREA = [6, -75, -35, -30]


def main():
    parser = argparse.ArgumentParser(
        description="Download ERA5-Land hourly raw data via CDS API.")
    add_common_args(parser)
    parser.add_argument("--groups", nargs="+", choices=sorted(GROUPS), default=None,
                        help="variable groups to download (default: all)")
    args = parser.parse_args()

    groups = {g: GROUPS[g] for g in (args.groups or GROUPS)}
    print(f"ERA5-Land {YEARS[0]}-{YEARS[-1]}, groups: {', '.join(groups)}")

    # NOTE: ERA5-Land has no "product_type" field.
    downloader_from_args(args).run(
        monthly_requests(DATASET, ERA5_LAND, groups, YEARS, HOURLY, AREA))


if __name__ == "__main__":
    main()
