# Climate Trend Analyzer

A Python and Streamlit project for exploring historical average-temperature observations. The Phase 1 dashboard reports only measurements present in the repository's raw dataset and derived calendar/geographic fields.

## What the current data supports

The source file `data/raw/climate.csv` has these columns:

| Source field | Canonical field | Meaning / unit |
| --- | --- | --- |
| `dt` | `date` | Observation date |
| `AverageTemperature` | `avg_temp_c` | Recorded average temperature; represented as °C by the canonical field convention. The source's unit documentation is not bundled in this repository. |
| `AverageTemperatureUncertainty` | `uncertainty_c` | Recorded temperature uncertainty; represented as °C by convention. Its precise source definition is not bundled. |
| `City` | `city` | Source city label |
| `Country` | `country` | Source country label |
| `Latitude` | `latitude` | Decimal degrees; N positive and S negative |
| `Longitude` | `longitude` | Decimal degrees; E positive and W negative |
| derived | `year` | Calendar year derived from `date` |
| derived | `month` | Calendar month (1–12) derived from `date` |

The repository does not record the dataset publisher, citation, license, or source unit specification. Confirm those details before redistributing the data or using it in a formal research publication. The raw data contains no rainfall, CO₂, sea-level, renewable-energy, forest-cover, or extreme-weather measurements. The application does not synthesize or display these as real climate indicators.

### Current repository snapshot

The inspected raw file has 239,177 rows covering 1743-11-01 through 2013-09-01, 49 country labels, and 100 city labels. There are 11,002 rows with missing temperature and uncertainty values; these are excluded from the 228,175-row canonical analytical dataset and reported in the quality outputs. No malformed dates or duplicate observation keys were found in this snapshot. Re-run preprocessing to refresh these figures when the source file changes.

See [docs/data_dictionary.md](docs/data_dictionary.md) for field-level definitions and [docs/project_audit.md](docs/project_audit.md) for the Phase 1 repository audit.

## Phase 2 analytics

The analyzer now adds descriptive annual/monthly trends, rolling averages, country and city summaries, hemisphere-aware seasonality, decade comparisons, OLS trend statistics, uncertainty summaries, and generated insights. The corresponding CSV reports are written to `outputs/reports/` by `python preprocess.py`.

Phase 3 adds location-specific anomaly detection with seasonal Z-score, IQR, and trailing rolling-deviation methods; severity classes; location risk scores; historical temperature records; and the Climate Alert Center. These signals use observed temperature values only. See [docs/climate_anomaly_engine.md](docs/climate_anomaly_engine.md) for thresholds, score definitions, and limitations.

Phase 4 adds the Forecast Lab with seasonal linear regression, seasonal ARIMA, a seasonal-naive benchmark, chronological holdout metrics, forecast intervals, and a future temperature-pattern risk screen. Forecasts use the latest contiguous observations and do not fill missing months. See [docs/forecasting_lab.md](docs/forecasting_lab.md) for model definitions and limitations.

The Streamlit app retains the Temperature Explorer, DATA QUALITY CENTER, and DATASET OVERVIEW pages and adds Global Climate Trends, Country Explorer, City Explorer, Seasonality Explorer, Decade Analysis, and Statistical Insights. All visuals summarize actual temperature observations. Read [docs/climate_analytics.md](docs/climate_analytics.md) for formulas, interpretation, and limitations.

## Architecture

```text
data/raw/climate.csv
        |
        v
src/data_loader.py -> normalize fields, dates, coordinates, and screen invalid rows
        |
        +--> src/data_validation.py -> quality, schema, and coverage reports
        +--> src/trend_analysis.py -> Phase 2 analytics reports
        |
        +--> data/processed/climate_cleaned.csv -> app/app.py
```

- `preprocess.py` provides the reusable data pipeline and command-line entry point.
- `main.py` runs preprocessing and descriptive summaries.
- `src/analysis.py` contains descriptive summaries, a simple annual linear trend, and within-city review flags.
- `src/forecasting.py` contains an experimental location-specific monthly ARIMA helper; it is not presented as validated forecasting.
- `app/app.py` provides the Phase 1 through Phase 3 pages and the Phase 4 Forecast Lab.

## Setup (Windows PowerShell)

```powershell
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

From the repository root:

```powershell
python preprocess.py
python main.py
streamlit run app/app.py
```

The preprocessing command writes the canonical processed dataset to `data/processed/climate_cleaned.csv` and audit CSV files under `outputs/reports/`. The dashboard can regenerate missing audit reports from the raw and processed files.

## Validation and tests

```powershell
pytest -q
python -m pip check
```

Tests use small in-memory fixtures. They do not replace provenance checks or validation against updated upstream source data.

## Data quality rules

- Required source fields are validated before processing.
- Dates are parsed and malformed dates are excluded from the cleaned output and counted in the reports.
- Coordinates are parsed from decimal values with optional N/S/E/W suffixes and checked against latitude/longitude bounds.
- Temperature plausibility screening uses a broad range of -90 °C to 60 °C. This is a guardrail, not a domain-specific certification.
- Rows missing required measurements or location/date values are excluded from the canonical output; source missingness remains visible in quality reports.
- Duplicate full rows and repeated `(date, city, country)` keys are counted.
- A 0–100 quality score equally weights completeness, consistency, calendar-month coverage, and validity. Levels are Excellent (≥90), Good (≥75), Moderate (≥60), and Poor (<60). Component definitions are displayed in the quality center and documented in the audit.

## Scientific limitations

- Coverage is uneven across locations and time. A row-wise mean is not necessarily population-weighted, area-weighted, or globally representative.
- Country/city labels are preserved from the source; no external geographic reconciliation is applied.
- The annual trend is descriptive and does not estimate causal attribution.
- Robust anomaly flags identify observations for review; they do not confirm extreme-weather events or measurement errors.
- The experimental ARIMA helper requires at least 36 consecutive monthly observations for one selected city-country pair, performs no imputation, and needs temporal backtesting before decision use.
- No multi-indicator correlations or causal conclusions are produced.

## Repository layout

```text
app/app.py
data/raw/climate.csv
data/processed/climate_cleaned.csv
docs/data_dictionary.md
docs/project_audit.md
outputs/reports/
src/data_loader.py
src/data_validation.py
src/analysis.py
src/forecasting.py
preprocess.py
main.py
tests/
```
