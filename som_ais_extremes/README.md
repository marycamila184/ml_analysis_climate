# som_ais_extremes — Precipitation Extremes with SOM + Artificial Immune Systems

Detection and generation of unprecedented precipitation extremes over South/Southeast
Brazil, using a Self-Organizing Map to define synoptic context and Artificial Immune
System algorithms (negative selection, clonal selection, novelty search) to build and
invert a repertoire of anomaly detectors.

Working plan — source of truth for scope, schedule and reading list: [`PLAN.md`](PLAN.md).

This scope is **independent of `era5_reliability/`** (Article 1). It shares the external
drive, the `ingest/` download layer and the `uv` environment, but not the grid, the
region, the period, or the variables. Nothing here overwrites Article 1 data.

---

## 1. The idea

The immune system recognises pathogens it has never seen, trained only on examples of
the host organism. Climate extremes have the same structure: tens of thousands of
ordinary days, a few dozen extreme events, and the need to anticipate events without
precedent.

The proposal has three moving parts:

1. **SOM** separates synoptic regimes — the *context* in which a day occurs.
2. **Negative selection** builds a detector repertoire *per regime* — what counts as
   anomalous *given that context*.
3. **Clonal selection + novelty search** inverts the repertoire: instead of classifying
   observed events, it generates a catalogue of plausible extreme events that never
   occurred, filtered by physical plausibility.

**Core version (course deliverable T3):** detection — the AIS scores the degree of
extremity conditioned on regime.

**Extended version (article):** generation — the AIS produces synthetic unprecedented
events, filtered for physical plausibility.

### The central bet

Negative selection was largely abandoned because it does not scale in high dimension.
The bet of this work is that **regime conditioning fixes that**, because inside a single
SOM node the self occupies a compact region. If the bet fails, the method fails — which
is why the dimensionality test is the first experiment to run, not an implementation
detail.

---

## 2. Logical structure

```
ERA5 synoptic fields (6-hourly, pressure + single level)
        │
        ▼  02_preprocessing
  daily aggregation → regional crop → regrid (1.0–1.5°) → Zarr
        │
        ▼  dimensionality reduction (PCA, d = 10–15)
  X (N days, d)
        │
        ▼  03_som
  SOM (5×4 grid) → regime label k for each day
        │
        ▼  04_negative_selection
  for each regime k:
      self_k = normal days in regime k          (train window only)
      negative selection → detectors (C_k, R_k)  [V-detector, variable radius]
        │
        ├──► CORE      new day → degree of extremity
        │              06_evaluation vs. baselines
        │
        └──► EXTENDED  05_generation
                       clonal selection + novelty / MAP-Elites
                              │
                              ▼  physical filter
                       Clausius-Clapeyron, spatial coherence,
                       CLIMBra plausibility envelope
                              │
                              ▼
                       synthetic extreme catalogue
```

### Role of each piece

| Piece | Function | Immune analogue |
|---|---|---|
| SOM | defines the context (synoptic regime) | tissue-specific tolerance |
| Negative selection | detector repertoire per regime | T-cell maturation in the thymus |
| Clonal selection | pushes detectors away from self | somatic hypermutation |
| Novelty / MAP-Elites | keeps repertoire diversity | lymphocyte lineage diversity |
| Physical filter | discards impossible candidates | protein biochemical viability |

### Directory layout

Downloads are **not** part of this pipeline — they live in the repository-level
[`../ingest/`](../ingest/) package, because raw datasets are shared across projects.
The synoptic fields this project needs are fetched by
[`../ingest/era5/download_era5_synoptic.py`](../ingest/era5/download_era5_synoptic.py).

| Path | Contents |
|---|---|
| `scripts/02_preprocessing/` | daily aggregation, crop, regrid, Zarr store, PCA |
| `scripts/03_som/` | SOM training, regime validation and naming |
| `scripts/04_negative_selection/` | V-detector implementation, per-regime repertoires |
| `scripts/05_generation/` | clonal selection, MAP-Elites, physical filters |
| `scripts/06_evaluation/` | baselines, POD/FAR/CSI, coverage, GEV return periods |
| `scripts/07_figures/` | article and monograph figures |
| `data/processed/` | Zarr stores and PCA artefacts (git-ignored) |
| `outputs/{regimes,detectors,catalog,figures}/` | run products |

Numbered directories mirror the `era5_reliability/` convention: they are executed in
order and each stage reads only the previous stage's output. Numbering starts at `02_`
in both projects because step 1 was download, and download now lives in `ingest/`.

---

## 3. Data — what the plan needs

For **what is currently on disk**, ask rather than read — any table here would go stale on
the next download:

```bash
uv run python -m ingest.status --missing --no-size
```

