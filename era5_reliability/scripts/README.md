# Pipeline Documentation — ERA5 Reliability Assessment

End-to-end pipeline for Article 1: ERA5 vs Xavier 2016 vs BR-DWGD reliability assessment
for ML training data over Brazil (1980–2013).

Run steps in order. Each step reads from the previous step's output.

---

## Step 1 — Download (`01_download/`)

### `download_era5.py`
Downloads raw hourly ERA5 data from the [Copernicus CDS API](https://cds.climate.copernicus.eu).

**Requires:** `~/.cdsapirc` with valid CDS credentials.

**Downloads 4 variable groups, one file per group per month:**

| Group file | ERA5 variables | Used to derive |
|------------|---------------|----------------|
| `tp_{year}_{month}.nc` | `tp` — total precipitation | `pr` (mm/day) |
| `temp_{year}_{month}.nc` | `t2m` — 2m air temperature, `d2m` — 2m dewpoint temperature | `tasmax`, `tasmin`, `hur` |
| `wind_{year}_{month}.nc` | `u10`, `v10` — wind components at 10m | `sfcWind` (m/s at 2m) |
| `ssr_{year}_{month}.nc` | `ssr` — surface net solar radiation | `rss` (MJ/m²/day) |

**Output:** `/media/mary-camila/Expansion/era5/raw/{group}/{group}_{year}_{month}.nc`
**Coverage:** 1980–2013, all months, 24 hours/day, Brazil bounding box (6°N–35°S, 75°W–30°W), 0.25° grid.

```bash
python 01_download/download_era5.py
```

---

### `download_brdwgd_gee.py`
Exports BR-DWGD data from Google Earth Engine to Google Drive.

**Requires:** GEE authentication (`ee.Authenticate()`).

**Note:** GEE exports are asynchronous. After running, monitor task status at
[code.earthengine.google.com](https://code.earthengine.google.com) and download
completed files from Google Drive to `data/raw/brdwgd/{variable}/`.

```bash
python 01_download/download_brdwgd_gee.py
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

**Input:** `data/raw/{era5,xavier,brdwgd}/`
**Output:** `data/processed/{era5,xavier,brdwgd}/{variable}.nc`

```bash
python 02_preprocessing/harmonize_grids.py
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
python 02_preprocessing/unit_conversions.py
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
python 02_preprocessing/biome_masks.py
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
python 03_metrics/compute_metrics.py
```

---

## Step 4 — Analysis (`04_analysis/`)

### `analysis_by_biome.py`
Re-computes metrics stratified by each of the 6 Brazilian biomes.

**Requires:** `data/processed/biome_mask.nc` (from Step 2) and processed datasets (from Step 2).
**Output:** `outputs/metrics/biome_metrics.csv`

```bash
python 04_analysis/analysis_by_biome.py
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
python 04_analysis/reliability_map.py
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
python 05_figures/fig1_biome_map.py
python 05_figures/fig2_bias_maps.py
python 05_figures/fig3_kge_boxplots.py
python 05_figures/fig4_reliability_map.py
```

---

## Data flow summary

```
CDS API ──► 01_download ──► raw hourly NetCDF
GEE     ──►               data/raw/

                           02_preprocessing ──► data/processed/
                                                (aligned, converted)

                           03_metrics ──► outputs/metrics/global_metrics.csv

                           04_analysis ──► outputs/metrics/biome_metrics.csv
                                       ──► outputs/reliability_map/*.nc

                           05_figures  ──► outputs/figures/*.png
```
