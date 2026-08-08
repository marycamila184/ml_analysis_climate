# Evaluating ERA5-Land as Machine Learning Training Data for Brazilian Climate Modeling

PhD research repository — Osmary Camila Bortoncello Glober | UFPR | 2026

Assessment of **ERA5-Land** reanalysis reliability as training data for machine learning
models over Brazil, evaluated against **BR-DWGD** (the sole reference) across six climate
variables and six biomes (1980–2025). ERA5-Land (0.1°) matches the BR-DWGD grid, removing
the resolution-alignment problem of the earlier ERA5 (0.25°) design; ERA5 (0.25°) is kept
as a secondary dataset.

## Structure

Data acquisition is separated from analysis. Everything that fetches raw data lives in
`ingest/`; the project folders start at preprocessing and only read the paths `ingest`
declares. Raw datasets are shared — BR-DWGD is Article 1's reference *and* the SOM+AIS
target — so they do not belong to any single project.

```
ml_analysis_climate/
├── ingest/             # Data acquisition only — no analysis
│   ├── paths.py        # Every raw data root (single source of truth)
│   ├── common/         # Shared CDS client, NetCDF helpers
│   ├── era5/           # ERA5-Land, ERA5 0.25° surface, ERA5 synoptic
│   ├── brdwgd/         # BR-DWGD v3.2.4
│   └── climbra/        # CLIMBra V5
├── era5_reliability/   # Article 1: ERA5-Land reliability for ML training
│   ├── data/           # Processed NetCDF files (not tracked by git)
│   ├── scripts/        # Numbered pipeline: 02_preprocessing → 05_figures
│   ├── notebooks/      # Interactive exploration
│   └── outputs/        # Metrics CSVs, figures, reliability maps
├── som_ais_extremes/   # SOM + Artificial Immune Systems for precipitation extremes
│   ├── scripts/        # Numbered pipeline: 02_preprocessing → 07_figures
│   ├── notebooks/      # Interactive exploration
│   └── outputs/        # Regimes, detectors, synthetic catalogue, figures
├── climbra/            # CLIMBra dataset exploration (sandbox)
│   └── notebooks/      # Analysis notebooks
└── pyproject.toml      # Python dependencies (uv)
```

## Projects

| Project | Folder | Status |
|---------|--------|--------|
| Article 1 — ERA5-Land vs BR-DWGD reliability for ML training | [`era5_reliability/`](era5_reliability/) | In progress (2026) |
| SOM + AIS — detection and generation of precipitation extremes | [`som_ais_extremes/`](som_ais_extremes/) | Phase 0 (2026–2027) |

## Setup

```bash
uv sync
```

Run analysis scripts with `uv run python <script>` (no manual venv activation needed).
Run `ingest` scripts as modules from the repository root, e.g.
`uv run python -m ingest.era5.download_era5_land`.

## Data sources

See [`ingest/README.md`](ingest/README.md) for how to fetch each dataset. For what is
currently on disk, ask rather than read a table:

```bash
uv run python -m ingest.status --missing --no-size
```

- **ERA5-Land** — ECMWF reanalysis, 0.1°, land-only, hourly, via [CDS API](https://cds.climate.copernicus.eu) (`reanalysis-era5-land`). Article 1's evaluated product.
- **BR-DWGD** — gridded observations (0.1°), official v3.2.4 daily NetCDF release ([Xavier et al.](https://github.com/AlexandreCandidoXavier/BR-DWGD)) via `gdown`. Article 1's sole reference; SOM+AIS target.
- **ERA5 single levels** — 0.25°, hourly, via CDS API (`reanalysis-era5-single-levels`). Article 1 secondary.
- **ERA5 synoptic** — 0.25°, 6-hourly pressure-level and single-level fields via CDS API. SOM+AIS predictors.
- **CLIMBra** — bias-corrected CMIP6 dataset. Sandbox; SOM+AIS plausibility envelope.

> The earlier three-way design (adding Xavier 2016 as a separate 0.25° product and
> triangulating references) was dropped for v1.