The requirements below are stable; the coverage against them is not.

Nothing in Article 1's downloads covers this project. Those were built for a
surface-variable evaluation; this project needs mid- and upper-tropospheric synoptic
fields, which are a different CDS dataset entirely.

### 3.1 ERA5 pressure levels — dataset `reanalysis-era5-pressure-levels`

| Variable | Level | Purpose |
|---|---|---|
| `geopotential` | 500 hPa | wave structure, troughs and ridges |
| `temperature` | 850 hPa | air masses, fronts |
| `specific_humidity` | 850 hPa | moisture availability |
| `u_component_of_wind` | 850 hPa | advection, low-level jet |
| `v_component_of_wind` | 850 hPa | advection, low-level jet |
| `u_component_of_wind` | 250 hPa | subtropical jet |
| `v_component_of_wind` | 250 hPa | subtropical jet |

These are the SOM's entire input. Without them there is no regime classification, and
without regimes there is no per-regime negative selection — i.e. no project.

### 3.2 ERA5 single levels — dataset `reanalysis-era5-single-levels`

| Variable | Purpose |
|---|---|
| `mean_sea_level_pressure` | system position |
| `total_column_water_vapour` | available moisture |
| `convective_available_potential_energy` | convective instability |

`total_precipitation` is deliberately **not** among the predictors. The plan's §4.1 lists
it, but §4.2 settles it: BR-DWGD is the ground truth, ERA5 precipitation has a known bias,
and using it as a predictor would leak the target into the SOM. Article 1's 0.25° `tp` is
already on disk if a diagnostic field is wanted.

### 3.3 What is on disk and is *not* usable here

- **ERA5-Land** — land-only, and therefore unusable for synoptic regimes: SACZ, frontal
  systems and the subtropical jet are defined partly over the Atlantic, and a land mask
  cuts them in half. This dataset stays with Article 1.
- **ERA5 surface `temp`, `wind`, `ssr`/`ssrd`** — Article 1 variables, not regime-defining.
  A regime is a large-scale circulation pattern; `t2m` mostly reports time of day and
  elevation. `t2m`/`d2m` could optionally supply surface thermodynamics, but the plan does
  not require them.

### 3.4 What already fits without re-downloading

- **Region.** Article 1's ERA5 crop is the Brazil box `N 6, W −75, S −35, E −30`, which
  fully contains this project's predictor box `lat −35…−10, lon −60…−38` (see §3.7). Its
  `tp` can simply be subset — no new `tp` request needed.
- **Resolution.** Those files are 0.25°; the plan wants 1.0–1.5° for regime work, so
  coarsening is a preprocessing step, not a re-download.
- **Period.** Article 1's 0.25° groups cover 1980–2025, matching the plan's window and the
  1980–2014 / 2015–2025 train-test split.

### 3.5 Download sizing

Retrieving the 10 synoptic fields over the predictor box (§3.7) at 0.25°, 6-hourly
(00/06/12/18 UTC), 1980–2025:

- ~9,000 grid points per field-time (≈36 KB float32)
- 4 steps/day × ~16,800 days ≈ 67,200 steps
- ≈2.4 GB per variable-level → **≈24 GB total**

Two decisions worth making before the first request:

1. **6-hourly, not hourly.** Synoptic regime classification is conventionally done at
   00/06/12/18 UTC. Hourly would be 6× the volume for no methodological gain. (Article 1
   needed hourly because it derives daily max/min; this project does not.)
2. **Download at 0.25° and regrid locally**, rather than using the CDS `grid` parameter.
   24 GB is cheap, and keeping native resolution leaves the option of testing regime
   sensitivity to grid spacing without a second multi-day download.

At ~24 GB, the plan's phase-0 target of "1.5 TB → under 50 GB" is met by scoping the
request correctly rather than by aggressive post-processing.

### 3.6 Paths

All raw roots are declared in [`../ingest/paths.py`](../ingest/paths.py) and must not be
hardcoded anywhere in this project.

| Data | Path |
|---|---|
| ERA5 synoptic (to download) | `{ERA5_SYNOPTIC}/{plev500,plev850,plev250,single}/` |
| ERA5 0.25° `tp` (existing) | `{ERA5_SFC}/tp/` |
| BR-DWGD (existing) | `{BRDWGD}/` |
| CLIMBra V5 (existing) | `{CLIMBRA}/V5/` |
| Processed Zarr | `som_ais_extremes/data/processed/` |

Large files (`.nc`, `.zarr`, `.tif`) live on the external drive and are git-ignored.

### 3.7 Decision — region, and why the predictor box is larger than the target

