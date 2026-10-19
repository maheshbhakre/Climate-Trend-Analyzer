# 🌍 Climate Trend Analyzer — AI Climate Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pandas](https://img.shields.io/badge/Pandas-Analytics-green)
![Plotly](https://img.shields.io/badge/Plotly-Interactive%20Charts-purple)
![Streamlit](https://img.shields.io/badge/Streamlit-Enterprise%20Dashboard-red)
![Statsmodels](https://img.shields.io/badge/Statsmodels-Forecasting-orange)
![Status](https://img.shields.io/badge/Status-Phase%205%20Complete-brightgreen)

---

## 📌 Overview

Climate Trend Analyzer is an end-to-end **AI Climate Intelligence Platform** built with Python, Streamlit, Pandas, Plotly, and statistical forecasting models.

It transforms historical city-level temperature observations into an interactive decision-support system that helps users:

* 📈 Understand long-term temperature trends
* 🌡️ Compare countries and cities across decades
* 🚨 Detect unusual temperature anomalies
* 🔮 Explore transparent country and city forecasts
* 📊 Evaluate trend strength and statistical confidence
* ✅ Inspect data quality, coverage, and validation results
* 🧠 Translate analytical reports into climate intelligence insights

**Author:** Mahesh Bhakre<br>
**Dashboard:** `streamlit run app/app.py`

---

## 🎥 Dashboard Preview

The dashboard is built as a premium Streamlit experience with a midnight-navy glassmorphism design system, interactive Plotly charts, reusable cards, alert states, and visible author branding.

![Executive Overview](images/output/overviev.png)

![Global Climate Trends](images/output/global_climate_trend.png)

![Forecast Lab](images/output/forcast_lab.png)

---

## 🛠 Problem Statement

Climate data is difficult to interpret when data validation, trend analysis, anomaly detection, forecasting, and visualization are separated across notebooks and disconnected reports.

Key challenges include:

* ❌ Limited visibility into long-term warming patterns
* ❌ Difficult comparison across countries and cities
* ❌ No unified anomaly and alert workflow
* ❌ Forecast results separated from historical context
* ❌ Unclear data completeness and geographic coverage
* ❌ Technical outputs that are difficult for decision-makers to scan

---

## ✅ Solution

Climate Trend Analyzer provides a reproducible analytics pipeline and an executive-ready dashboard that combines:

* Historical climate trend analysis
* Rolling averages and decade comparisons
* Seasonal anomaly and alert intelligence
* Country and city forecasting with confidence bands
* Risk scoring based on observed and forecast temperature patterns
* Statistical evidence including slope, R², correlation, and confidence intervals
* Data quality, schema, completeness, validity, and coverage reporting
* Downloadable validated data and report artifacts

All dashboard insights are derived from the repository's existing calculations and report outputs. The platform does not fabricate climate findings or claim causal attribution.

---

## 🌐 Platform Pages

| Page | Purpose |
| --- | --- |
| 🏠 Executive Overview | High-level climate intelligence summary, KPIs, risks, alerts, and forecast status |
| 🌍 Global Climate Trends | Annual temperature trends, rolling averages, decade shifts, and distributions |
| 🏛 Country Explorer | Country-level trends, anomalies, forecasts, uncertainty, and risk scores |
| 📍 City Explorer | City-level climate trends, forecasts, monthly patterns, and risk signals |
| 🚨 Climate Alert Center | Filterable anomaly console with severity and risk rankings |
| 🔮 Forecast Lab | Selectable country/city forecasts, horizons, models, and confidence bands |
| 📊 Statistical Intelligence | Trend slope, R², correlation, confidence intervals, and interpretations |
| ✅ Data Quality Center | Quality score, completeness, consistency, validity, and coverage |
| 📚 Dataset Explorer | Data dictionary, source fields, samples, coverage, and exports |
| ℹ️ Platform Information | Architecture, methodology, models, limitations, and provenance context |

---

## 🏭 Climate Intelligence Applications

| Use case | Application |
| --- | --- |
| Climate monitoring | Explore observed temperature movement across locations and time |
| Risk screening | Prioritize countries and cities using anomaly and forecast risk signals |
| Research support | Review transparent statistical summaries and uncertainty indicators |
| Data operations | Inspect quality, schema validity, missingness, and geographic coverage |
| Executive reporting | Convert analytical outputs into concise dashboard-ready insights |

---

## 📊 Analytics Capabilities

### Climate Analytics

* Annual and monthly temperature trend reports
* Rolling averages and seasonal patterns
* Decade-level temperature comparisons
* Country and city rankings
* OLS trend slope, R², correlation, and confidence intervals
* Temperature distribution and uncertainty analysis

### Climate Anomaly Engine

* Seasonal Z-score signals
* IQR-based outlier detection
* Rolling-deviation signals
* Moderate, severe, and extreme severity classes
* Historical anomaly records and climate alerts
* Country and city anomaly risk rankings

### Forecasting Intelligence Lab

* Country and city forecasting
* 12, 24, 36, and 60-month horizons
* Linear regression, ARIMA, and seasonal-naive benchmark models
* Chronological holdout metrics
* Forecast confidence bands
* Future temperature-pattern risk screening
* Forecast insights derived from model output and metrics

---

## 🏗 System Architecture

```text
Raw Climate CSV
      ↓
Preprocessing & Canonical Schema
      ↓
Data Validation Engine
      ↓
Trend Analysis Engine ──┐
Climate Anomaly Engine ─┼─→ Report Artifacts
Forecast Engine ────────┘
      ↓
Risk Scoring & Insight Generation
      ↓
Cached Streamlit + Plotly Dashboard
```

The analytical engines are separated from the presentation layer so the reports remain auditable and the dashboard remains fast, repeatable, and easy to validate.

---

## 📁 Project Structure

```text
AI-CLIMATE-TREND-ANALYZER/
├── app/
│   └── app.py
├── data/
│   ├── raw/
│   └── processed/
├── images/
│   └── output/
├── notebooks/
├── outputs/
│   └── reports/
├── src/
│   ├── anomaly_engine.py
│   ├── data_loader.py
│   ├── data_validation.py
│   ├── forecast_engine.py
│   ├── analysis.py
│   ├── forecasting.py
│   └── trend_analysis.py
├── tests/
├── docs/
├── main.py
├── preprocess.py
├── requirements.txt
└── README.md
```

---

## ⚙ Tech Stack

* **Language:** Python
* **Data Processing:** Pandas, NumPy
* **Statistical Analysis:** Statsmodels, descriptive statistics, OLS summaries
* **Forecasting:** Linear regression, ARIMA, seasonal-naive benchmark
* **Visualization:** Plotly
* **Dashboard:** Streamlit
* **Quality Engineering:** Pytest, compileall, pip check, Ruff-compatible codebase
* **Performance:** Streamlit cached data and resource loaders

---

## 📊 Dataset

The project uses historical city-level temperature observations with canonical fields for analysis, validation, anomaly screening, and forecasting.

### Core fields

* `date`
* `city`
* `country`
* `avg_temp_c`
* `uncertainty`
* `latitude`
* `longitude`

### Important scope note

The source contains average temperature and uncertainty observations. It does not contain rainfall, CO₂, sea level, renewable energy, or causal attribution variables.

---

## ⚙ Installation & Setup

```powershell
git clone https://github.com/maheshbhakre/Climate-Trend-Analyzer.git
cd Climate-Trend-Analyzer

python -m venv venv
venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🖥 Usage

```powershell
# Prepare the canonical processed dataset and report artifacts
python preprocess.py

# Launch the climate intelligence dashboard
streamlit run app/app.py
```

The application loads the validated dataset and report artifacts from `outputs/reports/`.

---

## 📈 Results & Report Artifacts

The repository contains generated evidence artifacts for:

* Data quality and coverage
* Schema validation
* Country and city trends
* Seasonality and decade trends
* Statistical trend summaries
* Uncertainty analysis
* Anomalies and climate alerts
* Historical records
* Country and city forecasts
* Forecast metrics and summary insights

These artifacts are the source of truth for dashboard cards and derived insights.

---

## 📸 Dashboard Implementation Proof

### 🔹 Executive Overview

![Executive Overview](images/output/overviev.png)

### 🔹 Global Climate Trends

![Global Climate Trends](images/output/global_climate_trend.png)

### 🔹 Country Explorer

![Country Explorer](images/output/country_explorer.png)

![Country Explorer Trend Graph](images/output/country_explorer_trendgraph.png)

### 🔹 City Explorer

![City Explorer](images/output/city_explorer.png)

![City Climate Graph](images/output/city_graph.png)

### 🔹 Climate Alert Center

![Climate Alert Center](images/output/climate_alert_center.png)

![Climate Alert Detail](images/output/alert_2.png)

### 🔹 Forecast Lab

![Forecast Lab](images/output/forcast_lab.png)

![Forecast Graph](images/output/forcast+graph.png)

---

## 🧠 Key Insights

* Historical temperature patterns can be reviewed consistently across countries and cities.
* Rolling, decade, and statistical views help separate short-term noise from longer-term signals.
* Anomaly severity and risk rankings help focus attention on unusual location-level behavior.
* Forecast confidence bands make future estimates easier to interpret with uncertainty in view.
* Data quality and coverage indicators make analytical limitations visible before interpretation.

These are analytical interpretations of the implemented reports, not causal climate conclusions.

---

## ✅ Validation

```powershell
pytest -q
python -m compileall -q app src tests preprocess.py main.py
python -m pip check
```

The test suite covers data loading, validation, trend analysis, anomaly generation, and forecast engine behavior.

---

## 📚 Documentation

* [Project audit](docs/project_audit.md)
* [Data dictionary](docs/data_dictionary.md)
* [Climate analytics](docs/climate_analytics.md)
* [Climate anomaly engine](docs/climate_anomaly_engine.md)
* [Forecasting Lab](docs/forecasting_lab.md)
* [Dashboard design system](docs/dashboard_design_system.md)
* [Recruiter demo guide](docs/recruiter_demo_guide.md)
* [Dashboard showcase guide](docs/dashboard_showcase_guide.md)

---

## ⚠️ Limitations

* Coverage is uneven across locations and time.
* Row-wise means are not automatically population-weighted, area-weighted, or globally representative.
* Trend estimates are descriptive and do not provide causal attribution.
* Anomaly flags are screening signals, not confirmed weather events or measurement errors.
* Future risk is a temperature-pattern screening score, not a calibrated hazard probability or loss model.
* Source publisher, license, and full unit provenance should be confirmed before formal redistribution or research publication.

---

## 🚀 Future Improvements

* Add a reproducible CI workflow for tests, lint, dependency checks, and screenshot smoke tests.
* Publish a versioned data provenance manifest and source citation.
* Add deployment configuration for Streamlit Community Cloud or container hosting.
* Add geography normalization and population/area-weighted aggregations.
* Add richer scenario analysis when additional climate indicators become available.

---

## 👨‍💻 Author

**Mahesh Bhakre**<br>
Data Science · Climate Analytics · Forecasting · Streamlit Product Design · Plotly Visualization

---

## 🌐 Connect With Me

<a href="https://github.com/maheshbhakre">
<img src="https://img.shields.io/badge/GitHub-Profile-black?style=for-the-badge&logo=github" alt="GitHub Profile">
</a>

<a href="https://www.linkedin.com/in/maheshbhakreds1242">
<img src="https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin" alt="LinkedIn Profile">
</a>

<a href="https://www.instagram.com/mahesh_bhakre__2k06">
<img src="https://img.shields.io/badge/Instagram-Follow-purple?style=for-the-badge&logo=instagram" alt="Instagram Profile">
</a>

<a href="https://saimfsd.github.io/mahesh-portfolio/">
<img src="https://img.shields.io/badge/Portfolio-Visit%20Website-orange?style=for-the-badge&logo=google-chrome" alt="Portfolio Website">
</a>

---

## ⭐ Portfolio Note

This project demonstrates a complete climate analytics workflow covering:

* Data preprocessing and validation
* Reproducible climate trend analysis
* Anomaly and alert intelligence
* Transparent forecasting with uncertainty
* Risk scoring and evidence-based insights
* Interactive Streamlit product design
* Executive-level Plotly visualization
* Documentation and release-quality engineering

---

## 🎯 Interview Pitch

> “I built an AI-powered Climate Intelligence Platform using Python, Streamlit, Pandas, Plotly, and statistical forecasting models. It validates climate data, analyzes country and city temperature trends, detects anomalies, generates forecast scenarios with confidence bands, scores future temperature-pattern risk, and presents the results through an executive-ready interactive dashboard.”

---
