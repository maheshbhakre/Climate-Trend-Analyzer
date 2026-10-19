# Phase 4 Forecasting Intelligence Lab

## Input and forecast origin

The engine accepts the Phase 1 canonical monthly temperature schema. It aggregates `avg_temp_c` by observed calendar month for global pooled, country pooled, or city-country series. Monthly observation uncertainty is retained for reporting, but is not used as a model feature because this repository does not document how the source uncertainty should be propagated through monthly aggregation. No rainfall, CO₂, sea level, pollution, or other external indicators are used.

The active application dataset is `data/processed/climate_cleaned.csv` (228,175 observations, 49 countries, 100 cities, last observation 2013-09). The separately referenced `data/processed/cleaned_climate.csv` contains 1,777 Abidjan observations and ends 2013-08. Both are canonical; the dashboard uses the larger Phase 1/2/3 dataset.

The series preparation step selects the latest uninterrupted month-to-month observed segment, with no interpolation or gap filling, and caps training at 720 months. The forecasts therefore begin after the last observed month in the selected segment; this dataset's 60-month horizon ends in 2018, not in the present. Country and global means weight available source rows equally, so changing location coverage can affect them.

## Models

- **Linear regression:** OLS with a linear time index plus fixed calendar-month effects. It is transparent and extrapolates a linear trend with recurring seasonality. Its 95% observation prediction intervals include fitted residual variability and coefficient uncertainty.
- **Seasonal ARIMA:** ARIMA(1,1,1)(1,1,0)[12], fitted to the observed consecutive monthly series. Statsmodels supplies the 95% forecast intervals.
- **Seasonal naive baseline:** repeats the last observed 12 monthly values. The 95% interval uses empirical one-year seasonal-naive residual spread and widens with forecast years. It is a benchmark, not a physical model.

Supported forecast horizons are 12, 24, 36, and 60 months. Automated reports compare all three models on a chronological 12-month holdout, then refit the model with lowest holdout RMSE for each location and produce the default 12-month report forecast. The interactive page lets the user choose a supported horizon and model.

## Evaluation

MAE and RMSE are expressed in degrees Celsius. MAPE is reported in percent and omits holdout points whose observed temperature is effectively zero; if all holdout values are zero, MAPE is undefined. R² is computed over the held-out period and may be negative when a model performs worse than the holdout mean. Model selection uses holdout RMSE only. The holdout is a single recent period and is not repeated rolling-origin validation.

## Future temperature-pattern risk

The risk screen compares forecast point estimates with the same-calendar-month 5th–95th percentile range from up to the latest 30 years of observed data. Frequency is the percentage of horizon months outside that range; magnitude scales mean outside-range departure against 10 °C; persistence scales the longest consecutive outside-range run against 12 months. The score weights these components 40%, 35%, and 25%, respectively. Levels are Low (<25), Medium (25–<50), High (50–<75), and Critical (≥75). This is an exploratory temperature-pattern score, not a probability of hazard, loss, or impact.

## Reports

`forecasts.csv` contains monthly predictions and intervals, selected model, training dates, and risk score. `forecast_metrics.csv` stores holdout performance by model and location. City and country reports summarize the selected-model horizon, holdout RMSE, and risk components. `forecast_summary.json` records the forecast origin, global best model and metrics, insights, and key limitations. Running `python preprocess.py` refreshes the reports in `outputs/reports/`.

## Limitations

The dataset is historical and ends in 2013. Forecasts are an extrapolation from that source snapshot, not a current outlook. The source does not bundle its provenance or detailed uncertainty definition. Models do not account for policy, emissions, circulation, land-use, or any other forcing, and do not support causal attribution. The climate anomaly risk screen does not represent exposure, vulnerability, population, or damages. Validate forecast skill over multiple rolling-origin periods and against homogenized authoritative data before any decision use.