Decided 2026-08-11, before any synoptic data was downloaded (`ingest.status` showed
0/552 months for every group). Recorded here because it is expensive to revisit: changing
the box after the SOM is trained means a multi-day re-download and invalidated regimes.

**Two domains, deliberately different.**

| Domain | Box | Used for |
|---|---|---|
| **Predictor** (SOM input) | `N −10, W −60, S −35, E −38` | Z500, MSLP, 850 T/q/u/v, 250 u/v, TCWV, CAPE |
| **Evaluation** (target) | South/Southeast, per §4 | BR-DWGD extremes, record breaks, GEV, POD/FAR/CSI |

`DEFAULT_AREA` in [`../ingest/era5/download_era5_synoptic.py`](../ingest/era5/download_era5_synoptic.py)
is the predictor box. It moves the northern edge from the plan's original −14 to **−10**.

**Why not all of Brazil.** The predictor set is seven pressure-level dynamical fields out
of ten — a subtropical predictor set, and it works because geostrophic balance holds
there. Toward the equator Coriolis goes to zero and the atmosphere sits near weak-
temperature-gradient balance: Z500 and MSLP variance over Amazonia is a fraction of its
value at 30°S, so a SOM trained there would separate nodes by seasonal cycle and noise
rather than by nameable regimes. Three further reasons:

- **Scale.** At 1.0–1.5° / 6-hourly the grid resolves fronts, extratropical cyclones,
  SACZ, the low-level jet, MCCs and cutoff lows (1000+ km, 2–5 day life cycles). Amazon
  extremes come from coastal squall lines and diurnal convection (~100 km, sub-daily) —
  subgrid in this predictor space, so the causative system is simply absent from the state.
- **Ground truth.** Criteria 1–3 in §4.2 rest on BR-DWGD grid-point maxima being real.
  BR-DWGD is interpolated from gauges, densest in S/SE and sparsest in the Amazon, with a
  station network that changes across 1980–2014. Northern "record breaks" would partly be
  interpolation and network artifacts.
- **The method's own bet.** §1 stakes the project on the self being compact inside a SOM
  node. That compactness *is* the strength of the synoptic conditioning; weak conditioning
  in the tropics leaves the self diffuse and removes the reason the method should work.

**Why −10 rather than −14.** The SACZ runs NW–SE from southern Amazonia (~8–12°S) across
MG/SP/RJ and out over the subtropical Atlantic, and is the dominant austral-summer extreme
driver for the Southeast. A cut at 14°S slices it through the middle, keeping the oceanic
half and dropping the continental anchor where it meets the low-level jet's moisture
transport. Since SACZ episodes differ mainly in *where* the band sits — northward-displaced
rains on Minas, southward-displaced on São Paulo/Rio — truncation invites the SOM to
collapse two physically distinct regimes into one node, and position is precisely what
determines the flood footprint.

Enlarging the *input* while holding the *target* fixed is what makes this consistent with
the paragraph above: the added 10–14°S rows carry little geopotential variance, which is
harmless as SOM input and would have been a real problem as evaluation area. Cost is +19%
volume (~20 → ~24 GB, §3.5) — negligible against the 50 GB phase-0 budget.

**What this decision assumes, and how it is checked.** The SOM does not read the grid
directly — a PCA to `d` = 10–15 sits between the crop and the training, so the added cells
only buy separability if SACZ-position variability survives into the retained components.
That is expected (band displacement is a large-scale, high-variance mode that should load
on the leading EOFs) but unverified. §6 step 4 makes it an explicit phase-0 check.

Note also what the enlargement does *not* do: the SOM has no notion of "reasons" for a
node assignment — the BMU is simply the nearest codebook vector. The gain is that two
physically distinct configurations land far apart in input space instead of nearly on top
of each other, so they can occupy separate nodes. Separability, not explanation.

**Unchanged.** Widening further via `--area` remains the documented mitigation if the
phase-0 event count comes up short (§6, and PLAN.md risk table) — to be done before
anything is built on the regimes, not after.

---

## 4. Experimental protocol

### 4.1 Temporal split

- **Train:** 1980–2014 (~12,800 days)
- **Test:** 2015–2025 (~4,000 days)

The cut is strict: nothing from the test period enters the PCA fit, the SOM training, or
the definition of self.

### 4.2 Operational definition of "unprecedented"

Four criteria, computed **on the training window only**, reported separately.

1. **Record break** — exceeds the 1980–2014 maximum at the grid point, for 1-, 3- and
   5-day accumulation windows. Record the margin in standard deviations.
2. **Record-shattering** — the exceedance margin exceeds any previous margin.
3. **GEV return period** — GEV fitted on train only; events with return period > 100 years.
4. **State-space novelty** — nearest-neighbour distance within train above the 99.9th
   percentile of internal train distances.

