"""Download the CLIMBra V5 bias-corrected CMIP6 dataset from its open repository.

Driven by a links file exported from the repository's download basket: one URL per
line, each carrying the target path and filename as query parameters. The file holds
session tokens, so it is git-ignored - re-export it if the links have expired.

Consumers: `climbra/` (exploratory) and `som_ais_extremes/` (plausibility envelope -
the 1st and 99th percentiles of each variable in the 2050 and 2100 projections).

Output: {CLIMBRA}/<path from the URL>

Usage:
    uv run python -m ingest.climbra.download_climbra
"""
import os
import time
import requests
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

from ingest.paths import CLIMBRA

# ==== CONFIG ====
# Links file lives beside this script; it is git-ignored (contains tokens).
LINKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "609b7ff93f0d4d1a9ba6eb709027c6ad.txt")
BASE_DIR = CLIMBRA
MAX_WORKERS = 2
CHUNK_SIZE = 1024 * 1024
RETRIES = 3
RETRY_DELAY = 5


session = requests.Session()


def parse_url(url):
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    filepath = params.get("path", ["file"])[0]
    filename = params.get("fileName", ["file"])[0]

    return filepath, filename


def download(url):
    rel_path, filename = parse_url(url)

    full_path = os.path.join(BASE_DIR, rel_path.lstrip("/"))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    temp_path = full_path + ".part"

    if os.path.exists(full_path):
        print(f"⏭️ Skipping: {filename}")
        return

    for attempt in range(RETRIES):
        try:
            downloaded = 0
            if os.path.exists(temp_path):
                downloaded = os.path.getsize(temp_path)

            headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}

            with session.get(url, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()

                # Check total size (if available)
                total_size = int(r.headers.get("content-length", 0)) + downloaded

                mode = "ab" if downloaded > 0 else "wb"

                with open(temp_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)

            # Verify file size if possible
            if os.path.exists(temp_path):
                final_size = os.path.getsize(temp_path)
                if total_size == 0 or final_size >= total_size:
                    os.rename(temp_path, full_path)
                    print(f"✅ {full_path}")
                    return
                else:
                    print(f"⚠️ Incomplete, retrying: {filename}")

        except Exception as e:
            print(f"⚠️ Attempt {attempt+1} failed: {filename}")

        time.sleep(RETRY_DELAY)

    print(f"❌ Failed after retries: {filename}")


def main():
    with open(LINKS_FILE) as f:
        links = [line.strip() for line in f if line.strip()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(download, links)


if __name__ == "__main__":
    main()