"""Report what is actually on disk against what the download scripts declare.

The point is that nothing here is written down twice. Expected coverage is imported
from the download modules themselves - their GROUPS and YEARS - so this report cannot
drift from what the scripts would actually fetch. A hand-maintained inventory table in
a README goes stale on the next run; this does not.

Usage:
    uv run python -m ingest.status                # summary per group
    uv run python -m ingest.status --missing      # also list the missing months
    uv run python -m ingest.status --no-size      # skip the disk walk (faster)
"""
import argparse
import os

from ingest.era5 import download_era5_land, download_era5_sfc, download_era5_synoptic
from ingest.era5.monthly import ALL_MONTHS
from ingest.paths import BRDWGD, CLIMBRA, ERA5_LAND, ERA5_SFC, ERA5_SYNOPTIC

# Monthly-chunked datasets, described by the module that downloads them.
MONTHLY = [
    ("ERA5-Land 0.1deg", ERA5_LAND,
     download_era5_land.GROUPS, download_era5_land.YEARS),
    ("ERA5 0.25deg sfc", ERA5_SFC,
     download_era5_sfc.GROUPS, download_era5_sfc.YEARS),
    ("ERA5 synoptic", ERA5_SYNOPTIC,
     {**download_era5_synoptic.PRESSURE_GROUPS, **download_era5_synoptic.SINGLE_GROUPS},
     [str(y) for y in range(download_era5_synoptic.DEFAULT_YEARS[0],
                            download_era5_synoptic.DEFAULT_YEARS[1] + 1)]),
]

# Datasets that are not month-chunked, so only presence and size are meaningful.
FLAT = [("BR-DWGD v3.2.4", BRDWGD), ("CLIMBra V5", CLIMBRA)]


def human(n_bytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n_bytes < 1024 or unit == "TB":
            return f"{n_bytes:.0f}{unit}"
        n_bytes /= 1024


def tree_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += os.stat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def spans(months):
    """Collapse a sorted YYYY_MM list into readable contiguous ranges."""
    if not months:
        return "-"
    out, start, prev = [], months[0], months[0]
    for m in months[1:]:
        y, mm = int(prev[:4]), int(prev[5:])
        nxt = f"{y + 1}_01" if mm == 12 else f"{y}_{mm + 1:02d}"
        if m != nxt:
            out.append((start, prev))
            start = m
        prev = m
    out.append((start, prev))
    return ", ".join(a if a == b else f"{a}..{b}" for a, b in out)


def report_monthly(name, base, groups, years, show_missing, show_size):
    expected = [f"{y}_{m}" for y in years for m in ALL_MONTHS]
    print(f"\n{name}  ({years[0]}-{years[-1]}, {len(expected)} months/group)")
    print(f"  {base}")

    if not os.path.isdir(base):
        print(f"  not downloaded - {len(groups)} groups x {len(expected)} months")
        return

    for group in groups:
        d = os.path.join(base, group)
        if not os.path.isdir(d):
            print(f"  {group:8s} not downloaded ({len(expected)} months)")
            continue

        have = {f[len(group) + 1:-3] for f in os.listdir(d)
                if f.startswith(group + "_") and f.endswith(".nc")}
        missing = [m for m in expected if m not in have]
        size = f"  {human(tree_size(d)):>6s}" if show_size else ""
        state = "complete" if not missing else f"missing {len(missing):3d}"
        print(f"  {group:8s} {len(have):3d}/{len(expected)}  {state}{size}")
        if missing and show_missing:
            print(f"           gaps: {spans(missing)}")


def report_flat(name, base, show_size):
    print(f"\n{name}")
    print(f"  {base}")
    if not os.path.isdir(base):
        print("  not downloaded")
        return
    n = sum(len(files) for _, _, files in os.walk(base))
    size = f", {human(tree_size(base))}" if show_size else ""
    print(f"  {n} files{size}")


def main():
    parser = argparse.ArgumentParser(
        description="Report raw data coverage against what the download scripts declare.")
    parser.add_argument("--missing", action="store_true",
                        help="list the missing months, collapsed into ranges")
    parser.add_argument("--no-size", action="store_true",
                        help="skip the disk walk (much faster on large trees)")
    args = parser.parse_args()

    show_size = not args.no_size
    for name, base, groups, years in MONTHLY:
        report_monthly(name, base, groups, years, args.missing, show_size)
    for name, base in FLAT:
        report_flat(name, base, show_size)
    print()


if __name__ == "__main__":
    main()
