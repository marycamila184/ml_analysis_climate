"""Download ERA5 synoptic fields for regime classification (1980-2025).

Consumer: `som_ais_extremes/` - these are the SOM's input fields. Nothing else in the
repository uses them, and no existing download covers them.

Two CDS datasets, 6-hourly at 00/06/12/18 UTC, over South/Southeast Brazil:

  reanalysis-era5-pressure-levels
    plev500 -> geopotential                        @ 500 hPa  # troughs and ridges
    plev850 -> temperature, specific_humidity,                # air masses, fronts,
               u/v_component_of_wind               @ 850 hPa  # moisture, low-level jet
    plev250 -> u/v_component_of_wind               @ 250 hPa  # subtropical jet

  reanalysis-era5-single-levels
    single  -> mean_sea_level_pressure                        # system position
               total_column_water_vapour                      # available moisture
               convective_available_potential_energy          # convective instability

The single-level group is named `single`, not `sfc`, to keep it distinct from
`download_era5_sfc.py` - a different script, for a different project, over a different
box. Nothing here is shared with it.

Variables are grouped by pressure level rather than one request per field, because a
CDS pressure-level request is a cross product of `variable` x `pressure_level`. Three
requests per month cover all seven variable-levels.

Deliberate choices, both worth knowing before re-running this:

  - 6-hourly, not hourly. Synoptic regime classification is conventionally done at the
    four main synoptic hours. Hourly would be 6x the volume for no methodological gain.
    (Article 1 needs hourly because it derives daily max/min; this project does not.)
  - Native 0.25 deg, regridded to 1.0-1.5 deg locally in 02_preprocessing rather than
    server-side via the CDS `grid` key. The full retrieval is only ~20 GB, and keeping
    native resolution allows testing regime sensitivity to grid spacing without a
    second multi-day download.

Region defaults to the plan's South/Southeast box. Covering all of Brazil multiplies
the volume and dilutes the synoptic regimes, which are regional. If the phase-0
extreme-event count comes up short, widening the box with --area is the documented
mitigation - do it before anything is built on top of the regimes, not after.

ERA5-Land is deliberately NOT used here: it is land-only, and SACZ, frontal systems and
the subtropical jet are defined partly over the Atlantic.

Output: {ERA5_SYNOPTIC}/{group}/{group}_{year}_{month}.nc

Usage:
    uv run python -m ingest.era5.download_era5_synoptic --years 1980 1980   # test month
    uv run python -m ingest.era5.download_era5_synoptic --workers 3
"""
import argparse

from ingest.common.cds_client import add_common_args, downloader_from_args
from ingest.era5.monthly import SIX_HOURLY, monthly_requests
from ingest.paths import ERA5_SYNOPTIC

PRESSURE_DATASET = "reanalysis-era5-pressure-levels"
SINGLE_DATASET = "reanalysis-era5-single-levels"

PRESSURE_GROUPS = {
    "plev500": {
        "variable":       ["geopotential"],
        "pressure_level": ["500"],
    },
    "plev850": {
        "variable":       ["temperature", "specific_humidity",
                           "u_component_of_wind", "v_component_of_wind"],
        "pressure_level": ["850"],
    },
    "plev250": {
        "variable":       ["u_component_of_wind", "v_component_of_wind"],
        "pressure_level": ["250"],
    },
}

SINGLE_GROUPS = {
    "single": ["mean_sea_level_pressure",
               "total_column_water_vapour",
               "convective_available_potential_energy"],
}

ALL_GROUPS = sorted({**PRESSURE_GROUPS, **SINGLE_GROUPS})

# 1980-2025: train 1980-2014, test 2015-2025 (see som_ais_extremes/README.md).
DEFAULT_YEARS = (1980, 2025)

# Bounding box: N, W, S, E - South/Southeast Brazil.
DEFAULT_AREA = [-14, -60, -35, -38]


def main():
    parser = argparse.ArgumentParser(
        description="Download ERA5 synoptic fields (pressure + single level) via CDS.")
    add_common_args(parser)
    parser.add_argument("--groups", nargs="+", choices=ALL_GROUPS, default=None,
                        help="variable groups to download (default: all)")
    parser.add_argument("--years", nargs=2, type=int, metavar=("FIRST", "LAST"),
                        default=DEFAULT_YEARS,
                        help=f"inclusive year range (default: {DEFAULT_YEARS[0]} "
                             f"{DEFAULT_YEARS[1]})")
    parser.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"),
                        default=DEFAULT_AREA,
                        help=f"bounding box (default: {DEFAULT_AREA})")
    args = parser.parse_args()

    selected = set(args.groups or ALL_GROUPS)
    years = [str(y) for y in range(args.years[0], args.years[1] + 1)]

    print(f"ERA5 synoptic {years[0]}-{years[-1]}, area {args.area}, "
          f"groups: {', '.join(sorted(selected))}")

    requests = []
    pressure = {g: s for g, s in PRESSURE_GROUPS.items() if g in selected}
    if pressure:
        requests += monthly_requests(
            PRESSURE_DATASET, ERA5_SYNOPTIC, pressure, years, SIX_HOURLY, args.area,
            extra={"product_type": "reanalysis"})

    single = {g: s for g, s in SINGLE_GROUPS.items() if g in selected}
    if single:
        requests += monthly_requests(
            SINGLE_DATASET, ERA5_SYNOPTIC, single, years, SIX_HOURLY, args.area,
            extra={"product_type": "reanalysis"})

    downloader_from_args(args).run(requests)


if __name__ == "__main__":
    main()
