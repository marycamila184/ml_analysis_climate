# ml_analysis_climate

PhD research repository — Osmary Camila Bortoncello Glober | UFPR | 2026

Climate data analysis and machine learning for Brazil, using ERA5, Xavier 2016, BR-DWGD, and CLIMBra datasets.

## Structure

```
ml_analysis_climate/
├── era5_reliability/   # Article 1: ERA5 reliability assessment for ML training
│   ├── data/           # Raw and processed NetCDF files (not tracked by git)
│   ├── scripts/        # Numbered pipeline: 01_download → 05_figures
│   ├── notebooks/      # Interactive exploration
│   ├── outputs/        # Metrics CSVs, figures, reliability maps
│   └── environment.yml # Conda environment
├── climbra/            # CLIMBra dataset exploration (sandbox)
│   ├── scripts/        # Download scripts
│   └── notebooks/      # Analysis notebooks
└── CLAUDE.md           # AI assistant project instructions (git-ignored)
```

## Articles

| Article | Folder | Status |
|---------|--------|--------|
| Article 1 — ERA5 vs Xavier vs BR-DWGD reliability | `era5_reliability/` | In progress (2026) |

## Setup

```bash
uv sync
source .venv/bin/activate
```

## Data sources

- **ERA5**: ECMWF reanalysis, downloaded via [CDS API](https://cds.climate.copernicus.eu)
- **Xavier 2016**: Bias-corrected gridded observations for Brazil (0.25°), manual download
- **BR-DWGD**: Gridded observations (0.1°), exported via Google Earth Engine
- **CLIMBra**: Bias-corrected CMIP6 dataset (EC-EARTH3, 1980–2013)
