"""Build one-file-per-group-per-month CDS requests.

Every ERA5 download in this repository is chunked the same way: one request per
variable group per month, named `{group}_{year}_{month}.nc`. Chunking by month keeps
individual CDS jobs small enough to queue quickly and makes an interrupted run
resumable at month granularity.
"""
import calendar
import os

from ingest.common.cds_client import Request

ALL_MONTHS = [f"{m:02d}" for m in range(1, 13)]
HOURLY = [f"{h:02d}:00" for h in range(24)]
SIX_HOURLY = ["00:00", "06:00", "12:00", "18:00"]


def days_in(year, month):
    n_days = calendar.monthrange(int(year), int(month))[1]
    return [f"{d:02d}" for d in range(1, n_days + 1)]


def monthly_requests(dataset, base_dir, groups, years, times, area,
                     months=ALL_MONTHS, extra=None):
    """One Request per group per month.

    `groups` maps a directory/file prefix to the request fields specific to that
    group - either a plain list of variables, or a dict for groups that also pin a
    pressure level. `extra` is merged into every request (e.g. `product_type`).

    Year-major ordering so a partial run finishes the earliest years first.
    """
    requests = []
    for year in years:
        for month in months:
            for group, spec in groups.items():
                fields = {"variable": spec} if isinstance(spec, list) else dict(spec)
                requests.append(Request(
                    out_file=os.path.join(base_dir, group,
                                          f"{group}_{year}_{month}.nc"),
                    dataset=dataset,
                    params={
                        **(extra or {}),
                        **fields,
                        "year":  year,
                        "month": month,
                        "day":   days_in(year, month),
                        "time":  times,
                        "area":  area,
                    },
                    label=f"{group} {year}-{month}",
                ))
    return requests
