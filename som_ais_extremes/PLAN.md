# Detection and Generation of Precipitation Extremes with SOM + Artificial Immune Systems

Work plan — Bioinspired Computing course (T1, T2, T3) and extension towards publication.

---

## 1. The idea in one paragraph

The immune system recognises pathogens it has never seen, training only on examples of the
host organism. Climate extremes have the same structure: tens of thousands of ordinary
days, a few dozen extreme events, and the need to anticipate events without precedent. The
proposal uses a **SOM** to separate synoptic regimes (the context), **negative selection**
to build a detector repertoire per regime (what is anomalous *in that* context), and
**clonal selection + novelty search** to invert the use of the repertoire: instead of
classifying observed events, generate a catalogue of plausible extreme events that never
occurred.

**Core version (T3, December):** detection — the AIS classifies the degree of extremity
conditioned on the regime.

**Extended version (Feb/Mar, article):** generation — the AIS produces unprecedented
synthetic events, filtered by physical plausibility.

---

## 2. Architecture

```
daily ERA5 fields
        │
        ▼
  dimensionality reduction (PCA, d = 10–15)
        │
        ▼
  SOM (5×4 grid, starting candidate)  ──►  regime k for each day
        │              size chosen by QE / TE / min-samples-per-node — README §4.4
        │
        ▼
  for each regime k:
      self_k = normal days of regime k
      negative selection → detectors C_k, R_k
        │
        ├──► [core]       new day → degree of extremity
        │
        └──► [extension]  clonal selection + novelty/MAP-Elites
                              │
                              ▼
                        physical filter (Clausius-Clapeyron,
                        spatial coherence, CLIMBra envelope)
                              │
                              ▼
                        catalogue of synthetic extremes
```

### Role of each piece

| Piece | Function | Immune analogue |
|---|---|---|
| SOM | defines the context (synoptic regime) | tissue-specific tolerance |
| Negative selection | detector repertoire per regime | T-cell maturation in the thymus |
| Clonal selection | pushes detectors away from self | somatic hypermutation |
| Novelty / MAP-Elites | maintains repertoire diversity | lymphocyte lineage diversity |
| Physical filter | discards impossible candidates | protein biochemical viability |

---

## 3. Schedule

Assumed: semester from August to December 2026; extension from January to March 2027.
**Adjust to the actual T1 and T2 delivery dates.**

| Weeks | Phase | Deliverable | Risk |
|---|---|---|---|
| Aug 1–3 | Data reduction | Subset < 50 GB in Zarr | **High — blocks everything** |
| Aug 3 – Sep 2 | T1: Novelty Search | PDF slides | Low |
| Sep 2 – Sep 4 | SOM: training and regime validation | Plotted and named maps | Medium |
| Oct 1 – Oct 3 | T2: AIS | PDF slides | Low |
| Oct 2 – Oct 4 | Negative selection per regime | Detectors + dimensionality test | **High** |
| Nov 1 – Nov 3 | T3 core: evaluation and baselines | Results table | Medium |
| Nov 4 – Dec 2 | Monograph + presentation | T3 delivered | Low |
| Dec 3 – Jan 2 | Article draft (core version) | Manuscript v1 | Low |
| Jan 2 – Feb 3 | Generative extension | Catalogue + hindcast | **High** |
| Feb 4 – Mar 2 | Wrap-up and submission | Article submitted | Medium |

### Decision points

- **End of October** — if the negative-selection dimensionality test fails (detector count
  exploding), reduce `d` or change the representation. Do not move forward before
  resolving it.
- **Mid-November** — if the core version's results do not beat the baselines, T3 becomes
  an honest comparative study (still worth a grade) and the extension is reassessed.
- **Mid-January** — if the core draft is not ready, cut the extension. One submitted
  article is worth more than two half-finished ones.

---

## 4. Data

### 4.1 ERA5 — atmospheric predictors

Source: Copernicus Climate Data Store, via the `cdsapi` library.

**Crop:** South/Southeast Brazil — latitude −35 to **−10**, longitude −60 to −38. This is
the *predictor* box (SOM input); extremes are still detected and validated over
South/Southeast on BR-DWGD. The northern edge was moved from the originally suggested −14
to −10 so the SACZ axis is not truncated through its middle — see README §3.7 for the
full decision. Covering all of Brazil remains the wrong move: it multiplies the volume and
dilutes the synoptic regimes, which are regional.

**Period:** 1980–2025, daily temporal resolution (aggregated from hourly), spatial
resolution regridded to 1.0° or 1.5° (0.25° is not needed to characterise a synoptic
regime).

Pressure levels:

| Variable | Level | Why |
|---|---|---|
| Geopotential | 500 hPa | wave structure, troughs and ridges |
| Temperature | 850 hPa | air masses, fronts |
| Specific humidity | 850 hPa | moisture availability |
| Wind u, v | 850 hPa | advection, low-level jets |
| Wind u, v | 250 hPa | subtropical jet |

