# Phase 3 Climate Anomaly Intelligence Engine

## Data and scope

The engine uses only canonical observed temperature and uncertainty records from the repository dataset. It compares each city-country series with its own observed history; it does not estimate rainfall, CO₂, sea level, pollution, forest cover, or impacts. The dataset is a collection of city observations with uneven temporal coverage, not an area-weighted global climate record.

## Detection methods

All methods emit a method-specific event with date, country, city, observed temperature, expected temperature, deviation, anomaly score, and severity. Same-month climatological baselines are computed by country, city, and calendar month, and require at least five observations for Z-score and IQR tests.

1. **Seasonal Z-score:** `(observation − same-city/month mean) / same-city/month sample standard deviation`. Absolute scores of 2 or greater are candidates. The expected value includes the observation being tested, so this is an exploratory retrospective detector.
2. **Seasonal IQR:** an observation outside `Q1 − 1.5 × IQR` or `Q3 + 1.5 × IQR` is a candidate. Its anomaly score is absolute departure from the same-month median expressed on a robust `IQR / 1.349` scale. If IQR is zero, the finite fallback score is the departure in °C; a zero departure has score zero.
3. **Rolling mean deviation:** the expected value combines the same-city/month climatology with the mean of the prior 12 deseasonalized residual observations. The current observation is excluded from this trailing baseline. A candidate must differ by at least 2 °C. Fewer than 12 prior observations produce no rolling result.

The detectors identify unusual values relative to the available local record. They are not mutually independent; one observation can have multiple method rows. Summary frequency and risk calculations deduplicate by location and date; the detail report intentionally preserves method rows.

## Severity

Severity uses the larger signal from absolute temperature departure and standardized anomaly score:

| Level | Temperature departure | Standardized score |
| --- | ---: | ---: |
| NORMAL | < 2 °C | < 2 |
| MODERATE | ≥ 2 °C | ≥ 2 |
| SEVERE | ≥ 4 °C | ≥ 3 |
| EXTREME | ≥ 6 °C | ≥ 4 |

Thus an observed departure of +6 °C is classified EXTREME. Statistical severity is not a statement about human or ecological impacts.

Location reports encode average severity as an ordinal mean: NORMAL=0, MODERATE=1, SEVERE=2, EXTREME=3. `severe_count` counts SEVERE plus EXTREME observations, while `extreme_count` counts only EXTREME observations.

## Climate risk score

Location scores combine three clipped 0–100 components: anomaly-observation frequency (40%), mean absolute deviation magnitude relative to 10 °C (35%), and persistence (25%). Persistence is the longest sequence of consecutive anomalous calendar months, scaled so 12 consecutive months equals 100. Final score levels are Low (<25), Medium (25–<50), High (50–<75), and Critical (≥75). This is a relative prioritization heuristic, not a calibrated probability or forecast of climate hazard or loss.

## Reports and insights

`python preprocess.py` writes `anomalies.csv` (method-specific detections), `climate_alerts.csv` (SEVERE and EXTREME detections), country and city risk summaries, `historical_records.csv` (observed temperature records and largest detected deviations), and `anomaly_summary.json` (counts, risk score, methods, limitations, and computed insights).

Insights are deterministic summaries of those calculations. Decade counts use method-specific detections and may include multiple methods for one observation; the dashboard also provides unique-observation counts. Comparisons over time may reflect changes in the set of reporting cities.

## Limitations and interpretation

Historical records refer only to this dataset snapshot, not all-time records. Sparse early coverage, source changes, uncertainty, autocorrelation, and shifts in city coverage can affect baselines and comparisons. The engine does not homogenize records, adjust for urban heat islands, model impacts, or establish attribution. Verify flagged records against source metadata and independent quality-controlled datasets before making scientific, operational, or policy decisions.