Criteria 1–3 measure impact magnitude; criterion 4 measures novelty of the atmospheric
configuration. **They are different things, and the generator is judged mainly by 4.**

Known trap: under a warming trend, temperature and humidity records break on their own.
Detrend or use a non-stationary GEV, and document the choice.

Sanity check: the automatic list must contain Petrópolis 2022, Rio Grande do Sul 2024 and
the 2014–2015 Southeast drought. If it does not, the criterion is miscalibrated.

### 4.3 Core evaluation (detection)

Mandatory baselines:

- per-grid-point 99th percentile threshold (what is used in practice);
- global Isolation Forest (no regime conditioning);
- global One-Class SVM;
- **per-regime Isolation Forest** — the baseline that isolates the AIS contribution from
  the SOM contribution.

Metrics: POD, FAR, CSI, precision-recall curve, Brier score. Reported per forecast
horizon *h* = 1, 3, 5, 7 days, showing where skill collapses.

### 4.4 Extended evaluation (generation)

- **Level 1 — retained-event coverage.** For each real 2015–2025 extreme, distance to the
  nearest synthetic event. Compared against bootstrap resampling, Gaussian perturbation
  and a simple VAE. Harder variant: *leave-the-worst-out* — remove the 20 most extreme
  events from the whole record and test whether they are regenerated.
- **Level 2 — physical plausibility.** Pass rate through the three filters
  (thermodynamic, spectral, regime coherence), compared against baselines. The point is to
  pass **and** be novel.
- **Level 3 — CLIMBra convergence.** Overlap between the synthetic catalogue and the
  envelope projected by the physical models. Two independent methodologies agreeing is the
  strongest argument in the article.

Complementary: return periods of generated events under the fitted GEV must be plausible
(200–500 years), not absurd.

---

## 5. Tooling

| Use | Library |
|---|---|
| SOM | `MiniSom` (or ~30-line own implementation) |
| One-class baselines | `scikit-learn` (IsolationForest, OneClassSVM) |
| Evolutionary | `DEAP` or `pymoo` |
| MAP-Elites | `pyribs` or `qdpy` |
| Extreme values | `scipy.stats.genextreme`, `pyextremes` |
| Climate data | `xarray`, `dask`, `zarr`, `cdsapi`, `xesmf` / `xarray-regrid` |

Negative selection is **implemented here**, not imported: existing libraries are old and
poorly maintained, and the algorithm is short.

Dependencies are managed with `uv` from the repository root (`pyproject.toml`). Several
of the libraries above are not yet declared there and must be added before phase 0.

---

## 6. Immediate next steps

1. Test the retrieval with a single month before launching the full download:

   ```bash
   uv run python -m ingest.era5.download_era5_synoptic --years 1980 1980 --groups plev500
   ```

2. Launch the full retrieval (~24 GB, runs for days — it is resumable):

   ```bash
   uv run python -m ingest.era5.download_era5_synoptic --workers 3
   ```

3. Add the missing dependencies to the root `pyproject.toml` (`zarr`, `minisom`,
   `scikit-learn`, `pyribs` or `qdpy`, `pyextremes`, `xarray-regrid`), then `uv sync`.
4. **Check that the enlarged predictor box paid off.** The −10 northern edge (§3.7) only
   helps if SACZ-position variability survives the PCA into the retained components
   (`d` = 10–15) — otherwise the extra rows are 4 GB of nothing. After the first PCA fit,
   plot the leading EOFs and confirm that one of them looks like a SACZ displacement or
   dipole mode, with structure north of 14°S. Band displacement is a large-scale,
   high-variance pattern and should load on the leading components, but this is an
   assumption to verify, not a certainty. If no such mode appears, revisit the crop before
   training the SOM — and note that the widening cannot help separate regimes the PCA has
   already discarded.
5. Confirm the extended (generative) version and publication horizon with the advisor.
6. Confirm T1 and T2 deadlines and realign the schedule.
7. Run the extreme-event count over the test period — 30–40 well-distributed cases sustain
   the validation, 5 do not. If the count is short, widen the region with `--area` before
   anything else is built on top.
8. Read Lehman & Stanley (2011) and Ji & Dasgupta (2007) — the two that most change design
   decisions.

---

## 7. Relation to the thesis

The thesis uses ERA5 (reanalysis) to improve CLIMBra (physical models), with BR-DWGD as
the observational reference. The motivation is the tension between projection capability
and explainability: physical models explain behaviour in 2100, ML methods do not.

This project attacks that tension sideways. Each SOM node is an interpretable synoptic
map, and each AIS detector is an inspectable object in state space — not a weight inside a
network. It is a machine learning approach whose internal objects a climatologist can look
at, name, and criticise.
