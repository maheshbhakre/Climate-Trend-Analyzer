# Phase 2 Climate Analytics

## Inputs and scope

All analytics use the canonical processed observations in `data/processed/climate_cleaned.csv`: date, average temperature, reported temperature uncertainty, location labels, coordinates, year, and month. No rainfall, greenhouse-gas, sea-level, or other unobserved indicator is estimated. The output is descriptive analysis of the available city observations.

## Methodology

- **Annual and monthly trends:** arithmetic means across available rows, with observation counts and mean reported uncertainty. The pooled mean weights each source row equally; it is not area- or population-weighted.
- **Temperature change:** annual pooled means are compared with the first observed annual mean. Country and city warming rates are ordinary least-squares slopes through each place's annual means, multiplied by ten for °C per decade. They are descriptive and sensitive to the observed time window and uneven coverage.
- **Rolling average:** a trailing window over monthly pooled means. Missing calendar months remain missing; no measurements are interpolated. The default dashboard window is 12 months.
- **Decades:** calendar years are grouped by decade (`year // 10 * 10`). Change compares each decade with the previous decade present in the data. If decades are absent, this is a comparison between adjacent observed groups, not necessarily consecutive decades.
- **Seasonality:** pooled calendar-month means provide warmest/coldest month and spread. Seasonal profiles use meteorological seasons and reverse labels for Southern Hemisphere observations. Equatorial observations remain in monthly totals but are omitted from the four-season profile because latitude alone does not establish local seasonal regimes.
- **Statistical trend:** OLS fits annual pooled mean temperature against calendar year and reports slope, R², Pearson correlation, p-value, and nominal 95% intervals. The confidence intervals use standard OLS assumptions; temporal autocorrelation, changing spatial composition, measurement-system changes, and missing coverage are not modeled. They should not be interpreted as causal evidence or a formal global climate estimate.
- **Uncertainty:** reported uncertainty is summarized globally, by country, and by city-country pair. The 0–100 range-relative reliability score compares mean reported uncertainty with the full observed temperature range. It is a heuristic only, not a probability, calibrated confidence score, or replacement for the Phase 1 quality score.
- **Rankings and insights:** country warming rankings use the OLS warming-rate estimate; city average-temperature rankings use row means. Automatically generated statements quote these computed values and do not imply causal attribution.

## Limitations

The source does not include source provenance or its unit/uncertainty definition in this repository; canonical values are conventionally represented in degrees Celsius. Geographic and temporal coverage is uneven, records are not equally representative of Earth's area, and source city/country labels are not reconciled to a reference gazetteer. Early periods contain fewer observations, so pooled means can change when the mix of reporting cities changes. Statistical intervals do not account for serial dependence or spatial sampling. Results are exploratory summaries and should be checked against authoritative, homogenized datasets before research or policy use.

## Reports

Running `python preprocess.py` refreshes the processed data and writes the six Phase 2 CSV reports under `outputs/reports/`: country trends, city trends, seasonality, decade trends, statistical trend, and uncertainty. The Streamlit pages use these reports and calculations from the same canonical observations.
