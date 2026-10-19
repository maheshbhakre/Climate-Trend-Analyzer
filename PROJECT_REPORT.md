# AI Climate Trend Analyzer: Project Report and Copilot Brief

> **Phase 1 status update (2026-10-18):** This report began as a pre-implementation audit and roadmap. Phase 1 is now implemented: the data pipeline uses the canonical nine-field schema, fabricated indicators have been removed from executable code and processed snapshots, audit reports and tests have been added, and the dashboard has three working pages. For the current implementation and measured data-quality results, see [docs/project_audit.md](docs/project_audit.md), [docs/data_dictionary.md](docs/data_dictionary.md), and `outputs/reports/`.

## 1. Executive summary

AI Climate Trend Analyzer is a Python data-analysis project with a Streamlit web dashboard. Its raw data is a historical temperature table containing date, city, country, coordinates, average temperature, and measurement uncertainty. The project currently includes a cleaning script, exploratory-analysis and anomaly functions, an ARIMA forecasting function, and a dashboard with country and year filters.

The dashboard can be started with `streamlit run app/app.py` after installing dependencies. Its Plotly import issue was caused by an incomplete Plotly installation and has been resolved in the local `venv`. The dashboard reads `data/processed/climate_cleaned.csv` and currently starts successfully.

The project is a useful prototype, but its descriptions and several displayed metrics go beyond what the underlying dataset supports. The raw file contains temperature observations only. Rainfall and CO2 columns are currently calculated as arbitrary multiples of temperature, so they are synthetic placeholders rather than climate measurements. The first priority for any advanced version should be data integrity, consistent preprocessing, and honest labeling. Forecasting, richer analytics, and deployment should follow that foundation.

## 2. Project purpose and intended users

The project aims to make historical climate observations easier to explore. Likely users include students, educators, analysts, and climate researchers who want to:

- Inspect how recorded average temperatures vary over time.
- Compare countries and, where supported by the data, cities or regions.
- Explore uncertainty and data coverage.
- Identify unusual values for further review.
- Produce transparent summaries and export filtered data.

The current dashboard is an exploratory tool. It should not be described as a policy-grade climate model or source of causal conclusions without better validated data and methods.

## 3. Current repository map

| Path | Current role | Notes |
| --- | --- | --- |
| `app/app.py` | Streamlit dashboard | Loads the processed CSV, filters by country/year, displays summary metrics and Plotly charts, and offers a CSV download. |
| `preprocess.py` | Raw-data transformation script | Renames selected columns, parses dates, derives year, drops rows missing core fields, and writes `climate_cleaned.csv`. |
| `src/analysis.py` | EDA, linear trend, anomaly detection | Uses Matplotlib, Seaborn, NumPy, and scikit-learn. Its expected column names do not currently match `preprocess.py` output. |
| `src/forecasting.py` | ARIMA forecasting function | Uses statsmodels and expects a `Date` column with a regularly sampled temperature series. It is not connected to the dashboard or `main.py`. |
| `main.py` | Intended command-line analysis flow | Currently calls `clean_data`, which is not defined in `preprocess.py`, and expects columns that do not match the raw CSV or preprocessor output. |
| `data/raw/climate.csv` | Primary source dataset | Header: `dt, AverageTemperature, AverageTemperatureUncertainty, City, Country, Latitude, Longitude`. |
| `data/processed/climate_cleaned.csv` | Dashboard input | Has normalized `date`, `avg_temp_c`, `country`, and `year`, plus two synthetic placeholder columns. |
| `data/processed/cleaned_climate.csv`, `climate_data.csv` | Older processed files | Their relationship to current processing is unclear; confirm provenance before using them. |
| `outputs/` | Saved images | Includes chart and dashboard screenshots. The README references several dashboard images. |
| `requirements.txt` | Python dependencies | Was empty; it now lists the packages imported by the current project modules. |
| `README.md` | Project introduction and setup | Describes more climate indicators than the raw data provides, and its clone URL points to an expense tracker repository. |

The repository also contains `notebooks/` and `.vscode/`; inspect their contents before reorganizing or deleting anything.

## 4. Data profile and meaning

### Raw fields