Single level:

| Variable | Why |
|---|---|
| Mean sea level pressure | position of systems |
| Precipitable water (total column) | available moisture |
| CAPE | convective instability |
| Total precipitation | target (but see 4.2) |

### 4.2 BR-DWGD — observed precipitation

Daily grid interpolated from Brazilian weather stations (Xavier et al.), 0.1° resolution.
**It is the reference truth for precipitation** — ERA5 precipitation has a known bias and
must not be used as the target.

Action: check the current version and coverage period before downloading; the dataset has
been extended more than once.

### 4.3 CLIMBra — physical model projections

Bias-corrected CMIP6 ensemble for Brazil (Ballarin et al., *Scientific Data*, 2023),
available in an open repository. Use in this project:

1. Build the **plausibility envelope** — 1st and 99th percentiles of each variable in the
   2050 and 2100 projections.
2. Convergence validation — compare the synthetic catalogue against the extremes that
   physics projects.

Download only what those two things need; the full ensemble is not required.

### 4.4 Phase 0 pipeline

```
hourly download → daily aggregation → regional crop → regrid →
concatenation → Zarr with chunking on the time axis →
deseasonalise → per-point z-score → sqrt(cos lat) weighting →
PCA → X (N, d)
```

Goal: **from ~1.5 TB to under 50 GB**. Without this, every iteration takes hours and the
schedule does not close.

The three steps between Zarr and PCA are not cosmetic and their order is fixed — the
latitude weighting must follow the z-score or it cancels exactly. See README §4.3.

Tools: `xarray`, `dask`, `zarr`, `cdsapi`, `xesmf` or `xarray-regrid`, `scikit-learn`
(incremental PCA).

---

## 5. What to study

A short list, in the order in which it changes design decisions.

**1. Ji & Dasgupta (2007), *Revisiting Negative Selection Algorithms***
The critical assessment of the technique: it documents the scalability problems in high
dimension and delimits where it works. Determines whether the method is viable. Read it
first. While there, look at the **V-detector** (Ji & Dasgupta, 2004), the variable-radius
variant worth implementing.

**2. Lehman & Stanley (2011), *Abandoning Objectives: Evolution through the Search for Novelty Alone***
The founding novelty-search paper, short and argumentative. Determines how the search is
formulated. The concept to master is the **behavioural descriptor** — the hardest design
decision in the technique.

**3. Coles (2001), *An Introduction to Statistical Modeling of Extreme Values***
Extreme value theory: GEV, generalised Pareto distribution, return periods. Read chapters
3 and 6 — chapter 6 covers non-stationary models and is what resolves the trap of records
broken purely by a warming trend. It is the basis of the "unprecedented" criterion and of
the validation metrics.

**4. Engelbrecht, *Computational Intelligence*, Part VI (AIS)**
Already in the course bibliography. Overview of the four models — negative selection,
clonal selection, immune networks, danger theory. The backbone of T2. Part II covers SOM.

**5. Mouret & Clune (2015), *Illuminating search spaces by mapping elites***
MAP-Elites. Probably what will actually be implemented; the coverage metric becomes a
figure in the article.

**6. Forrest et al. (1994) and de Castro & Von Zuben (2002)**
The two originals: negative selection and CLONALG. Short. From the first, extract the
probabilistic reasoning about how many detectors are needed — that is the calculation that
determines whether the method scales.

**7. Hewitson & Crane (2002), *Self-organizing maps: applications to synoptic climatology***
The bridge between SOM and meteorology. The reference that legitimises SOM for a climate
reader.

**8. Fischer, Sippel & Knutti (2021), on *record-shattering* events**
The scientific justification for the entire project in one paper. Trace from it the
**ensemble boosting** literature — it is the competing method this approach proposes to
make cheaper, and it needs to be cited.

Beyond these, when validating the regimes: regional literature on Brazilian synoptic
systems (SACZ, frontal systems, mesoscale convective complexes), needed to name the SOM
nodes.

### Tooling

| Use | Library |
|---|---|
| SOM | `MiniSom` (or an own implementation, ~30 lines) |
| One-class baselines | `scikit-learn` (IsolationForest, OneClassSVM) |
| Evolutionary | `DEAP` or `pymoo` |
| MAP-Elites | `pyribs` or `qdpy` |
| Extreme values | `scipy.stats.genextreme`, `pyextremes` |
| Climate data | `xarray`, `dask`, `zarr`, `cdsapi` |

Negative selection: **implement it yourself**. The existing libraries are old and poorly
maintained, and the algorithm is simple.

---

## 6. Experimental protocol

### 6.1 Temporal split

- **Train:** 1980–2014 (~12,800 days)
- **Test:** 2015–2025 (~4,000 days)

