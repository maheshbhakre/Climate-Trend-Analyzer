# Phase 1 repository audit

Audit scope: `README.md`, `requirements.txt`, `main.py`, `preprocess.py`, all files under `src/` and `app/`, the raw and processed data directories, `outputs/`, and `notebooks/`. This audit was completed before implementation changes using the repository files and a profile of `data/raw/climate.csv`.

## Current architecture before Phase 1

The repository was a small monolithic Streamlit dashboard with a standalone preprocessing script and separate, partially disconnected analysis modules:

- `data/raw/climate.csv` held the source observations.
- `preprocess.py` read the source, renamed some columns, derived year, fabricated rainfall and CO₂ values from temperature, and wrote one processed CSV.
- `app/app.py` independently loaded that processed CSV and rendered a Streamlit dashboard.
- `src/analysis.py` implemented plots, a linear regression, and global z-score flags against a different column naming scheme.
- `src/forecasting.py` fit ARIMA against yet another assumed date/temperature schema and was not integrated into the app or CLI.
- `main.py` attempted to connect preprocessing and analysis but imported a function that did not exist.
- `outputs/` contained screenshots/figures, not machine-readable audit reports. `notebooks/` was empty at audit time.

## Current data flow before Phase 1

`data/raw/climate.csv` → ad hoc renaming in `preprocess.py` → synthetic indicator columns added → `data/processed/climate_cleaned.csv` → dashboard reads relative path → filters and charts.

There was no shared loader, formal schema, data-quality report, date/coordinate validation, or provenance record. Processed files had multiple names and differing sizes, and their relationship was undocumented.

## Actual data profile

Observed raw header:

```text
dt, AverageTemperature, AverageTemperatureUncertainty, City, Country, Latitude, Longitude
```

Profile from the current file snapshot:

- 239,177 rows and 7 columns.
- Date range: 1743-11-01 through 2013-09-01; no malformed date values found.
- 49 country labels and 100 city labels.
- 11,002 missing values in `AverageTemperature` and the same 11,002 rows missing `AverageTemperatureUncertainty`.
- No other missing fields found in the snapshot.
- No exact duplicate rows or repeated `(dt, City, Country)` observation keys found.
- Temperature values ranged from -26.772 to 38.283 in the source numeric field.
- Latitude/longitude are text encoded with hemisphere suffixes, for example `5.63N` and `3.23W`.
- Dataset publisher, source citation, source license, and explicit measurement units are not recorded in the repository. Do not guess them.

These are snapshot-specific counts; rerun preprocessing and report generation after replacing the source data.

## Broken components found before Phase 1

1. `main.py` imported `clean_data` from `preprocess.py`, but that function was absent.
2. `main.py` and `src/analysis.py` expected `Date`, `Temperature`, `Month`, and `Year`; the raw file used `dt`, `AverageTemperature`, etc.
3. `preprocess.py` executed on import instead of exposing a safe reusable pipeline.
4. The preprocessor fabricated `co2_emissions` and `rainfall_mm` by multiplying temperature by constants.
5. The dashboard selected and displayed those fabricated fields as climate indicators.
6. `src/forecasting.py` expected `Date` and `Temperature`, did not select a geographic series, and assumed the observations form a regular monthly time series.
7. Dashboard and CLI paths were relative to the process working directory.
8. The README described unprovided rainfall, emissions, sea level, renewable energy, extreme weather, and forest metrics, and included an unrelated repository clone URL.

## Data contract issues

- No canonical field names or explicit source-to-canonical mapping existed.
- Uncertainty existed in the raw source but was omitted from the dashboard.
- Hemisphere suffix coordinates were not parsed to signed numeric degrees.
- Invalid dates, missing temperatures, invalid coordinates, temperature plausibility, and duplicates had no consistent audit policy.
- Multiple processed CSVs (`climate_cleaned.csv`, `cleaned_climate.csv`, `climate_data.csv`) were present without documented lineage.
- The source's unit, publisher, citation, and license metadata are absent; the project must retain this as an explicit provenance gap.

## Code integration problems

- Preprocessor, CLI, analytics modules, forecast helper, and dashboard used incompatible schema conventions.
- `main.py` could not execute through its missing import and also called analyses requiring fields absent from preprocessing output.
- Dashboard hard-coded only the current processed file name and used bare exception handling around file read.
- Global country ranking was labelled as “Top Performers,” which implies value judgment for temperature.
- Global z-score anomaly logic compared observations from different places and local climates.
- ARIMA had no location selector, frequency check, gap check, or forecast evaluation.

## Technical debt

- No tests existed at audit time.
- Dependencies were unpinned and `requirements.txt` was empty at the initial audit.
- No data dictionary or machine-readable quality reports existed.
- README contained mojibake and stale claims.
- Dashboard rendered without visible sources, units caveat, coverage notes, or data-quality indicators.
- Project paths were coupled to the launch directory.
- Generated/processed data provenance and refresh procedure were unclear.

## Phase 1 implementation decisions

- Canonical output: `date`, `avg_temp_c`, `uncertainty_c`, `city`, `country`, `latitude`, `longitude`, `year`, `month`.
- Keep source rows in reports; exclude rows with missing required values or failed date, coordinate, temperature-screening, or uncertainty checks from the clean analytical output.
- Temperature plausibility screen: -90 °C to 60 °C. This is a broad guardrail, not source-specific scientific validation.
- Quality score: equal-weight average of completeness, duplicate-key consistency, observed calendar-month coverage across the file-wide span, and validity. Always expose component scores and formula description.
- No fabricated climate indicators, unsupported correlations, or causal interpretations.
- The exploratory annual mean is explicitly an unweighted mean of available city rows and not automatically globally representative.

## Phase 1 execution results

- The 239,177-row raw file produced 228,175 canonical valid records; 11,002 rows with missing temperature/uncertainty were excluded from the analytical output and remain counted in audit reports.
- The quality score is 99.67/100 (Excellent) under the documented component method. Completeness is 98.69%; consistency, overall month coverage, and validity are 100% for this snapshot.
- `cleaned_climate.csv` and `climate_data.csv` were migrated from their legacy 10-column naming (including an undocumented `Z` field) to the canonical nine-field schema. They remain historical snapshots and are not used by the application.
- `outputs/reports/` now contains quality, coverage, schema-validation, and data-dictionary CSV reports.
- Automated tests, Ruff lint/format checks, compile checks, dependency consistency, CLI execution, and Streamlit startup were verified. See the implementation report returned with this change for the detailed results.

## Files and folders audited

- README, requirements, CLI, preprocessing, analysis, forecasting, dashboard.
- Raw source CSV and all three existing processed CSV files.
- Output images and screenshots.
- Notebooks folder (empty at audit time).
