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

Requests are I/O-bound: nearly all wall-clock time is CDS queueing and MARS tape
retrieval, not local bandwidth. Downloads therefore run in a thread pool
(`--workers`, default 3) with one cdsapi.Client per thread, since a Client is not
documented as thread-safe. Request starts are throttled to one every `--delay`
seconds (default 5) across all workers, to stay clear of CDS rate limiting.

Output: /media/mary-camila/Expansion/era5land/raw/{group}/{group}_{year}_{month}.nc
"""
import argparse
import cdsapi
import os
import threading
import time
import calendar
from concurrent.futures import ThreadPoolExecutor

from nc_utils import unwrap_zip_nc

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

# A cdsapi.Client is not documented as thread-safe, so each worker thread gets its own.
_local = threading.local()

# Guards stdout and errors.log against interleaved writes from concurrent workers.
_lock = threading.Lock()

# Separate lock for the rate limiter: it is held across a sleep, so it must not be the
# same lock that guards logging or workers would block waiting to print.
_rate_lock = threading.Lock()
_last_request = 0.0

_delay = 5.0
_retry_max = 10
_done = 0
_total = 0


def get_client():
    if not hasattr(_local, "client"):
        # cdsapi defaults to retry_max=500 with sleep_max=120, i.e. it keeps retrying a
        # connection error for ~16 h while holding the worker, so this script's own retry
        # loop never runs and nothing reaches errors.log. Cap it low enough that a truly
        # stuck request fails, gets retried here, and finally lands in errors.log for a
        # later pass instead of stalling the run. Only connection errors and timeouts
        # count against it - a job legitimately sitting in the CDS queue is not affected.
        _local.client = cdsapi.Client(timeout=600, retry_max=_retry_max)
    return _local.client


def throttle():
    """Enforce a minimum gap between consecutive CDS requests, across all workers.

    Spaces out request *starts* globally rather than sleeping per worker, so the pace
    stays the same no matter how many workers are running.
    """
    global _last_request
    with _rate_lock:
        wait = _delay - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()


def log(message):
    """Report a finished task, advancing the progress counter.

    Prints one whole line at a time so concurrent workers do not shred each other.
    """
    global _done
    with _lock:
        _done += 1
        print(f"[{_done}/{_total}] {message}", flush=True)


def note(message):
    """Print an interim message without advancing the progress counter."""
    with _lock:
        print(message, flush=True)


def get_days(year, month):
    n_days = calendar.monthrange(int(year), int(month))[1]
    return [f"{d:02d}" for d in range(1, n_days + 1)]


def download_group(group, variables, year, month):
    out_file = os.path.join(BASE_DIR, group, f"{group}_{year}_{month}.nc")

    if os.path.exists(out_file):
        log(f"[SKIP] {group} {year}-{month}")
        return

    # Retrieve to a temporary name and rename only on success: os.replace is atomic on
    # the same filesystem, so a file at the final path is always a complete download and
    # the skip-if-exists check above can never resume onto a truncated file.
    part_file = out_file + ".part"
    days = get_days(year, month)

    for attempt in range(3):
        try:
            throttle()
            get_client().retrieve(
                "reanalysis-era5-land",
                {
                    # NOTE: ERA5-Land has no "product_type" field.
                    "variable": variables,
                    "year":     year,
                    "month":    month,
                    "day":      days,
                    "time":     HOURS,
                    "area":     AREA,
                    # New CDS API: `format` is legacy and silently ignored, and
                    # download_format defaults to "zip". Both keys are required to
                    # get a plain NetCDF back instead of a zipped one.
                    "data_format":     "netcdf",
                    "download_format": "unarchived",
                },
                part_file,
            )
            # Safety net in case CDS returns a zip anyway (see nc_utils).
            if unwrap_zip_nc(part_file):
                note(f"[UNZIP] {group} {year}-{month} (CDS returned a zip)")
            os.replace(part_file, out_file)
            log(f"[OK] {group} {year}-{month}")
            return
        except Exception as e:
            note(f"[RETRY] {group} {year}-{month}, attempt {attempt + 1}: {e}")
            time.sleep(20)

    log(f"[ERROR] {group} {year}-{month} failed after 3 attempts")
    with _lock:
        with open(os.path.join(BASE_DIR, "errors.log"), "a") as errlog:
            errlog.write(f"{group} {year}-{month}\n")


def main():
    global _total, _delay, _retry_max

    parser = argparse.ArgumentParser(
        description="Download ERA5-Land hourly raw data via CDS API (1980-2013).")
    parser.add_argument("--workers", type=int, default=3,
                        help="concurrent CDS requests (default: 3)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="minimum seconds between requests (default: 5)")
    parser.add_argument("--retry-max", type=int, default=10,
                        help="cdsapi connection retries per request, 120s apart "
                             "(default: 10; cdsapi's own default of 500 is ~16h)")
    parser.add_argument("--groups", nargs="+", choices=sorted(GROUPS), default=None,
                        help="variable groups to download (default: all)")
    args = parser.parse_args()

    _delay = args.delay
    _retry_max = args.retry_max

    groups = {g: GROUPS[g] for g in (args.groups or GROUPS)}

    for group in groups:
        os.makedirs(os.path.join(BASE_DIR, group), exist_ok=True)

    # Year-major ordering so a partial run finishes the earliest years first.
    tasks = [
        (group, variables, year, month)
        for year in YEARS
        for month in MONTHS
        for group, variables in groups.items()
    ]
    _total = len(tasks)

    print(f"{_total} requests over {', '.join(groups)} "
          f"({YEARS[0]}-{YEARS[-1]}) with {args.workers} workers, "
          f"{args.delay:g}s between requests")

    pool = ThreadPoolExecutor(max_workers=args.workers)
    try:
        for task in tasks:
            pool.submit(download_group, *task)
        pool.shutdown(wait=True)
    except KeyboardInterrupt:
        # Drop the queued months immediately instead of draining them. Requests already
        # in flight cannot be cancelled, so they still finish (or leave a .part behind,
        # which the next run overwrites); without cancel_futures the pool would work
        # through every remaining month before exiting.
        print("\ninterrupted: cancelling queued requests, "
              "waiting for in-flight downloads...", flush=True)
        pool.shutdown(wait=True, cancel_futures=True)
        print("stopped. re-run to resume where this left off.", flush=True)


if __name__ == "__main__":
    main()
