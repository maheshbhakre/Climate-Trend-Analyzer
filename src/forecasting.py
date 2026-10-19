"""Location-specific monthly forecasting helper (experimental, not attribution)."""

from __future__ import annotations

import pandas as pd
from statsmodels.tsa.arima.model import ARIMA


def forecast_temperature(
    dataframe: pd.DataFrame,
    *,
    city: str,
    country: str,
    steps: int = 24,
) -> pd.DataFrame:
    """Fit ARIMA to a selected location's monthly mean series.

    No imputation is performed: gaps or fewer than 36 monthly observations are
    rejected. This helper remains experimental and should be backtested before
    use as a decision-support forecast.
    """
    required = {"date", "avg_temp_c", "city", "country"}
    missing = sorted(required.difference(dataframe.columns))
    if missing:
        raise ValueError("Forecasting requires canonical fields: " + ", ".join(missing))
    if steps < 1:
        raise ValueError("Forecast steps must be a positive number of months.")
    selected = dataframe.loc[
        dataframe["city"].eq(city) & dataframe["country"].eq(country),
        ["date", "avg_temp_c"],
    ].copy()
    if selected.empty:
        raise ValueError(f"No observations are available for {city}, {country}.")
    selected["date"] = pd.to_datetime(selected["date"], errors="coerce")
    monthly = (
        selected.dropna(subset=["date", "avg_temp_c"])
        .set_index("date")["avg_temp_c"]
        .resample("MS")
        .mean()
        .dropna()
        .sort_index()
    )
    full_index = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    if len(monthly) < 36 or not monthly.index.equals(full_index):
        raise ValueError(
            "Forecasting requires at least 36 consecutive monthly observations; "
            "the selected city series is shorter or has gaps."
        )
    fitted = ARIMA(monthly, order=(2, 1, 2)).fit()
    prediction = fitted.get_forecast(steps=steps)
    interval = prediction.conf_int()
    return pd.DataFrame(
        {
            "date": prediction.predicted_mean.index,
            "forecast_avg_temp_c": prediction.predicted_mean.to_numpy(),
            "lower_95_c": interval.iloc[:, 0].to_numpy(),
            "upper_95_c": interval.iloc[:, 1].to_numpy(),
            "city": city,
            "country": country,
        }
    )
