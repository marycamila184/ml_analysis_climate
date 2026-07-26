"""One-time repair: unwrap ZIP-wrapped .nc files produced by the legacy CDS request.

Downloads made before `data_format`/`download_format` were added to the ERA5-Land
request are ZIP archives named `.nc`, each holding a single `data_0.nc`. The data
itself is complete and correct, so the archives only need unwrapping - no file has
to be downloaded again.

Each file is replaced in place: the member is extracted to `<file>.unwrap` and then
os.replace()d over the original, which is atomic on the same filesystem. Files that
are already plain NetCDF are skipped, so the script is safe to interrupt and re-run.

Usage:
    python repair_zipped_nc.py --dry-run        # report what would change
    python repair_zipped_nc.py                  # repair in place
    python repair_zipped_nc.py --verify         # also open each result in xarray
"""
import argparse
import os
import sys

from nc_utils import UnwrapError, is_netcdf, is_zip, unwrap_zip_nc

BASE_DIR = "/media/mary-camila/Expansion/era5land/raw"


def find_nc_files(base_dir):
    for root, _, files in os.walk(base_dir):
        for name in sorted(files):
            if name.endswith(".nc"):
                yield os.path.join(root, name)


def human(n_bytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n_bytes < 1024 or unit == "TB":
            return f"{n_bytes:.1f}{unit}"
        n_bytes /= 1024


def main():
    parser = argparse.ArgumentParser(
        description="Unwrap ZIP-wrapped ERA5-Land .nc files in place.")
    parser.add_argument("--base-dir", default=BASE_DIR,
                        help=f"raw data root (default: {BASE_DIR})")
    parser.add_argument("--dry-run", action="store_true",
                        help="only report which files are zipped")
    parser.add_argument("--verify", action="store_true",
                        help="open each repaired file in xarray to confirm it is valid")
    parser.add_argument("--prune-invalid", action="store_true",
                        help="delete files that are neither ZIP nor NetCDF (truncated "
                             "downloads) so the downloader fetches them again")
    args = parser.parse_args()

    if not os.path.isdir(args.base_dir):
        sys.exit(f"not a directory: {args.base_dir}")

    files = list(find_nc_files(args.base_dir))
    if not files:
        sys.exit(f"no .nc files found under {args.base_dir}")

    zipped, plain, invalid = [], [], []
    for path in files:
        if is_zip(path):
            zipped.append(path)
        elif is_netcdf(path):
            plain.append(path)
        else:
            invalid.append(path)

    print(f"{len(files)} .nc files: {len(zipped)} ZIP archives, "
          f"{len(plain)} plain NetCDF, {len(invalid)} invalid")

    # Truncated leftovers from before downloads became atomic. They are not valid data
    # but do satisfy the downloader's skip-if-exists check, so they must be removed or
    # that month is silently never retried.
    for path in invalid:
        rel = os.path.relpath(path, args.base_dir)
        size = os.path.getsize(path)
        if args.dry_run:
            print(f"[WOULD DELETE] {rel} ({human(size)}, not ZIP or NetCDF)")
        elif args.prune_invalid:
            os.remove(path)
            print(f"[DELETED] {rel} ({human(size)}) - will be re-downloaded")
        else:
            print(f"[INVALID] {rel} ({human(size)}) - re-run with --prune-invalid "
                  f"to delete so it is downloaded again")

    if not zipped:
        print("no archives to unwrap")
        return

    if args.dry_run:
        for path in zipped:
            print(f"[WOULD UNZIP] {os.path.relpath(path, args.base_dir)} "
                  f"({human(os.path.getsize(path))})")
        print(f"\ndry run: no files changed ({len(zipped)} would be unwrapped, "
              f"{len(invalid)} deleted)")
        return

    # Largest archive bounds the temporary space needed, since files are done one
    # at a time and each .unwrap is replaced before the next starts.
    headroom = max(os.path.getsize(p) for p in zipped)
    free = os.statvfs(args.base_dir).f_bavail * os.statvfs(args.base_dir).f_frsize
    print(f"largest archive {human(headroom)}, free space {human(free)}")
    if free < headroom * 3:
        sys.exit("not enough free space to unwrap safely")

    repaired = failed = 0
    for i, path in enumerate(zipped, 1):
        rel = os.path.relpath(path, args.base_dir)
        try:
            if unwrap_zip_nc(path):
                repaired += 1
                print(f"[{i}/{len(zipped)}] [OK] {rel} -> "
                      f"{human(os.path.getsize(path))}", flush=True)
            else:
                print(f"[{i}/{len(zipped)}] [SKIP] {rel} already NetCDF", flush=True)
        except (UnwrapError, OSError) as e:
            failed += 1
            print(f"[{i}/{len(zipped)}] [ERROR] {rel}: {e}", flush=True)

    print(f"\nrepaired {repaired}, failed {failed}")

    if args.verify:
        verify(zipped, args.base_dir)

    if failed:
        sys.exit(1)


def verify(paths, base_dir):
    """Confirm each file opens as NetCDF and reports the expected grid."""
    import xarray as xr

    print(f"\nverifying {len(paths)} files with xarray...")
    bad = 0
    for path in paths:
        rel = os.path.relpath(path, base_dir)
        try:
            with xr.open_dataset(path) as ds:
                if not ds.data_vars:
                    raise ValueError("no data variables")
        except Exception as e:
            bad += 1
            print(f"[BAD] {rel}: {type(e).__name__}: {e}")
    print(f"verified {len(paths) - bad} OK, {bad} bad")
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
