"""Download ERA5 0.25 deg single-level hourly raw data via CDS API (1980-2025).

Consumer: `era5_reliability/` (Article 1) - secondary dataset, NOT the evaluated
product. ERA5-Land 0.1 deg is the product; see `download_era5_land.py`.

Downloads all 24 hours per day, per month, storing raw NetCDF without any
transformation. Variable names are kept as original ERA5 names.

  tp   -> total_precipitation                                  # pr
  temp -> 2m_temperature, 2m_dewpoint_temperature              # tasmax, tasmin, hur
  wind -> 10m_u_component_of_wind, 10m_v_component_of_wind     # sfcWind
  ssrd -> surface_solar_radiation_downwards                    # rss (use this one)
  ssr  -> surface_net_solar_radiation                          # legacy, see below

Radiation: BR-DWGD's Rs is INCOMING shortwave at the surface - what a station pyranometer
measures. `ssr` is NET shortwave (downward minus reflected), so it carries the model's
surface albedo inside it and is not a like-for-like match. `ssrd` is. The ERA5-Land script
uses `ssrd` for this reason.

`ssr` is kept because it is already downloaded (12 GB) and deleting it gains nothing:
`ssrd - ssr` is the reflected component, which diagnoses how much of any radiation bias is
an albedo artefact rather than an irradiance error. Use `ssrd` for the comparison, `ssr`
only for that diagnostic.

Output: {ERA5_SFC}/{group}/{group}_{year}_{month}.nc

Usage:
    uv run python -m ingest.era5.download_era5_sfc --workers 3
"""
import argparse

from ingest.common.cds_client import add_common_args, downloader_from_args
from ingest.era5.monthly import HOURLY, monthly_requests
from ingest.paths import ERA5_SFC

DATASET = "reanalysis-era5-single-levels"

GROUPS = {
    "tp":   ["total_precipitation"],
    "temp": ["2m_temperature", "2m_dewpoint_temperature"],
    "wind": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
    "ssrd": ["surface_solar_radiation_downwards"],
    "ssr":  ["surface_net_solar_radiation"],
}

YEARS = [str(y) for y in range(1980, 2026)]

# Bounding box: N, W, S, E (Brazil)
AREA = [6, -75, -35, -30]


def main():
    parser = argparse.ArgumentParser(
        description="Download ERA5 0.25 deg single-level hourly data via CDS API.")
    add_common_args(parser)
    parser.add_argument("--groups", nargs="+", choices=sorted(GROUPS), default=None,
                        help="variable groups to download (default: all)")
    args = parser.parse_args()

    groups = {g: GROUPS[g] for g in (args.groups or GROUPS)}
    print(f"ERA5 single levels {YEARS[0]}-{YEARS[-1]}, groups: {', '.join(groups)}")

    downloader_from_args(args).run(
        monthly_requests(DATASET, ERA5_SFC, groups, YEARS, HOURLY, AREA,
                         extra={"product_type": "reanalysis"}))


if __name__ == "__main__":
    main()
