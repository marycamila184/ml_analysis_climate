"""Helpers for normalizing CDS downloads to plain NetCDF.

The new CDS API renamed `format` to `data_format` and defaults `download_format`
to `zip`. A request that still sends the legacy `format` key silently receives a
ZIP archive, even though the target filename ends in `.nc`. Such a file is not
readable by xarray, so it must be unwrapped before preprocessing.

Requests now ask for `download_format: "unarchived"`, but `unwrap_zip_nc` is kept
as a safety net (and to repair files already on disk) because CDS has changed this
contract once already.
"""
import os
import zipfile

ZIP_MAGIC = b"PK\x03\x04"
# netCDF4 files are HDF5 ("\x89HDF"); netCDF3 classic/64-bit are "CDF\x01"/"CDF\x02".
NETCDF_MAGIC = (b"\x89HDF", b"CDF\x01", b"CDF\x02")


class UnwrapError(Exception):
    """A file is a ZIP archive but cannot be reduced to a single NetCDF."""


def _magic(path):
    with open(path, "rb") as f:
        return f.read(4)


def is_zip(path):
    """True if the file starts with the ZIP magic number.

    Checked by magic bytes rather than zipfile.is_zipfile, which scans for a central
    directory anywhere in the file and so can misjudge a large binary NetCDF.
    """
    return _magic(path) == ZIP_MAGIC


def is_netcdf(path):
    """True if the file starts with a NetCDF/HDF5 magic number."""
    return _magic(path).startswith(NETCDF_MAGIC)


def unwrap_zip_nc(path):
    """Replace a ZIP-wrapped NetCDF at `path` with the NetCDF itself.

    Returns True if the file was unwrapped, False if it was already plain NetCDF.
    Extracts to a temporary file and os.replace()s over the original, so an
    interrupted run never leaves a truncated file at `path`.
    Raises UnwrapError if the archive does not hold exactly one .nc member.
    """
    if not is_zip(path):
        return False

    with zipfile.ZipFile(path) as archive:
        members = [m for m in archive.namelist() if m.endswith(".nc")]
        if len(members) != 1:
            raise UnwrapError(
                f"{path}: expected 1 .nc member, found {len(members)}: "
                f"{archive.namelist()}")

        tmp = path + ".unwrap"
        with archive.open(members[0]) as src, open(tmp, "wb") as dst:
            # Chunked copy: these members are hundreds of MB.
            while chunk := src.read(8 << 20):
                dst.write(chunk)

    os.replace(tmp, path)
    return True
