import numpy as np
import pandas as pd
import pytest

from src.forecast_engine import (
    SUPPORTED_HORIZONS,
    evaluate_forecast,
    forecast_risk_score,
    generate_forecast,
    naive_baseline_model,
    prepare_forecast_series,
    train_arima_model,
    train_linear_regression_model,
)


@pytest.fixture
def forecast_frame() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2000-01-01", periods=120, freq="MS")
    for country, city, offset in (("A", "North", 0.0), ("B", "South", 8.0)):
        for i, date in enumerate(dates):
            temperature = (
                12 + offset + 5 * np.sin(2 * np.pi * (date.month - 1) / 12) + i * 0.008
            )
            rows.append(
                {
                    "date": date,
                    "avg_temp_c": temperature,
                    "uncertainty_c": 0.25,
                    "city": city,
                    "country": country,
                    "latitude": 40 if country == "A" else -30,
                    "longitude": 10,
                    "year": date.year,
                    "month": date.month,
                }
            )
    return pd.DataFrame(rows)


def test_prepare_forecast_series_location_and_gap_handling(
    forecast_frame: pd.DataFrame,
) -> None:
    north = forecast_frame[
        ~((forecast_frame.city == "North") & (forecast_frame.date == "2004-01-01"))
    ]
    prepared = prepare_forecast_series(
        north, forecast_type="city", city="North", country="A"
    )
    assert len(prepared) == 71
    assert prepared.date.iloc[0] == pd.Timestamp("2004-02-01")
    assert prepared.date.iloc[-1] == pd.Timestamp("2009-12-01")
    month_number = prepared.date.dt.year * 12 + prepared.date.dt.month
    assert month_number.diff().dropna().eq(1).all()


def test_linear_regression_model_generates_valid_confidence_bands(
    forecast_frame: pd.DataFrame,
) -> None:
    series = prepare_forecast_series(
        forecast_frame, forecast_type="city", city="North", country="A"
    ).set_index("date")["avg_temp_c"]
    model = train_linear_regression_model(series)
    assert model.model_name == "linear_regression"
    forecast = generate_forecast(
        forecast_frame,
        horizon_months=24,
        forecast_type="city",
        city="North",
        country="A",
        model_name="linear_regression",
    )
    assert len(forecast) == 24
    assert (forecast.lower_95_c <= forecast.forecast_avg_temp_c).all()
    assert (forecast.forecast_avg_temp_c <= forecast.upper_95_c).all()
    assert forecast.date.iloc[0] == pd.Timestamp("2010-01-01")


def test_seasonal_arima_and_naive_models_fit(forecast_frame: pd.DataFrame) -> None:
    series = prepare_forecast_series(
        forecast_frame, forecast_type="city", city="North", country="A"
    ).set_index("date")["avg_temp_c"]
    arima = train_arima_model(series)
    naive = naive_baseline_model(series)
    assert arima.model_name == "arima"
    assert naive.model_name == "naive_baseline"
    for name in ("arima", "naive_baseline"):
        result = generate_forecast(
            forecast_frame,
            horizon_months=12,
            forecast_type="city",
            city="North",
            country="A",
            model_name=name,
        )
        assert len(result) == 12
        assert np.isfinite(result.forecast_avg_temp_c).all()
        assert (result.lower_95_c <= result.upper_95_c).all()


def test_model_evaluation_returns_requested_metrics(
    forecast_frame: pd.DataFrame,
) -> None:
    series = prepare_forecast_series(forecast_frame, forecast_type="global").set_index(
        "date"
    )["avg_temp_c"]
    result = evaluate_forecast(series, "linear_regression", test_months=12)
    assert result["test_months"] == 12
    for metric in ("mae_c", "rmse_c", "mape_pct", "r_squared"):
        assert np.isfinite(result[metric])
    assert result["mae_c"] >= 0 and result["rmse_c"] >= 0


def test_forecast_risk_score_uses_future_departures(
    forecast_frame: pd.DataFrame,
) -> None:
    historical = prepare_forecast_series(
        forecast_frame, forecast_type="city", city="North", country="A"
    ).set_index("date")["avg_temp_c"]
    future_dates = pd.date_range(
        historical.index[-1] + pd.offsets.MonthBegin(1), periods=12, freq="MS"
    )
    forecast = pd.DataFrame({"date": future_dates, "forecast_avg_temp_c": [40.0] * 12})
    score = forecast_risk_score(forecast, historical)
    assert score["forecast_months_outside_recent_5_95_percent_range"] == 12
    assert score["future_climate_risk_score"] > 0
    assert score["risk_level"] in {"Low", "Medium", "High", "Critical"}


def test_forecast_horizons_are_restricted(forecast_frame: pd.DataFrame) -> None:
    assert SUPPORTED_HORIZONS == (12, 24, 36, 60)
    with pytest.raises(ValueError, match="horizon_months"):
        generate_forecast(forecast_frame, horizon_months=18, forecast_type="global")


@pytest.mark.parametrize("horizon", [12, 24, 36, 60])
def test_each_supported_horizon_and_country_scope(
    forecast_frame: pd.DataFrame, horizon: int
) -> None:
    forecast = generate_forecast(
        forecast_frame,
        horizon_months=horizon,
        forecast_type="country",
        country="A",
        model_name="linear_regression",
    )
    assert len(forecast) == horizon
    assert forecast.forecast_type.eq("country").all()
    assert forecast.country.eq("A").all()
