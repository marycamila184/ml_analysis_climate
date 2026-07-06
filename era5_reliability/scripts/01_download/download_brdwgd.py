"""
Download official BR-DWGD daily NetCDF files (v3.2.4) to the external disk.

Source: Xavier et al. gridded dataset, distributed via Google Drive
(https://github.com/AlexandreCandidoXavier/BR-DWGD). Two zip archives cover
all six variables (pr, Tmax, Tmin, Rs, u2, RH; ETo comes along but is unused),
each split into three period chunks: 1961-1980, 1981-2000, 2001-2024.
The study period 1980-2013 spans all three chunks, so everything is kept.

Requires gdown (Google Drive downloads with confirmation-token handling).

Output: /media/mary-camila/Expansion/brdwgd/raw/{zip archives + extracted .nc}
"""
import os
import time
import zipfile

import gdown

BASE_DIR = "/media/mary-camila/Expansion/brdwgd/raw"

# Google Drive file IDs from the official BR-DWGD folder
# https://drive.google.com/drive/folders/11-qnvwojirAtaQxSE03N0_SUrbcsz44N
ARCHIVES = {
    "pr_Tmax_Tmin_NetCDF_Files.zip": "1oQWHpXwFgTKNH4Fa2GwCPJ3QN1AMgNPJ",
    "ETo_u2_RH_Rs_NetCDF_Files.zip": "1aGdOHRT10W8oBWvE5IvmEAqJCNQOYYid",
    "README.txt":                    "1_VYa1Kz7TPpT7tDUyArMg-n5TCbx6IRe",
}

os.makedirs(BASE_DIR, exist_ok=True)


def download_archive(name, file_id):
    out_file = os.path.join(BASE_DIR, name)

    if os.path.exists(out_file):
        print(f"[SKIP] {name}")
        return out_file

    for attempt in range(3):
        try:
            print(f"[DOWNLOAD] {name}")
            gdown.download(id=file_id, output=out_file, resume=True)
            if os.path.exists(out_file):
                print(f"[OK] {name}")
                return out_file
            raise RuntimeError("gdown finished without producing the file")
        except Exception as e:
            print(f"[RETRY] {name}, attempt {attempt + 1}: {e}")
            time.sleep(20)

    print(f"[ERROR] {name} failed after 3 attempts")
    with open(os.path.join(BASE_DIR, "errors.log"), "a") as log:
        log.write(f"{name}\n")
    return None


def extract_archive(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = os.path.join(BASE_DIR, member)
            if os.path.exists(target):
                print(f"[SKIP] {member}")
                continue
            print(f"[EXTRACT] {member}")
            zf.extract(member, BASE_DIR)


for name, file_id in ARCHIVES.items():
    path = download_archive(name, file_id)
    if path and name.endswith(".zip"):
        extract_archive(path)

print("\nDone. NetCDF files are in", BASE_DIR)
