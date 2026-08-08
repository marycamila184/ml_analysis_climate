"""Filesystem roots for raw data.

Single source of truth for where every raw dataset lives. Both the download scripts
in `ingest/` and the preprocessing stages in the project folders import from here,
so a drive that gets remounted somewhere else is a one-line change.

Raw data is never written inside the repository: it lives on the external drive and
is git-ignored.
"""
import os

# Override for a differently mounted drive without editing this file.
DRIVE = os.environ.get("CLIMATE_DATA_ROOT", "/media/mary-camila/Expansion")

# ERA5 0.25 deg single levels, hourly - Article 1 secondary dataset.
ERA5_SFC = os.path.join(DRIVE, "era5", "raw")

# ERA5-Land 0.1 deg, land-only, hourly - Article 1 evaluated product.
ERA5_LAND = os.path.join(DRIVE, "era5land", "raw")

# ERA5 0.25 deg synoptic fields, 6-hourly - som_ais_extremes predictors.
#   plev/ pressure levels (z500, t850, q850, u/v 850, u/v 250)
#   sfc/  single levels   (msl, tcwv, cape)
ERA5_SYNOPTIC = os.path.join(DRIVE, "era5_synoptic", "raw")

# BR-DWGD v3.2.4 daily, 0.1 deg - observational reference for both projects.
BRDWGD = os.path.join(DRIVE, "brdwgd", "raw")

# CLIMBra V5 bias-corrected CMIP6 projections.
CLIMBRA = os.path.join(DRIVE, "climbra")
