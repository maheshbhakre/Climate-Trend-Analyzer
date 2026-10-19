"""Explainable monthly temperature forecasts for canonical climate observations."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA

from src.data_loader import CANONICAL_COLUMNS

SUPPORTED_HORIZONS = (12, 24, 36, 60)
MODEL_NAMES = ("linear_regression", "arima", "naive_baseline")
MAX_TRAINING_MONTHS = 720
MIN_TRAINING_MONTHS = 48


@dataclass
class FittedForecastModel:
    """Small common wrapper around model-specific fitted state."""

    model_name: str
    history: pd.Series
    fitted: Any = None
    residual_scale: float = 0.0
    design_columns: tuple[str, ...] = ()


def _validate_frame(dataframe: pd.DataFrame) -> None:
    missing = [name for name in CANONICAL_COLUMNS if name not in dataframe]
    if missing:
        raise ValueError("Forecasting requires canonical fields: " + ", ".join(missing))
    if dataframe.empty:
        raise ValueError("Forecasting cannot run on an empty dataset.")


def _month_number(index: pd.DatetimeIndex) -> np.ndarray:
    return index.month.to_numpy()


def _monthly_design(index: pd.DatetimeIndex, start: int) -> pd.DataFrame:
    months = _month_number(index)
    design = pd.DataFrame(
        {"trend_index": np.arange(start, start + len(index), dtype=float)}
    )
    for month in range(2, 13):
        design[f"month_{month}"] = (months == month).astype(float)
    design.insert(0, "const", 1.0)
    return design


def _coerce_series(series: pd.Series | pd.DataFrame) -> pd.Series:
    if isinstance(series, pd.DataFrame):
        if "date" in series and "avg_temp_c" in series:
            values = series.set_index("date")["avg_temp_c"]
        elif "avg_temp_c" in series:
            values = series["avg_temp_c"]
        else:
            raise ValueError("Forecast series must contain 'avg_temp_c'.")
    else:
        values = series.copy()
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError(
            "Forecast series must use a DatetimeIndex of monthly observations."
        )
    values = pd.to_numeric(values, errors="coerce").dropna().sort_index()
    values.index = values.index.to_period("M").to_timestamp()
    values = values.groupby(level=0).mean().sort_index().astype(float)
    if values.empty:
        raise ValueError("No valid monthly temperature observations are available.")
    expected = pd.date_range(values.index[0], values.index[-1], freq="MS")
    if not values.index.equals(expected):
        raise ValueError(
            "Forecast model input must be a consecutive monthly series; prepare it first."
        )
    return values


def prepare_forecast_series(
    dataframe: pd.DataFrame,
    *,
    forecast_type: str = "city",
    city: str | None = None,
    country: str | None = None,
    max_history_months: int = MAX_TRAINING_MONTHS,
) -> pd.DataFrame:
    """Aggregate observed temperatures monthly and retain the latest contiguous run.

    Gaps are not imputed. When the source has gaps, only observations from the
    latest uninterrupted month-to-month segment are used. The default training
    window is the latest 60 years to limit the effect of older measurement and
    coverage regimes while retaining sufficient history for seasonal models.
    """
    _validate_frame(dataframe)
    if forecast_type not in {"global", "country", "city"}:
        raise ValueError("forecast_type must be 'global', 'country', or 'city'.")
    if max_history_months < MIN_TRAINING_MONTHS:
        raise ValueError(f"max_history_months must be at least {MIN_TRAINING_MONTHS}.")
    selected = dataframe.copy()
    if forecast_type == "country":
        if not country:
            raise ValueError("A country is required for a country forecast.")
        selected = selected.loc[selected["country"].eq(country)]
    elif forecast_type == "city":
        if not country or not city:
            raise ValueError("A city and country are required for a city forecast.")
        selected = selected.loc[
            selected["country"].eq(country) & selected["city"].eq(city)
        ]
    if selected.empty:
        location = f"{city}, {country}" if city else country or "selected scope"
        raise ValueError(f"No observations are available for {location}.")
    selected["date"] = pd.to_datetime(selected["date"], errors="coerce")
    selected["avg_temp_c"] = pd.to_numeric(selected["avg_temp_c"], errors="coerce")
    selected["uncertainty_c"] = pd.to_numeric(
        selected["uncertainty_c"], errors="coerce"
    )
    selected = selected.dropna(subset=["date", "avg_temp_c"])
    selected["date"] = selected["date"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        selected.groupby("date", as_index=False)
        .agg(
            avg_temp_c=("avg_temp_c", "mean"),
            uncertainty_c=("uncertainty_c", "mean"),
            observation_count=("avg_temp_c", "size"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )
    ordinals = monthly["date"].dt.year * 12 + monthly["date"].dt.month
    breaks = ordinals.diff().ne(1)
    if len(monthly):
        breaks.iloc[0] = True
    monthly["segment"] = breaks.cumsum()
    latest_segment = monthly["segment"].iloc[-1]
    monthly = monthly.loc[monthly["segment"].eq(latest_segment)].drop(columns="segment")
    monthly = monthly.tail(max_history_months).reset_index(drop=True)
    if len(monthly) < MIN_TRAINING_MONTHS:
        raise ValueError(
            f"Only {len(monthly)} consecutive monthly observations are available; "
            f"at least {MIN_TRAINING_MONTHS} are required."
        )
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month
    return monthly[
        ["date", "avg_temp_c", "uncertainty_c", "observation_count", "year", "month"]
    ]


def train_linear_regression_model(
    series: pd.Series | pd.DataFrame,
) -> FittedForecastModel:
    """Fit a linear trend plus fixed calendar-month effects using OLS."""
    values = _coerce_series(series)
    if len(values) < 24:
        raise ValueError("Linear regression requires at least 24 consecutive months.")
    design = _monthly_design(values.index, 0)
    fitted = sm.OLS(values.to_numpy(), design).fit()
    scale = float(np.sqrt(np.mean(np.square(fitted.resid))))
    return FittedForecastModel(
        "linear_regression", values, fitted, scale, tuple(design.columns)
    )


def train_arima_model(series: pd.Series | pd.DataFrame) -> FittedForecastModel:
    """Fit a seasonal ARIMA(1,1,1)(1,1,0)[12] model to observed monthly means."""
    values = _coerce_series(series)
    if len(values) < MIN_TRAINING_MONTHS:
        raise ValueError(
            f"Seasonal ARIMA requires at least {MIN_TRAINING_MONTHS} consecutive months."
        )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ARIMA(
            values,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 0, 12),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit()
    scale = float(np.sqrt(np.mean(np.square(np.asarray(fitted.resid)[12:]))))
    return FittedForecastModel("arima", values, fitted, scale)


def naive_baseline_model(series: pd.Series | pd.DataFrame) -> FittedForecastModel:
    """Create a seasonal-naive baseline that repeats the last observed 12 months."""
    values = _coerce_series(series)
    if len(values) < 24:
        raise ValueError(
            "Seasonal naive baseline requires at least 24 consecutive months."
        )
    errors = values.iloc[12:].to_numpy() - values.iloc[:-12].to_numpy()
    scale = float(np.std(errors, ddof=1)) if len(errors) > 1 else 0.0
    return FittedForecastModel("naive_baseline", values, residual_scale=scale)


def _fit_model(
    series: pd.Series | pd.DataFrame, model_name: str
) -> FittedForecastModel:
    trainers = {
        "linear_regression": train_linear_regression_model,
        "arima": train_arima_model,
        "naive_baseline": naive_baseline_model,
    }
    if model_name not in trainers:
        raise ValueError(f"model_name must be one of: {', '.join(MODEL_NAMES)}.")
    return trainers[model_name](series)


def _predict_model(model: FittedForecastModel, horizon_months: int) -> pd.DataFrame:
    future_index = pd.date_range(
        model.history.index[-1] + pd.offsets.MonthBegin(1),
        periods=horizon_months,
        freq="MS",
    )
    if model.model_name == "linear_regression":
        design = _monthly_design(future_index, len(model.history))
        prediction = model.fitted.get_prediction(exog=design).summary_frame(alpha=0.05)
        mean = prediction["mean"].to_numpy()
        lower = prediction["obs_ci_lower"].to_numpy()
        upper = prediction["obs_ci_upper"].to_numpy()
    elif model.model_name == "arima":
        prediction = model.fitted.get_forecast(steps=horizon_months)
        interval = prediction.conf_int(alpha=0.05)
        mean = np.asarray(prediction.predicted_mean)
        lower = interval.iloc[:, 0].to_numpy()
        upper = interval.iloc[:, 1].to_numpy()
    else:
        last_year = model.history.iloc[-12:].to_numpy()
        mean = np.resize(last_year, horizon_months)
        widths = (
            1.96
            * model.residual_scale
            * np.sqrt(np.ceil(np.arange(1, horizon_months + 1) / 12))
        )
        lower, upper = mean - widths, mean + widths
    return pd.DataFrame(
        {
            "date": future_index,
            "forecast_avg_temp_c": mean,
            "lower_95_c": np.minimum(lower, mean),
            "upper_95_c": np.maximum(upper, mean),
        }
    )


def generate_forecast(
    dataframe: pd.DataFrame,
    *,
    horizon_months: int = 12,
    forecast_type: str = "city",
    city: str | None = None,
    country: str | None = None,
    model_name: str = "linear_regression",
) -> pd.DataFrame:
    """Forecast a selected global, country, or city series for a supported horizon."""
    if horizon_months not in SUPPORTED_HORIZONS:
        raise ValueError(f"horizon_months must be one of {SUPPORTED_HORIZONS}.")
    series_frame = prepare_forecast_series(
        dataframe, forecast_type=forecast_type, city=city, country=country
    )
    values = series_frame.set_index("date")["avg_temp_c"]
    model = _fit_model(values, model_name)
    forecast = _predict_model(model, horizon_months)
    forecast["forecast_type"] = forecast_type
    forecast["country"] = country if forecast_type != "global" else "Global pooled"
    forecast["city"] = city if forecast_type == "city" else pd.NA
    forecast["model_name"] = model_name
    forecast["horizon_months"] = horizon_months
    forecast["training_start_date"] = values.index.min()
    forecast["training_end_date"] = values.index.max()
    forecast["mean_reported_uncertainty_c"] = series_frame["uncertainty_c"].mean()
    return forecast


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = predicted - actual
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    nonzero = np.abs(actual) > 1e-8
    mape = (
        float(np.mean(np.abs(errors[nonzero] / actual[nonzero])) * 100)
        if nonzero.any()
        else float("nan")
    )
    total = float(np.sum(np.square(actual - np.mean(actual))))
    r_squared = (
        float(1 - np.sum(np.square(errors)) / total) if total > 0 else float("nan")
    )
    return {"mae_c": mae, "rmse_c": rmse, "mape_pct": mape, "r_squared": r_squared}


def evaluate_forecast(
    series: pd.Series | pd.DataFrame,
    model_name: str = "linear_regression",
    test_months: int = 12,
) -> dict[str, float | int | str]:
    """Evaluate a one-step-ahead model over a chronological holdout window."""
    values = _coerce_series(series)
    if test_months < 1 or len(values) <= test_months:
        raise ValueError("The series must have more observations than test_months.")
    train, actual = values.iloc[:-test_months], values.iloc[-test_months:]
    if model_name == "arima" and len(train) < MIN_TRAINING_MONTHS:
        raise ValueError(
            f"ARIMA evaluation needs {MIN_TRAINING_MONTHS} training months before holdout."
        )
    model = _fit_model(train, model_name)
    predicted = _predict_model(model, test_months)["forecast_avg_temp_c"].to_numpy()
    return {
        "model_name": model_name,
        "test_months": test_months,
        "test_start_date": actual.index.min(),
        "test_end_date": actual.index.max(),
        **_regression_metrics(actual.to_numpy(), predicted),
    }


def forecast_risk_score(
    forecast: pd.DataFrame,
    historical_series: pd.Series | pd.DataFrame,
) -> dict[str, float | str]:
    """Score projected departures from local recent same-month historical ranges.

    This temperature-pattern screening score is not a hazard probability, impact
    estimate, or climate-risk loss model.
    """
    values = _coerce_series(historical_series)
    required = {"date", "forecast_avg_temp_c"}
    if not required.issubset(forecast.columns):
        raise ValueError("forecast must contain date and forecast_avg_temp_c columns.")
    recent = values.loc[values.index >= values.index.max() - pd.DateOffset(years=30)]
    baseline = pd.DataFrame(
        {"temperature": recent.to_numpy(), "month": recent.index.month}
    )
    ranges = baseline.groupby("month")["temperature"].quantile([0.05, 0.95]).unstack()
    future = forecast[["date", "forecast_avg_temp_c"]].copy()
    future["month"] = pd.to_datetime(future["date"]).dt.month
    future["lower_ref_c"] = future["month"].map(ranges[0.05])
    future["upper_ref_c"] = future["month"].map(ranges[0.95])
    future["departure_c"] = np.where(
        future["forecast_avg_temp_c"] > future["upper_ref_c"],
        future["forecast_avg_temp_c"] - future["upper_ref_c"],
        np.where(
            future["forecast_avg_temp_c"] < future["lower_ref_c"],
            future["forecast_avg_temp_c"] - future["lower_ref_c"],
            0.0,
        ),
    )
    flagged = future["departure_c"].ne(0)
    frequency = float(flagged.mean() * 100)
    magnitude = (
        float(
            np.clip(future.loc[flagged, "departure_c"].abs().mean() / 10 * 100, 0, 100)
        )
        if flagged.any()
        else 0.0
    )
    longest = 0
    current = 0
    for is_flagged in flagged:
        current = current + 1 if is_flagged else 0
        longest = max(longest, current)
    persistence = float(min(100.0, longest / 12 * 100))
    score = 0.40 * frequency + 0.35 * magnitude + 0.25 * persistence
    level = (
        "Low"
        if score < 25
        else "Medium"
        if score < 50
        else "High"
        if score < 75
        else "Critical"
    )
    return {
        "frequency_score": frequency,
        "magnitude_score": magnitude,
        "persistence_score": persistence,
        "future_climate_risk_score": score,
        "risk_level": level,
        "forecast_months_outside_recent_5_95_percent_range": int(flagged.sum()),
    }


def generate_forecast_insights(
    forecast: pd.DataFrame,
    metrics: pd.DataFrame,
    risk: dict[str, float | str],
) -> list[str]:
    """Create summary statements directly from model forecasts, metrics, and risk."""
    insights: list[str] = []
    if not forecast.empty:
        mean_future = float(forecast["forecast_avg_temp_c"].mean())
        first = float(forecast["forecast_avg_temp_c"].iloc[0])
        last = float(forecast["forecast_avg_temp_c"].iloc[-1])
        label = (
            forecast["city"].dropna().iloc[0]
            if forecast["city"].notna().any()
            else forecast["country"].iloc[0]
        )
        insights.append(
            f"The selected model projects a mean of {mean_future:.2f} °C over the forecast horizon for {label}."
        )
        insights.append(
            f"The forecast changes from {first:.2f} °C in its first month to {last:.2f} °C in its final month."
        )
    if not metrics.empty and metrics["rmse_c"].notna().any():
        best = metrics.loc[metrics["rmse_c"].idxmin()]
        insights.append(
            f"{best['model_name']} had the lowest held-out RMSE ({best['rmse_c']:.3f} °C over {int(best['test_months'])} months)."
        )
    insights.append(
        f"The future temperature-pattern risk score is {float(risk['future_climate_risk_score']):.1f}/100 ({risk['risk_level']}); this is a screening score, not a calibrated hazard probability."
    )
    return insights


def generate_forecast_reports(
    dataframe: pd.DataFrame,
    output_dir: str | Path,
    *,
    horizon_months: int = 12,
    evaluation_months: int = 12,
) -> dict[str, Path]:
    """Backtest available models and write global, country, and city forecasts."""
    _validate_frame(dataframe)
    if horizon_months not in SUPPORTED_HORIZONS:
        raise ValueError(f"horizon_months must be one of {SUPPORTED_HORIZONS}.")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    locations: list[tuple[str, str | None, str | None]] = [("global", None, None)]
    locations.extend(
        ("country", None, country)
        for country in sorted(dataframe["country"].dropna().unique())
    )
    locations.extend(
        ("city", city, country)
        for country, city in sorted(
            dataframe[["country", "city"]]
            .dropna()
            .drop_duplicates()
            .itertuples(index=False, name=None)
        )
    )
    all_forecasts: list[pd.DataFrame] = []
    all_metrics: list[dict[str, Any]] = []
    report_rows: dict[str, list[dict[str, Any]]] = {"country": [], "city": []}
    summary_insights: list[str] = []

    for forecast_type, city, country in locations:
        try:
            prepared = prepare_forecast_series(
                dataframe,
                forecast_type=forecast_type,
                city=city,
                country=country,
            )
            series = prepared.set_index("date")["avg_temp_c"]
            validation_rows = []
            for model_name in MODEL_NAMES:
                try:
                    result = evaluate_forecast(series, model_name, evaluation_months)
                    result.update(
                        {
                            "forecast_type": forecast_type,
                            "country": country or "Global pooled",
                            "city": city,
                        }
                    )
                    all_metrics.append(result)
                    validation_rows.append(result)
                except (ValueError, np.linalg.LinAlgError, RuntimeError) as exc:
                    all_metrics.append(
                        {
                            "forecast_type": forecast_type,
                            "country": country or "Global pooled",
                            "city": city,
                            "model_name": model_name,
                            "test_months": evaluation_months,
                            "mae_c": np.nan,
                            "rmse_c": np.nan,
                            "mape_pct": np.nan,
                            "r_squared": np.nan,
                            "model_status": str(exc),
                        }
                    )
            eligible = [
                row for row in validation_rows if np.isfinite(row.get("rmse_c", np.nan))
            ]
            if not eligible:
                continue
            best_name = min(eligible, key=lambda row: row["rmse_c"])["model_name"]
            predicted = generate_forecast(
                dataframe,
                horizon_months=horizon_months,
                forecast_type=forecast_type,
                city=city,
                country=country,
                model_name=best_name,
            )
            predicted["validation_rmse_c"] = min(row["rmse_c"] for row in eligible)
            predicted["validation_model_name"] = best_name
            risk = forecast_risk_score(predicted, series)
            predicted["future_climate_risk_score"] = risk["future_climate_risk_score"]
            predicted["risk_level"] = risk["risk_level"]
            all_forecasts.append(predicted)
            if forecast_type != "global":
                row = {
                    "country": country,
                    "city": city,
                    "forecast_type": forecast_type,
                    "selected_model": best_name,
                    "horizon_months": horizon_months,
                    "forecast_mean_c": float(predicted["forecast_avg_temp_c"].mean()),
                    "forecast_end_c": float(predicted["forecast_avg_temp_c"].iloc[-1]),
                    "forecast_lower_mean_c": float(predicted["lower_95_c"].mean()),
                    "forecast_upper_mean_c": float(predicted["upper_95_c"].mean()),
                    "validation_rmse_c": float(min(row["rmse_c"] for row in eligible)),
                    **risk,
                }
                report_rows[forecast_type].append(row)
        except (ValueError, KeyError) as exc:
            all_metrics.append(
                {
                    "forecast_type": forecast_type,
                    "country": country or "Global pooled",
                    "city": city,
                    "model_name": "all",
                    "test_months": evaluation_months,
                    "mae_c": np.nan,
                    "rmse_c": np.nan,
                    "mape_pct": np.nan,
                    "r_squared": np.nan,
                    "model_status": str(exc),
                }
            )

    forecasts = (
        pd.concat(all_forecasts, ignore_index=True) if all_forecasts else pd.DataFrame()
    )
    metrics = pd.DataFrame(all_metrics)
    city_report = pd.DataFrame(report_rows["city"])
    country_report = pd.DataFrame(report_rows["country"])
    reports = {
        "forecasts": forecasts,
        "forecast_metrics": metrics,
        "city_forecast_report": city_report,
        "country_forecast_report": country_report,
    }
    paths: dict[str, Path] = {}
    for name, report in reports.items():
        path = output / f"{name}.csv"
        report.to_csv(path, index=False)
        paths[name] = path
    if not forecasts.empty:
        global_forecast = forecasts.loc[forecasts["forecast_type"].eq("global")]
        global_metrics = metrics.loc[metrics["forecast_type"].eq("global")]
        global_risk = forecast_risk_score(
            global_forecast,
            prepare_forecast_series(dataframe, forecast_type="global").set_index(
                "date"
            )["avg_temp_c"],
        )
        summary_insights = generate_forecast_insights(
            global_forecast, global_metrics, global_risk
        )
        global_row = (
            global_metrics.loc[global_metrics["rmse_c"].idxmin()]
            if global_metrics["rmse_c"].notna().any()
            else None
        )
    else:
        global_risk = {}
        global_row = None
    summary = {
        "forecast_origin": str(dataframe["date"].max()),
        "forecast_horizon_months": horizon_months,
        "evaluation_holdout_months": evaluation_months,
        "training_window_max_months": MAX_TRAINING_MONTHS,
        "location_forecast_count": int(
            len(city_report) + len(country_report) + (not forecasts.empty)
        ),
        "global_best_model": None
        if global_row is None
        else str(global_row["model_name"]),
        "global_validation_metrics": None
        if global_row is None
        else {
            name: float(global_row[name]) if np.isfinite(global_row[name]) else None
            for name in ("mae_c", "rmse_c", "mape_pct", "r_squared")
        },
        "global_future_risk": global_risk,
        "insights": summary_insights,
        "limitations": [
            "Forecast origin is the dataset's last observed month; historical data do not extend to the present.",
            "Only the latest contiguous observed segment is modeled; gaps are not interpolated.",
            "Global and country averages are unweighted across available city rows and may change with location coverage.",
            "Confidence intervals are model-based prediction intervals and do not include an interpretation of the source uncertainty field because its definition and covariance are not available here.",
            "Risk scores screen forecast temperatures against recent local historical monthly ranges; they are not hazard probabilities or impact estimates.",
        ],
    }
    summary_path = output / "forecast_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    paths["forecast_summary"] = summary_path
    return paths