| Field | Meaning | Suggested handling |
| --- | --- | --- |
| `dt` | Observation date | Parse strictly or with a documented coercion policy; retain the original value when auditability matters. |
| `AverageTemperature` | Average temperature for the row | Normalize to `avg_temp_c` only after confirming the source unit and documenting it. |
| `AverageTemperatureUncertainty` | Reported uncertainty for the temperature value | Preserve this field; it enables uncertainty-aware visualizations and quality checks. |
| `City`, `Country` | Geographic labels | Normalize whitespace and missing values; do not silently merge distinct names. |
| `Latitude`, `Longitude` | Geographic coordinates expressed as text with hemisphere suffixes | Parse to numeric signed coordinates before mapping or spatial aggregation. |

### Critical data-quality point

There is no observed precipitation/rainfall field or CO2 field in the raw CSV. The current preprocessor creates `co2_emissions = avg_temp_c * 1.5` and `rainfall_mm = avg_temp_c * 2.0`. These calculations have no physical or data-source justification. Remove them or mark them explicitly as illustrative synthetic demo values and keep them out of factual insights. A real multi-indicator dashboard requires reputable datasets for each additional metric, documented units, source links, time coverage, and a clear join key such as country and year.

## 5. What the current dashboard does

1. Configures a wide Streamlit page.
2. Reads `data/processed/climate_cleaned.csv` relative to the current working directory.
3. Lowercases all column names.
4. Offers a multi-select for countries, a year-range slider, and a metric selector.
5. Filters rows and stops with a warning when there are no rows.
6. Shows average, maximum, minimum, and number of countries for the selected filter.
7. Draws a yearly line chart, a top-country bar chart, and a value histogram.
8. Displays a short insight box and a 100-row preview.
9. Exports the full filtered rows as CSV.

### Dashboard caveats to address

- Metric choices currently include synthetic rainfall and CO2 placeholders. Remove them until they are backed by real data or label them as synthetic.
- “Top performers” is not meaningful for temperature: higher temperature is not universally better. Rename it to a neutral label such as “Countries with highest selected average” and explain what ranking means.
- The chart averages observations by year and country selection. State whether the global comparison is an unweighted mean of city/country rows; consider population- or area-weighting only if a credible weighting dataset is added.
- Uncertainty is not shown even though the source includes it.
- The broad `except:` hides whether the file is missing, malformed, or permission-blocked. Use a specific error and actionable guidance.
- Relative paths depend on launching Streamlit from the repository root. Resolve paths from the application file or project root.
- Empty or malformed datasets may break the slider, metric calculation, or top/bottom country indexing. Validate schema, non-empty values, and numeric columns before rendering.
- Chart APIs emit deprecation warnings for `use_container_width`; update to the current supported width argument during dashboard maintenance.
- The page has no clear source/citation, data coverage details, units, caveat panel, or last-refresh metadata.

## 6. Current code health and integration gaps

### Preprocessing

`preprocess.py` runs its work at import time and has no reusable `clean_data` function, even though `main.py` imports that name. It writes one output file while the dashboard uses a different convention from the other older processed files. Its current transformation also fabricates non-temperature metrics. Refactor it into small functions such as `load_raw_data`, `validate_schema`, `clean_data`, and `save_processed_data`, with a guarded command-line entry point (`if __name__ == "__main__":`).

### Main analysis flow

`main.py` imports the missing `clean_data` function. It then expects `Date`, `Temperature`, `Month`, and `Year`, while the raw source has `dt` and `AverageTemperature`, and the current preprocessor produces lowercase normalized names and `year`. The current program therefore cannot be relied on as a working end-to-end analysis command until the data contract is made consistent.

### Analysis functions

`src/analysis.py` expects title-cased columns (`Date`, `Temperature`, `Month`, `Year`) and mutates its input by adding rolling mean and z-score fields. It assumes data is sufficiently populated and that standard deviation is nonzero. The monthly aggregation requires a month field that the current preprocessor does not produce. Add clear function contracts, schema validation, handling for constant/short series, and return results instead of relying only on `plt.show()` and console output.

### Forecasting

