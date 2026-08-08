"""Shared CDS retrieval engine for every ERA5 download in this repository.

Requests are I/O-bound: nearly all wall-clock time is CDS queueing and MARS tape
retrieval, not local bandwidth. Downloads therefore run in a thread pool with one
cdsapi.Client per thread, since a Client is not documented as thread-safe. Request
starts are throttled globally to stay clear of CDS rate limiting.

Every download is atomic: the retrieval writes to `<out_file>.part` and only
os.replace()s onto the final path on success. os.replace is atomic on the same
filesystem, so a file at the final path is always a complete download and the
skip-if-exists check can never resume onto a truncated file.

Usage:

    from ingest.common.cds_client import CDSDownloader, Request

    requests = [Request(out_file=..., dataset=..., params=..., label=...), ...]
    CDSDownloader(workers=3).run(requests)
"""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import cdsapi

from ingest.common.nc_utils import unwrap_zip_nc

# The new CDS API renamed `format` to `data_format` and defaults `download_format`
# to "zip"; a request sending only the legacy key silently receives a ZIP archive
# named `.nc`. Both keys are required to get plain NetCDF back.
NETCDF_FORMAT = {
    "data_format":     "netcdf",
    "download_format": "unarchived",
}


@dataclass
class Request:
    """One CDS retrieval writing one file."""
    out_file: str            # absolute destination path
    dataset: str             # CDS dataset name, e.g. "reanalysis-era5-land"
    params: dict             # request body, merged with NETCDF_FORMAT
    label: str = ""          # short identifier for log lines

    def __post_init__(self):
        if not self.label:
            self.label = os.path.basename(self.out_file)


@dataclass
class CDSDownloader:
    """Runs a batch of CDS requests concurrently, throttled and resumable."""

    workers: int = 2
    delay: float = 5.0           # minimum seconds between request starts
    attempts: int = 3            # retries of the whole request, by this class
    # cdsapi defaults to retry_max=500 with sleep_max=120, i.e. it keeps retrying a
    # connection error for ~16 h while holding the worker, so the retry loop below
    # never runs and nothing reaches errors.log. Cap it low enough that a truly stuck
    # request fails, gets retried here, and finally lands in errors.log for a later
    # pass instead of stalling the run. Only connection errors and timeouts count
    # against it - a job legitimately sitting in the CDS queue is not affected.
    retry_max: int = 10
    timeout: int = 600
    error_log: str = None        # defaults to errors.log beside the first output

    _local: threading.local = field(default_factory=threading.local, init=False)
    # Guards stdout and errors.log against interleaved writes from concurrent workers.
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    # Separate lock for the rate limiter: it is held across a sleep, so it must not be
    # the same lock that guards logging or workers would block waiting to print.
    _rate_lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _last_request: float = field(default=0.0, init=False)
    _done: int = field(default=0, init=False)
    _total: int = field(default=0, init=False)

    def _client(self):
        if not hasattr(self._local, "client"):
            self._local.client = cdsapi.Client(
                timeout=self.timeout, retry_max=self.retry_max)
        return self._local.client

    def _throttle(self):
        """Enforce a minimum gap between consecutive CDS requests, across all workers.

        Spaces out request *starts* globally rather than sleeping per worker, so the
        pace stays the same no matter how many workers are running.
        """
        with self._rate_lock:
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()

    def _log(self, message):
        """Report a finished task, advancing the progress counter.

        Prints one whole line at a time so concurrent workers do not shred each other.
        """
        with self._lock:
            self._done += 1
            print(f"[{self._done}/{self._total}] {message}", flush=True)

    def _note(self, message):
        """Print an interim message without advancing the progress counter."""
        with self._lock:
            print(message, flush=True)

    def _record_error(self, label):
        with self._lock:
            with open(self.error_log, "a") as log:
                log.write(f"{label}\n")

    def _fetch(self, request):
        if os.path.exists(request.out_file):
            self._log(f"[SKIP] {request.label}")
            return

        os.makedirs(os.path.dirname(request.out_file), exist_ok=True)
        part_file = request.out_file + ".part"

        for attempt in range(self.attempts):
            try:
                self._throttle()
                self._client().retrieve(
                    request.dataset,
                    {**request.params, **NETCDF_FORMAT},
                    part_file,
                )
                # Safety net in case CDS returns a zip anyway (see nc_utils).
                if unwrap_zip_nc(part_file):
                    self._note(f"[UNZIP] {request.label} (CDS returned a zip)")
                os.replace(part_file, request.out_file)
                self._log(f"[OK] {request.label}")
                return
            except Exception as e:
                self._note(f"[RETRY] {request.label}, attempt {attempt + 1}: {e}")
                time.sleep(20)

        self._log(f"[ERROR] {request.label} failed after {self.attempts} attempts")
        self._record_error(request.label)

    def run(self, requests):
        """Download every request, skipping files already on disk.

        Safe to interrupt and re-run: completed files are skipped and a partial
        retrieval only ever leaves a `.part` behind, which the next run overwrites.
        """
        requests = list(requests)
        if not requests:
            print("nothing to download")
            return

        self._total = len(requests)
        self._done = 0
        if self.error_log is None:
            self.error_log = os.path.join(
                os.path.dirname(os.path.dirname(requests[0].out_file)), "errors.log")

        print(f"{self._total} requests with {self.workers} workers, "
              f"{self.delay:g}s between requests")

        pool = ThreadPoolExecutor(max_workers=self.workers)
        try:
            for request in requests:
                pool.submit(self._fetch, request)
            pool.shutdown(wait=True)
        except KeyboardInterrupt:
            # Drop the queued requests immediately instead of draining them. Requests
            # already in flight cannot be cancelled, so they still finish (or leave a
            # .part behind); without cancel_futures the pool would work through every
            # remaining request before exiting.
            print("\ninterrupted: cancelling queued requests, "
                  "waiting for in-flight downloads...", flush=True)
            pool.shutdown(wait=True, cancel_futures=True)
            print("stopped. re-run to resume where this left off.", flush=True)


def add_common_args(parser):
    """Register the flags every download script shares."""
    parser.add_argument("--workers", type=int, default=2,
                        help="concurrent CDS requests (default: 2)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="minimum seconds between requests (default: 5)")
    parser.add_argument("--retry-max", type=int, default=10,
                        help="cdsapi connection retries per request, 120s apart "
                             "(default: 10; cdsapi's own default of 500 is ~16h)")
    return parser


def downloader_from_args(args):
    return CDSDownloader(workers=args.workers, delay=args.delay,
                         retry_max=args.retry_max)
