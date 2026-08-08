# ingest — data acquisition

Everything that fetches raw data lives here, and nothing here does analysis. The project
folders (`era5_reliability/`, `som_ais_extremes/`, `climbra/`) start at preprocessing and
only *read* the paths declared in [`paths.py`](paths.py).

The reason for the split: raw datasets are shared. BR-DWGD is Article 1's reference *and*
the SOM+AIS target; ERA5 feeds both. Keeping downloads inside one project folder made the
other project's dependency invisible and would have duplicated the CDS retrieval logic.

Run everything as a module **from the repository root**, so the `ingest` package resolves.

---

## Quick reference

```bash
# What is on disk right now (read-only, safe during a download)
uv run python -m ingest.status --missing --no-size

# ERA5-Land 0.1deg   -> Article 1 evaluated product
uv run python -m ingest.era5.download_era5_land --workers 3

# ERA5 0.25deg       -> Article 1 secondary  (--groups to fetch only some)
uv run python -m ingest.era5.download_era5_sfc --workers 3
uv run python -m ingest.era5.download_era5_sfc --groups ssrd --workers 3

# ERA5 synoptic      -> som_ais_extremes predictors  (test one month first)
uv run python -m ingest.era5.download_era5_synoptic --years 1980 1980 --groups plev500
uv run python -m ingest.era5.download_era5_synoptic --workers 3

# BR-DWGD and CLIMBra (one-shot, not month-chunked)
uv run python -m ingest.brdwgd.download_brdwgd
uv run python -m ingest.climbra.download_climbra
```

All ERA5 downloads are **resumable** — completed months are skipped, so re-running after
an interruption costs only the in-flight month. Run them under `tmux` or `nohup`: a full
pass takes hours to days and a closed terminal kills it.

**Run one at a time.** CDS caps active requests per user, so two scripts at `--workers 3`
split one quota instead of doubling throughput.

### Weight per group

Wall-clock time on CDS is dominated by queueing and MARS tape retrieval **per request**,
not by bytes — so request count matters more than size. A 2 MB synoptic month can take as
long to come back as a 353 MB ERA5-Land month.

| Script | One month | Full pass | Requests |
|---|---|---|---|
| `download_era5_land` | `wind` 353 MB, `temp` 290, `pev` 241, `tp` 150, `ssrd` 127 | ~530 GB | 2760 |
| `download_era5_sfc` | `wind` 95 MB, `temp` 70, `ssr`/`ssrd` 23, `tp` 22 | ~120 GB | 2760 |
| `download_era5_synoptic` | `plev850` ~4 MB, `single` ~3, `plev250` ~2, `plev500` ~1 | ~5 GB | 2208 |

Size differences come from variable count per group and from compressibility: `tp` is
mostly exact zeros and compresses hard, wind is noisy in both components and does not.
Synoptic months are tiny because the S/SE box is a quarter the area *and* 6-hourly is a
sixth the timesteps — ~24× less data per variable than the hourly Brazil-box groups.

---

## Coverage — what is on disk

Do not trust a table in a README for this; it goes stale on the next download. Ask:

```bash
uv run python -m ingest.status --missing --no-size
```

[`status.py`](status.py) imports `GROUPS` and `YEARS` from the download modules
themselves, so what it calls "complete" is by definition what the scripts would fetch.
It cannot drift from them. Run it before and after any download session.

## What each dataset is for

| Dataset | Resolution / cadence | Downloaded period | Consumers |
|---|---|---|---|
| ERA5-Land | 0.1°, land-only, hourly | 1980–2025 | Article 1 — **evaluated product** |
| ERA5 single levels | 0.25°, hourly | 1980–2025 | Article 1 — secondary |
| ERA5 synoptic | 0.25°, 6-hourly, pressure + single level | 1980–2025 | SOM+AIS — predictors |
| BR-DWGD v3.2.4 | 0.1°, daily | 1961–2025 as published | Article 1 **reference**; SOM+AIS **target** |
| CLIMBra V5 | daily | as published | CLIMBra sandbox; SOM+AIS plausibility envelope |