`src/forecasting.py` fits ARIMA directly to the provided temperature rows and forecasts 24 steps. The source contains observations for many cities and countries, so it must first select a single location and sort/aggregate observations to a well-defined regular cadence. Forecast horizons need clear units (months/years), a train/test evaluation, baseline comparison, uncertainty intervals, and warnings against extrapolating beyond the observed series. It currently has no dashboard or CLI integration.

### Documentation and setup

README setup describes the high-level stack but its clone URL is unrelated to this repository. Its feature list claims rainfall and several other measures not present in the source file. Update it so all advertised metrics and workflows match implemented behavior. Pin or constrain dependency versions for reproducibility after the app is stabilized; the existing requirements list is currently unpinned.

## 7. Recommended target architecture

Keep the project simple and split responsibilities clearly:

```text
raw climate data
      |
      v
src/data_loader.py  -> schema checks, parsing, normalization
      |
      v
src/analysis.py     -> aggregation, trends, anomalies, evaluation
      |                          |
      +--------------------------+
                                 v
                         app/app.py (Streamlit UI)
```

Suggested boundaries:

- **Data layer:** resolve paths safely, read CSVs, validate required columns, parse date/coordinates, report rejected rows, and never invent observations.
- **Analysis layer:** pure functions that accept DataFrames and return DataFrames/scalars for trends, coverage, anomalies, and forecasts. Keep chart formatting in the UI layer.
- **UI layer:** filters and charts only; display friendly errors from validated data functions.
- **Configuration:** centralize source/output paths and documented metric metadata (display name, units, source, valid aggregation).
- **Tests:** add small fixture CSVs for valid data, missing columns, invalid dates, missing values, one-row data, and zero-variance series. Test calculations and failure messages.

## 8. Phased roadmap from small improvements to advanced capabilities

### Phase 1 — Make the existing project truthful and dependable

1. Establish one canonical schema (`date`, `avg_temp_c`, `uncertainty_c`, `city`, `country`, `latitude`, `longitude`, `year`, and optionally `month`).
2. Implement reusable preprocessing and align every consumer with that schema.
3. Remove fabricated rainfall/CO2 values and remove them from dashboard controls until real datasets are added.
4. Fix `main.py` so it can run preprocessing and analysis without missing imports or incompatible columns.
5. Add robust error messages for absent files, invalid columns, empty data, and missing metric values.
6. Replace broad exceptions, avoid mutating shared input data, and make all data paths independent of launch directory.
7. Update README claims and clone/setup instructions.

**Done when:** a clean environment can be set up, preprocessing produces the documented schema, the dashboard loads from the processed output, and every displayed metric maps to a real input field or a clearly labeled calculation.

### Phase 2 — Improve dashboard usefulness

1. Add an overview tab with source, units, date coverage, number of cities/countries, and missing-data counts.
2. Add uncertainty bands or error bars where the source’s uncertainty field can support them.
3. Add a location selector (country, then city) and comparison of selected locations.
4. Add neutral ranking labels, clear axes, units, and data coverage annotations.
5. Add a map only after coordinates are parsed and validated.
6. Add a data-quality tab and a filtered export that preserves source fields and applied filter metadata.
7. Add accessible color choices and readable light/dark theme behavior.

### Phase 3 — Strengthen scientific analysis

1. Define aggregation choices explicitly (city, country, or global) and explain observation weighting.
2. Add robust time-series summaries, long-term trend estimates, confidence intervals, and sensitivity to start/end year.
3. Compare anomaly methods (e.g., robust median/MAD and seasonal residuals) and label anomalies as records for review, not proof of extreme weather.
4. Evaluate forecasts with temporal holdout/backtesting and simple baselines; report MAE/RMSE and prediction intervals.
5. Prevent data leakage by splitting chronologically before model fitting.
6. Document limitations: station coverage changes, uncertainty, missingness, aggregation bias, and source revisions.

### Phase 4 — Add genuine multi-indicator climate analytics

1. Identify trusted sources for precipitation, emissions, sea level, renewable energy, forest coverage, and extreme events.
2. Store source, license, units, update frequency, geography resolution, and time coverage for every added dataset.
3. Normalize country identifiers with stable codes (e.g., ISO codes), and define temporal/geographic joins with explicit rules.
4. Show missing coverage rather than filling absent observations with fabricated values.
5. Provide side-by-side indicators and correlations with caveats; do not claim causation from correlation.

