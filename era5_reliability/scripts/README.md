# Pipeline Documentation — ERA5-Land Reliability Assessment

End-to-end pipeline for Article 1: **ERA5-Land vs BR-DWGD** reliability assessment for ML
training data over Brazil (1980–2025). BR-DWGD is the sole reference; ERA5 (0.25°) is kept
as a secondary dataset.

Run steps in order. Each step reads from the previous step's output.

> **Migration status.** The project moved from ERA5 (0.25°, three-way with Xavier) to
> **ERA5-Land (0.1°) vs BR-DWGD**, with a single 0.1° target grid, conservative regrid,
> decomposed KGE (r, β, γ) + CSI, and a utility test (Test B). Steps 2–5 still document
> the current v1 scripts and are being migrated — treat their grid (0.25°), Xavier
> comparisons, bilinear regrid, and composite score as pending revision, not the target
> design.

---

## Step 1 — Download → moved to [`ingest/`](../../ingest/)

Data acquisition is no longer part of this pipeline. Raw datasets are shared across
projects (BR-DWGD is this article's reference *and* the SOM+AIS target), so all download
scripts live in the repository-level [`ingest/`](../../ingest/) package, which also
documents what is currently on disk.

Run from the repository root:

```bash
uv run python -m ingest.era5.download_era5_land    # evaluated product, 0.1°
uv run python -m ingest.era5.download_era5_sfc     # secondary, ERA5 0.25°
uv run python -m ingest.brdwgd.download_brdwgd     # reference, v3.2.4
uv run python -m ingest.status --missing --no-size # what is actually on disk
```

Both ERA5 products are downloaded for **1980–2025**, matching this article's analysis
window. BR-DWGD covers through 2025-12-31, so the reference does not limit it. Keep
downloads at least as wide as the analysis window and slice the period in Step 2 — never
at download time.

**Caveats these downloads hand to Step 2:** accumulated fields (`tp`, `ssrd`, `pev`) need
deaccumulation; ERA5-Land wind is at 10 m vs BR-DWGD 2 m (log-profile correction); `ssrd`
is downward shortwave whereas the historical `rss` convention meant *net* radiation;
`potential_evaporation` is not the same quantity as BR-DWGD's Penman-Monteith ET0 (declare).

**Xavier 2016:** manual download required from the publisher. Save to `data/raw/xavier/`.

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
CDS API      ──► ingest/  ──► raw NetCDF on external drive
Google Drive ──►              /media/mary-camila/Expansion/{era5land,era5,brdwgd}/raw/

                           02_preprocessing ──► data/processed/
                                                (aligned, converted)

                           03_metrics ──► outputs/metrics/global_metrics.csv

                           04_analysis ──► outputs/metrics/biome_metrics.csv
                                       ──► outputs/reliability_map/*.nc

                           05_figures  ──► outputs/figures/*.png
```
