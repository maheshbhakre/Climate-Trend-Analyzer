# Canonical climate schema

The processed dataset uses one field name and meaning throughout preprocessing, analysis, reports, and the dashboard. The `°C` names follow the project’s canonical convention; unit documentation from the source publisher is not present in this repository and should be verified before formal publication.

| Field | Type | Required | Source / derivation | Definition and format |
| --- | --- | --- | --- | --- |
| `date` | datetime | Yes | `dt` | Observation date, parsed as a date/time value. Malformed dates are reported and excluded from clean output. |
| `avg_temp_c` | float | Yes | `AverageTemperature` | Source average-temperature observation, represented as °C by canonical convention. Never filled or fabricated. |
| `uncertainty_c` | float | Yes | `AverageTemperatureUncertainty` | Source temperature-uncertainty observation, represented as °C by convention. The exact source definition is not available locally. |
| `city` | string | Yes | `City` | Trimmed source city label. No external geographic name reconciliation is applied. |
| `country` | string | Yes | `Country` | Trimmed source country label. No external geographic name reconciliation is applied. |
| `latitude` | float | Yes | `Latitude` | Signed decimal degrees. North is positive and south is negative. Valid range: -90 to 90. |
| `longitude` | float | Yes | `Longitude` | Signed decimal degrees. East is positive and west is negative. Valid range: -180 to 180. |
| `year` | integer | Yes | Derived from `date` | Calendar year as a four-digit integer. |
| `month` | integer | Yes | Derived from `date` | Calendar month from 1 to 12. |

## Source schema observed in this repository

`data/raw/climate.csv` contains `dt`, `AverageTemperature`, `AverageTemperatureUncertainty`, `City`, `Country`, `Latitude`, and `Longitude`. Coordinate values are text such as `5.63N` and `3.23W` and are converted to signed numeric degrees.

Repository-level source checks found 239,177 source rows, date values from 1743-11-01 through 2013-09-01, 49 distinct country labels, 100 distinct city labels, and 11,002 missing temperature and uncertainty rows. No malformed dates, exact duplicate rows, or repeated `(dt, City, Country)` observation keys were found in this snapshot. These statistics describe the file inspected and may change if it is replaced.

## Exclusion and validation policy

- Missing required values, invalid dates, invalid coordinates, non-numeric values, negative uncertainty, and temperatures outside the broad -90 °C to 60 °C screening interval are excluded from the canonical clean output.
- Missingness and invalidity are counted in reports based on the raw input; the clean file is not a substitute for the audit trail.
- The screening interval is a broad guardrail and not proof that a value is scientifically correct.
- `year` and `month` are deterministic calendar features, not climate measurements.
- No rainfall, emissions, sea-level, renewable-energy, forest, or extreme-event fields are derived from temperature.