### Phase 5 — Operationalize

1. Add dependency lock/pins and documented Python support.
2. Add automated linting and unit/integration checks in CI.
3. Add reproducible data refresh commands with source provenance and validation summaries.
4. Add caching for expensive processing/model fitting and performance profiling on representative data.
5. Add deployment instructions, health checks, configuration through environment variables, and privacy/security review if user uploads are introduced.

## 9. Suggested user experience

- **Overview:** “What data is this?” and a clear snapshot of coverage and quality.
- **Explore:** selectable indicator, country/city, date range, aggregation, and units.
- **Trends:** observed series, uncertainty, long-term trend, and description of calculation.
- **Compare:** selected locations with meaningful comparison and clear sample coverage.
- **Anomalies:** method, threshold, flagged records, and a reminder that flags are not causal explanations.
- **Forecast:** location-specific forecast with backtest scores, interval bands, and limitations.
- **Data:** preview, source columns, missing values, and export.

## 10. Copilot instructions: ready-to-paste project brief

```text
You are helping me improve the existing AI Climate Trend Analyzer repository. First inspect the current code and data; do not assume the README is fully accurate.

Project today:
- Python project with a Streamlit dashboard at app/app.py.
- Raw input is data/raw/climate.csv. Its columns are dt, AverageTemperature,
  AverageTemperatureUncertainty, City, Country, Latitude, Longitude.
- preprocess.py currently writes data/processed/climate_cleaned.csv.
- The dashboard filters by country/year and displays temperature, country
  comparisons, a histogram, and CSV export.
- src/analysis.py contains plotting, linear trend, and z-score anomaly functions.
- src/forecasting.py contains an ARIMA function but it is not integrated.
- requirements.txt lists pandas, numpy, streamlit, plotly, matplotlib, seaborn,
  scikit-learn, and statsmodels.

Important correctness rules:
- The raw dataset contains temperature and its uncertainty, not observed
  rainfall, CO2, sea level, renewable energy, forest coverage, or weather-event
  counts. Do not fabricate those metrics. Remove synthetic placeholders or keep
  them clearly labeled as synthetic demo data and out of scientific results.
- Align preprocessing, analysis, dashboard, and documentation to one explicit
  schema. Preserve source fields and document units and transformations.
- Treat the data as city/country historical observations. Forecast only a
  selected, sorted, regularly sampled location or a clearly defined aggregate.
- Do not make causal claims from correlations or call anomalies confirmed
  extreme weather events.
- Use clear validation and actionable errors for missing files, columns, dates,
  empty data, and invalid selections. Avoid bare except blocks.
- Make file paths independent of the current working directory.
- Keep analysis functions testable and separate calculations from Streamlit UI.

Work in small, reviewable stages. Start by mapping existing behavior and fixing
the data contract and broken end-to-end flow. Before adding advanced features,
state the files you plan to change and the acceptance criteria. Preserve existing
useful behavior. Add focused tests for calculations and edge cases when the
analysis implementation changes, and run only the relevant checks. Update the
README to describe what is actually implemented. Do not add new external data
without documenting its source, license, units, join keys, and coverage.

Long-term direction:
1. Reliable preprocessing, schema validation, and reproducible setup.
2. Honest temperature dashboard with uncertainty, coverage, and location
   comparisons.
3. Statistically evaluated trends, anomaly review, and location-specific
   forecasts with backtesting and uncertainty intervals.
4. Real multi-indicator analytics only after trusted datasets and explicit joins
   are available.
5. CI, pinned dependencies, caching, deployment guidance, and performance work.

For each change, explain what changed, why it is correct for this dataset, how
it was checked, and any remaining limitations. Do not silently change the
meaning of a metric or hide data-quality problems.
```

## 11. Recommended first implementation sequence

1. Agree on the canonical column names and source units.
2. Refactor preprocessing into callable functions and eliminate synthetic indicators.
3. Align `main.py`, `src/analysis.py`, and dashboard to that schema.
4. Add targeted tests around data cleaning, annual aggregation, and invalid inputs.
5. Update README and add a data dictionary.
6. Only then implement uncertainty visualization and a location-aware forecasting workflow.

This sequence makes each later feature rest on a stable and defensible data foundation.
