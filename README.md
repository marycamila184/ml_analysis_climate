# Evaluating ERA5-Land as Machine Learning Training Data for Brazilian Climate Modeling

PhD research repository — Osmary Camila Bortoncello Glober | UFPR | 2026

Assessment of **ERA5-Land** reanalysis reliability as training data for machine learning
models over Brazil, evaluated against **BR-DWGD** (the sole reference) across six climate
variables and six biomes (1980–2013). ERA5-Land (0.1°) matches the BR-DWGD grid, removing
the resolution-alignment problem of the earlier ERA5 (0.25°) design; ERA5 (0.25°) is kept
as a secondary dataset.

## Structure

```
ml_analysis_climate/
├── era5_reliability/   # Article 1: ERA5 reliability assessment for ML training
│   ├── data/           # Raw and processed NetCDF files (not tracked by git)
│   ├── scripts/        # Numbered pipeline: 01_download → 05_figures
│   ├── notebooks/      # Interactive exploration
│   └── outputs/        # Metrics CSVs, figures, reliability maps
├── climbra/            # CLIMBra dataset exploration (sandbox)
│   ├── scripts/        # Download scripts
│   └── notebooks/      # Analysis notebooks
└── pyproject.toml      # Python dependencies (uv)
```

## Articles

| Article | Folder | Status |
|---------|--------|--------|
| Article 1 — ERA5-Land vs BR-DWGD reliability for ML training | `era5_reliability/` | In progress (2026) |

## Setup

```bash
uv sync
```

Run any script with `uv run python <script>` (no manual venv activation needed).

## Data sources

- **ERA5-Land** (evaluated product): ECMWF reanalysis, 0.1°, land-only, hourly, downloaded via [CDS API](https://cds.climate.copernicus.eu) (`reanalysis-era5-land`)
- **BR-DWGD** (sole reference): Gridded observations (0.1°), official v3.2.4 daily NetCDF release ([Xavier et al.](https://github.com/AlexandreCandidoXavier/BR-DWGD)), downloaded via `gdown`
- **ERA5** (secondary): ECMWF reanalysis, 0.25°, downloaded via CDS API (`reanalysis-era5-single-levels`)
- **CLIMBra**: Bias-corrected CMIP6 dataset (EC-EARTH3, 1980–2013) — Article 2/3

> The earlier three-way design (adding Xavier 2016 as a separate 0.25° product and
> triangulating references) was dropped for v1.