**Everything is fetched to 1980–2025**, which is what both projects now analyse: Article 1
over the full window, SOM+AIS split 1980–2014 train / 2015–2025 test. BR-DWGD, the
reference for both, covers through 2025-12-31, so nothing is limited by it.

Keep downloads at least as wide as any analysis window and slice in preprocessing —
widening a download is days of CDS queueing, slicing is free.

**ERA5-Land is not a substitute for the synoptic fields.** It is land-only, and SACZ,
frontal systems and the subtropical jet are defined partly over the Atlantic — a land mask
cuts those regimes in half. The two ERA5 trees are not interchangeable in either
direction: ERA5-Land has the resolution Article 1 needs and no ocean; the synoptic set has
the ocean and the vertical structure the SOM needs and no 0.1° detail.

---

## Scripts

### `era5/download_era5_land.py` — ERA5-Land 0.1°, hourly
Article 1's evaluated product. Dataset `reanalysis-era5-land` (land-only, **no
`product_type` field**). Brazil box `N 6, W −75, S −35, E −30`, **1980–2025**, 24 h/day.

| Group | Variables | Derives |
|---|---|---|
| `tp` | `total_precipitation` | `pr` |
| `temp` | `2m_temperature`, `2m_dewpoint_temperature` | `tasmax`, `tasmin` (daily max/min), `hur` (Magnus) |
| `wind` | `10m_u/v_component_of_wind` | `sfcWind` = √(u²+v²) |
| `ssrd` | `surface_solar_radiation_downwards` | `rss` — matches BR-DWGD Rs (incoming shortwave) |
| `pev` | `potential_evaporation` | BR-DWGD ET0 (approximate — declare) |

Deferred to Article 3 (documented in the script header, not downloaded): the hydrological
land-state package — `volumetric_soil_water_layer_1..4`, `runoff`/`surface_runoff`/
`sub_surface_runoff`, `total_evaporation`, `skin_temperature`.

```bash
uv run python -m ingest.era5.download_era5_land --workers 3
uv run python -m ingest.era5.download_era5_land --groups tp temp   # subset
```

### `era5/download_era5_sfc.py` — ERA5 0.25° single levels, hourly
Article 1's secondary dataset. Brazil box, **1980–2025**, 24 h/day. Groups `tp`, `temp`,
`wind`, `ssrd`, `ssr`.

Radiation: BR-DWGD's Rs is **incoming** shortwave — what a station pyranometer measures.
`ssr` is **net** (downward minus reflected), so it carries the model's surface albedo
inside it and is not a like-for-like match; `ssrd` is. Use `ssrd` for the comparison.
`ssr` is retained because it is already downloaded and `ssrd - ssr` is the reflected
component, which tells you how much of any radiation bias is an albedo artefact rather
than an irradiance error.

```bash
uv run python -m ingest.era5.download_era5_sfc --workers 3
uv run python -m ingest.era5.download_era5_sfc --groups ssrd --workers 3   # just ssrd
```

### `era5/download_era5_synoptic.py` — ERA5 0.25° synoptic fields, 6-hourly
SOM+AIS predictors. South/Southeast box `N −14, W −60, S −35, E −38`, 1980–2025,
00/06/12/18 UTC. Grouped by pressure level because a CDS pressure-level request is a
cross product of `variable` × `pressure_level` — three requests per month cover all seven
variable-levels.

| Group | Dataset | Variables | Level |
|---|---|---|---|
| `plev500` | pressure-levels | `geopotential` | 500 hPa |
| `plev850` | pressure-levels | `temperature`, `specific_humidity`, `u/v_component_of_wind` | 850 hPa |
| `plev250` | pressure-levels | `u/v_component_of_wind` | 250 hPa |
| `single` | single-levels | `mean_sea_level_pressure`, `total_column_water_vapour`, `convective_available_potential_energy` | — |

