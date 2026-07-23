# Pipeline Documentation — ERA5-Land Reliability Assessment

End-to-end pipeline for Article 1: **ERA5-Land vs BR-DWGD** reliability assessment for ML
training data over Brazil (1980–2013). BR-DWGD is the sole reference; ERA5 (0.25°) is kept
as a secondary dataset.

Run steps in order. Each step reads from the previous step's output.

> **Migration status.** The project moved from ERA5 (0.25°, three-way with Xavier) to
> **ERA5-Land (0.1°) vs BR-DWGD**, with a single 0.1° target grid, conservative regrid,
> decomposed KGE (r, β, γ) + CSI, and a utility test (Test B). **Step 1 below reflects the
> new design.** Steps 2–5 still document the current v1 scripts and are being migrated —
> treat their grid (0.25°), Xavier comparisons, bilinear regrid, and composite score as
> pending revision, not the target design.

---

## Step 1 — Download (`01_download/`)

### `download_era5_land.py` (evaluated product)
Downloads raw hourly ERA5-Land data from the [Copernicus CDS API](https://cds.climate.copernicus.eu)
(dataset `reanalysis-era5-land`, 0.1°, land-only; **no `product_type` field**).

**Requires:** `~/.cdsapirc` with valid CDS credentials and the ERA5-Land licence accepted once on the CDS site.

**Downloads 5 variable groups, one file per group per month:**

| Group file | ERA5-Land variables | Used to derive / compare with BR-DWGD |
|------------|---------------------|----------------------------------------|
| `tp_{year}_{month}.nc` | `total_precipitation` | `pr` |
| `temp_{year}_{month}.nc` | `2m_temperature`, `2m_dewpoint_temperature` | `tasmax`, `tasmin` (daily max/min of hourly t2m), `hur` (Magnus from t2m + d2m) |
| `wind_{year}_{month}.nc` | `10m_u/v_component_of_wind` | `sfcWind` = √(u²+v²) |
| `ssrd_{year}_{month}.nc` | `surface_solar_radiation_downwards` | `rss` — matches BR-DWGD Rs (incoming shortwave) |
| `pev_{year}_{month}.nc` | `potential_evaporation` | BR-DWGD ET0 (approximate; see caveat) |

**Deferred (documented in the script header, not downloaded):** the Level 3 hydrological
package — `volumetric_soil_water_layer_1..4`, `runoff/surface_runoff/sub_surface_runoff`,
`total_evaporation`, `skin_temperature` — for Article 3 / multivariate state.

**Caveats for preprocessing (Step 2):** accumulated fields (`tp`, `ssrd`, `pev`) need
deaccumulation; ERA5-Land wind is at 10 m vs BR-DWGD 2 m (log-profile correction); `ssrd`
is downward shortwave whereas the historical `rss` convention meant *net* radiation;
`potential_evaporation` is not the same quantity as BR-DWGD's Penman-Monteith ET0 (declare).

**Output:** `/media/mary-camila/Expansion/era5land/raw/{group}/{group}_{year}_{month}.nc`
**Coverage:** 1980–2013, all months, 24 hours/day, Brazil bounding box (6°N–35°S, 75°W–30°W), 0.1° grid.

```bash
uv run python 01_download/download_era5_land.py
```

---

### `download_era5.py` (secondary, ERA5 0.25°)
Downloads raw hourly ERA5 data (`reanalysis-era5-single-levels`, 0.25°). Kept as a secondary
dataset — not the evaluated product for Article 1.

| Group file | ERA5 variables | Used to derive |
|------------|---------------|----------------|
| `tp_{year}_{month}.nc` | `tp` — total precipitation | `pr` (mm/day) |
| `temp_{year}_{month}.nc` | `t2m` — 2m air temperature, `d2m` — 2m dewpoint temperature | `tasmax`, `tasmin`, `hur` |
| `wind_{year}_{month}.nc` | `u10`, `v10` — wind components at 10m | `sfcWind` (m/s at 2m) |
| `ssr_{year}_{month}.nc` | `ssr` — surface net solar radiation | `rss` (MJ/m²/day) |

**Output:** `/media/mary-camila/Expansion/era5/raw/{group}/{group}_{year}_{month}.nc`

```bash
uv run python 01_download/download_era5.py
```

---

### `download_brdwgd.py`
Downloads the official BR-DWGD v3.2.4 daily NetCDF files (native 0.1° grid) from
[Xavier's Google Drive](https://github.com/AlexandreCandidoXavier/BR-DWGD) via `gdown`.

**Downloads two zip archives + dataset README, then extracts them:**

| Archive | Variables |
|---------|-----------|
| `pr_Tmax_Tmin_NetCDF_Files.zip` | `pr`, `Tmax`, `Tmin` |
| `ETo_u2_RH_Rs_NetCDF_Files.zip` | `ETo` (unused), `u2`, `RH`, `Rs` |

Each variable is split into three period chunks (1961–1980, 1981–2000, 2001–2024);
the study period 1980–2013 spans all three. Daily values are kept as published —
no aggregation, no regridding at download time.

**Output:** `/media/mary-camila/Expansion/brdwgd/raw/`
Skips existing files, retries failed downloads, resumes partial ones.

```bash
uv run uv run python 01_download/download_brdwgd.py
```

**Xavier 2016:** Manual download required from the publisher. Save files to `data/raw/xavier/`.

---

## Step 2 — Preprocessing (`02_preprocessing/`)

### `harmonize_grids.py`
Aligns all three datasets to the same grid and period.

| Dataset | Native resolution | Action |
|---------|------------------|--------|
| ERA5 | 0.25° | Clip to Brazil, standardize coordinate names |
| Xavier 2016 | 0.25° | Standardize variable names |
| BR-DWGD | 0.1° | Resample to 0.25° via bilinear interpolation |

**Input:** `/media/mary-camila/Expansion/{era5,brdwgd}/raw/` and `data/raw/xavier/`
**Output:** `data/processed/{era5,xavier,brdwgd}/{variable}.nc`

```bash
uv run python 02_preprocessing/harmonize_grids.py
```

---

### `unit_conversions.py`
Converts ERA5 raw units to match Xavier and BR-DWGD.

| Variable | Raw ERA5 unit | Target unit | Conversion |
|----------|--------------|-------------|------------|
| `pr` | m/day | mm/day | × 1000 |
| `rss` | J/m² | MJ/m²/day | ÷ 1 000 000 |
| `hur` | — | % | Magnus equation from `t2m` + `d2m` |
| `sfcWind` | m/s at 10m | m/s at 2m | FAO 56 logarithmic correction |

**Note:** Only needed if ERA5 was downloaded as daily data. If using the hourly
pipeline, these conversions are applied in the preprocessing step.

```bash
uv run python 02_preprocessing/unit_conversions.py
```

---

### `biome_masks.py`
Rasterizes the IBGE Brazil biomes shapefile onto the ERA5 0.25° grid.

**Requires:** IBGE shapefile downloaded to `data/raw/biomes/biomas_250mil.shp`.
Download from [IBGE](https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html).

| Value | Biome |
|-------|-------|
| 1 | Amazon |
| 2 | Cerrado |
| 3 | Caatinga |
| 4 | Atlantic Forest |
| 5 | Pampa |
| 6 | Pantanal |

**Output:** `data/processed/biome_mask.nc`

```bash
uv run python 02_preprocessing/biome_masks.py
```

---

## Step 3 — Metrics (`03_metrics/`)

### `compute_metrics.py`
Computes all validation metrics globally (all grid cells combined).

**Comparisons:** ERA5 vs Xavier, ERA5 vs BR-DWGD
**Variables:** `pr`, `tasmax`, `tasmin`, `rss`, `sfcWind`, `hur`

| Metric | Description |
|--------|-------------|
| `bias_rel` | Relative bias (%) |
| `rmse` | Root Mean Square Error |
| `mae` | Mean Absolute Error |
| `r` | Pearson correlation |
| `kge` | Kling-Gupta Efficiency (Gupta et al. 2009) |
| `bias_p10` / `bias_p90` | Bias at 10th / 90th percentile |
| `cdd` / `cwd` | Consecutive Dry / Wet Days (precipitation only) |

**Output:** `outputs/metrics/global_metrics.csv`

```bash
uv run python 03_metrics/compute_metrics.py
```

---

## Step 4 — Analysis (`04_analysis/`)

### `analysis_by_biome.py`
Re-computes metrics stratified by each of the 6 Brazilian biomes.

**Requires:** `data/processed/biome_mask.nc` (from Step 2) and processed datasets (from Step 2).
**Output:** `outputs/metrics/biome_metrics.csv`

```bash
uv run python 04_analysis/analysis_by_biome.py
```

---

### `reliability_map.py`
Generates the ERA5 Reliability Map for ML Training — the main product of Article 1.

Computes a composite normalized score [0–1] per grid cell per variable,
combining KGE, relative bias, and P90 bias with equal weights.

| Score | Category |
|-------|----------|
| ≥ 0.7 | High confidence |
| 0.4 – 0.7 | Moderate confidence |
| < 0.4 | Low confidence |

**Output:**
- `outputs/reliability_map/score_{variable}.nc` — continuous score [0–1]
- `outputs/reliability_map/category_{variable}.nc` — classified map (1/2/3)

```bash
uv run python 04_analysis/reliability_map.py
```

---

## Step 5 — Figures (`05_figures/`)

| Script | Figure | Description |
|--------|--------|-------------|
| `fig1_biome_map.py` | Figure 1 | Brazil biome map with ERA5 grid overlay |
| `fig2_bias_maps.py` | Figure 2 | Spatial relative bias maps (6 panels, ERA5 vs Xavier) |
| `fig3_kge_boxplots.py` | Figure 3 | KGE distribution by biome and variable |
| `fig4_reliability_map.py` | Figure 4 | ERA5 reliability map (main article figure) |

**Output:** `outputs/figures/fig{1-4}_*.png` at 300 DPI.

```bash
uv run python 05_figures/fig1_biome_map.py
uv run python 05_figures/fig2_bias_maps.py
uv run python 05_figures/fig3_kge_boxplots.py
uv run python 05_figures/fig4_reliability_map.py
```

---

## Data flow summary

```
CDS API      ──► 01_download ──► raw NetCDF on external drive
Google Drive ──►               /media/mary-camila/Expansion/{era5,brdwgd}/raw/

                           02_preprocessing ──► data/processed/
                                                (aligned, converted)

                           03_metrics ──► outputs/metrics/global_metrics.csv

                           04_analysis ──► outputs/metrics/biome_metrics.csv
                                       ──► outputs/reliability_map/*.nc

                           05_figures  ──► outputs/figures/*.png
```