The cut is strict: nothing from the test period enters the PCA fit, the SOM training, or
the definition of self.

### 6.2 Operational definition of "unprecedented"

Four criteria, computed **using the training window only**. Report separately.

1. **Record break** — exceeds the 1980–2014 maximum at the grid point, for accumulation
   windows of 1, 3 and 5 days. Record the margin in standard deviations.
2. **Record-shattering** — the exceedance margin exceeds any previous margin.
3. **Return period by GEV** — fit GEV on train only; events with a return period above
   100 years.
4. **State-space novelty** — nearest-neighbour distance within train above the 99.9th
   percentile of the internal train distances.

Criteria 1–3 measure impact magnitude; criterion 4 measures novelty of the atmospheric
configuration. **They are different things, and the generator is tested above all by 4.**

**Trap to handle:** under a warming trend, temperature and humidity records break on their
own. Detrend or use a non-stationary GEV, and document the choice.

**Sanity check:** the automatic list must contain Petrópolis 2022, Rio Grande do Sul 2024
and the 2014–2015 Southeast drought. If it does not, the criterion is miscalibrated.

**Preliminary survey (do in phase 0):** count how many events remain after the margin
filter. Thirty to forty well-distributed cases sustain the validation; five do not, and
then the window must change or the region must be widened.

### 6.3 Core version evaluation (detection)

Mandatory baselines:

- 99th percentile threshold per grid point (what is used in practice);
- global Isolation Forest (without regime conditioning);
- global one-class SVM;
- Isolation Forest **per regime** — this is the baseline that isolates the contribution of
  the AIS itself, separated from the contribution of the SOM.

Metrics: POD, FAR, CSI, precision-recall curve, Brier score. Report per forecast horizon
*h* = 1, 3, 5, 7 days and show where skill collapses.

### 6.4 Extended version evaluation (generation)

**Level 1 — retained-event coverage.** For each real extreme in 2015–2025, distance to the
nearest synthetic event. Compare against generative baselines: bootstrap resampling,
Gaussian perturbation, simple VAE. Harder variant: *leave-the-worst-out* — remove the 20
most extreme events from the whole record and test whether they are regenerated.

**Level 2 — physical plausibility.** Pass rate through the three filters (thermodynamic,
spectral, regime coherence), compared against the baselines. The point is to pass **and**
be unprecedented.

**Level 3 — convergence with CLIMBra.** Overlap between the synthetic catalogue and the
envelope projected by the physical models. Two independent methodologies agreeing is the
strongest argument in the article.

Complementary: return periods of the generated events under the fitted GEV must be
plausible (200–500 years), not absurd.

---

## 7. Risks and challenges

| Risk | Impact | Mitigation |
|---|---|---|
| Dimensionality kills negative selection | Fatal to the method | `d` ≤ 15; regime conditioning already reduces it a lot; test early |
| Phase 0 slips | The whole schedule shifts | Freeze the crop in week 3, even if imperfect |
| SOM regimes do not match the literature | Loss of credibility | Validate in September, before building on top |
| Too few events in the test set | Validation without statistical power | Survey in phase 0; widen the region if necessary |
| Validating generation is intrinsically hard | Challenged in the defence and in review | Three independent levels; hindcast as anchor |
| "Why not Isolation Forest?" | Weakens the justification | Answer: IF classifies, it does not generate; detectors are explicit, mutable objects |
| Scope too large | Nothing gets finished | Core and extension kept separate, with a cut in January |

### The central challenge, in one sentence

Negative selection was largely abandoned precisely because it does not scale in high
dimension. **The bet of this work is that regime conditioning solves that**, because
inside a single SOM node the self occupies a compact region. If that bet fails, the method
fails — which is why the dimensionality test is the first experiment to run, in October,
and not an implementation detail.

---

## 8. Link to the thesis

The thesis uses ERA5 (reanalysis) to improve CLIMBra (physical models), with BR-DWGD as
the observational reference. The motivation is the tension between projection capability
and explainability: physical models explain behaviour in 2100, ML methods do not.

This project attacks that tension sideways. Each SOM node is an interpretable synoptic
map, and each AIS detector is an inspectable object in state space — not a weight inside a
network. It is a machine learning approach whose internal objects a climatologist can look
at, name, and criticise.

---

## 9. Immediate next steps

1. Confirm with the advisor the interest in the extended version and the publication
   horizon.
2. Confirm the T1 and T2 delivery dates and realign the schedule.
3. Open a CDS account and test `cdsapi` with one month of data before firing off the full
   download.
4. Check the current version and coverage of BR-DWGD and CLIMBra.
5. Run the extreme-event count survey over the test period.
6. Read Lehman & Stanley (2011) and Ji & Dasgupta (2007) — the two that most change design
   decisions.