Test one month before launching the full retrieval:

```bash
uv run python -m ingest.era5.download_era5_synoptic --years 1980 1980 --groups plev500
uv run python -m ingest.era5.download_era5_synoptic --workers 3
```

### `brdwgd/download_brdwgd.py` — BR-DWGD v3.2.4 daily, 0.1°
Two Google Drive zip archives (`pr`/`Tmax`/`Tmin` and `ETo`/`u2`/`RH`/`Rs`) plus the
dataset README, fetched with `gdown` and extracted. Each variable is split into three
period chunks (1961–1980, 1981–2000, 2001–2025). Values are kept as published — no
aggregation, no regridding at download time.

```bash
uv run python -m ingest.brdwgd.download_brdwgd
```

### `climbra/download_climbra.py` — CLIMBra V5
Driven by a links file exported from the repository's download basket, expected beside the
script. **The links file carries session tokens and is git-ignored** — re-export it if the
links have expired.

```bash
uv run python -m ingest.climbra.download_climbra
```

### `status.py` — coverage report
Reports what is on disk against what the download scripts declare, per group. Safe to run
at any time, including while a download is in progress — it only reads.

```bash
uv run python -m ingest.status --missing --no-size   # fast, lists gaps as ranges
uv run python -m ingest.status                       # adds size on disk (walks the tree)
```

---

## Shared machinery

| Module | Contents |
|---|---|
| [`paths.py`](paths.py) | Every raw data root. Override the drive with `CLIMATE_DATA_ROOT`. |
| [`status.py`](status.py) | Coverage report, derived from the download modules' own `GROUPS`/`YEARS`. |
| [`common/cds_client.py`](common/cds_client.py) | Throttled thread pool, per-thread `cdsapi.Client`, retry loop, atomic `.part` rename, `errors.log`. |
| [`common/nc_utils.py`](common/nc_utils.py) | ZIP-wrapped NetCDF detection and unwrapping. |
| [`era5/monthly.py`](era5/monthly.py) | Builds one-file-per-group-per-month CDS requests. |

Three properties every download here has, and that new scripts should keep:

- **Resumable.** Completed files are skipped; interrupting and re-running picks up where
  it stopped. Month-sized chunks make that granular.
- **Atomic.** Retrieval writes `<file>.part` and `os.replace()`s onto the final path only
  on success, so a file at the final path is always complete. Without this, a truncated
  download would satisfy the skip check and be silently accepted forever — which is
  exactly what happened before, and why a one-off `repair_zipped_nc` script used to live
  here. All 4,593 raw `.nc` files were verified plain and valid on 2026-08-08, and both
  root causes are now fixed structurally, so the script was removed (it is in git history
  if a future CDS change ever needs it).
- **Throttled.** Request *starts* are spaced globally rather than per worker, so the pace
  on CDS stays the same regardless of `--workers`.

Two CDS quirks are handled centrally and are worth knowing:

- `format` was renamed to `data_format`, and `download_format` now defaults to `"zip"`. A
  request sending only the legacy key silently receives a ZIP archive named `.nc`, which
  xarray cannot open. `NETCDF_FORMAT` sends both keys; `unwrap_zip_nc` is kept as a safety
  net because CDS has changed this contract once already.
- `cdsapi` defaults to `retry_max=500` with `sleep_max=120` — roughly 16 hours of retrying
  a connection error while holding a worker, so the script's own retry loop never runs and
  nothing reaches `errors.log`. `CDSDownloader` caps it at 10 by default. Jobs legitimately
  queued at CDS are not affected.

## Requirements

`~/.cdsapirc` with valid CDS credentials, and each dataset's licence accepted once on the
CDS website (ERA5 and ERA5-Land are separate licences).
