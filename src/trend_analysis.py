"""Descriptive time-series and geographic analytics for canonical climate data."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.data_loader import CANONICAL_COLUMNS

ANALYTICS_REPORT_NAMES = (
    "country_trend_report",
    "city_trend_report",
    "seasonality_report",
    "decade_trend_report",
    "statistical_trend_report",
    "uncertainty_report",
)


def _validate_frame(dataframe: pd.DataFrame) -> None:
    missing = [column for column in CANONICAL_COLUMNS if column not in dataframe]
    if missing:
        raise ValueError(
            "Trend analysis requires canonical fields: " + ", ".join(missing)
        )
    if dataframe.empty:
        raise ValueError("Trend analysis cannot run on an empty dataset.")
    if dataframe["date"].isna().any() or dataframe["avg_temp_c"].isna().any():
        raise ValueError(
            "Trend analysis requires valid dates and temperatures in every row."
        )


def _group_columns(group_by: str | Sequence[str] | None) -> list[str]:
    if group_by is None:
        return []
    return [group_by] if isinstance(group_by, str) else list(group_by)


def annual_temperature_trends(
    dataframe: pd.DataFrame,
    group_by: str | Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return annual unweighted observation means, uncertainty, and row counts."""
    _validate_frame(dataframe)
    groups = _group_columns(group_by)
    keys = [*groups, "year"]
    result = (
        dataframe.groupby(keys, dropna=False, as_index=False)
        .agg(
            average_temperature_c=("avg_temp_c", "mean"),
            average_uncertainty_c=("uncertainty_c", "mean"),
            observation_count=("avg_temp_c", "size"),
        )
        .sort_values(keys)
        .reset_index(drop=True)
    )
    return result


def monthly_temperature_trends(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return monthly means over time, aggregated across available city rows."""
    _validate_frame(dataframe)
    monthly = dataframe.assign(
        month_start=dataframe["date"].dt.to_period("M").dt.to_timestamp()
    )
    result = (
        monthly.groupby("month_start", as_index=False)
        .agg(
            average_temperature_c=("avg_temp_c", "mean"),
            average_uncertainty_c=("uncertainty_c", "mean"),
            observation_count=("avg_temp_c", "size"),
        )
        .rename(columns={"month_start": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    result["year"] = result["date"].dt.year
    result["month"] = result["date"].dt.month
    return result[
        [
            "date",
            "year",
            "month",
            "average_temperature_c",
            "average_uncertainty_c",
            "observation_count",
        ]
    ]


def decadal_temperature_trends(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarize each observed calendar decade and its change from prior observed decade."""
    _validate_frame(dataframe)
    with_decade = dataframe.assign(decade=(dataframe["year"] // 10) * 10)
    result = (
        with_decade.groupby("decade", as_index=False)
        .agg(
            average_temperature_c=("avg_temp_c", "mean"),
            average_uncertainty_c=("uncertainty_c", "mean"),
            observation_count=("avg_temp_c", "size"),
        )
        .sort_values("decade")
        .reset_index(drop=True)
    )
    result["previous_observed_decade"] = result["decade"].shift(1).astype("Int64")
    result["decade_to_decade_change_c"] = result["average_temperature_c"].diff()
    highest = int(result.loc[result["average_temperature_c"].idxmax(), "decade"])
    lowest = int(result.loc[result["average_temperature_c"].idxmin(), "decade"])
    result["highest_temperature_decade"] = highest
    result["lowest_temperature_decade"] = lowest
    return result


def rolling_temperature_average(
    dataframe: pd.DataFrame,
    window: int = 12,
) -> pd.DataFrame:
    """Add a trailing window mean over monthly pooled observations.

    A 12-month window means 12 observed calendar-month aggregates. Missing
    calendar months are not interpolated and therefore do not add fabricated data.
    """
    if window < 1:
        raise ValueError("Rolling-average window must be a positive number of months.")
    monthly = monthly_temperature_trends(dataframe)
    monthly = monthly.set_index("date").asfreq("MS").reset_index()
    monthly["year"] = monthly["date"].dt.year
    monthly["month"] = monthly["date"].dt.month
    monthly["rolling_average_c"] = (
        monthly["average_temperature_c"]
        .rolling(window=window, min_periods=window)
        .mean()
    )
    monthly["rolling_window_months"] = window
    return monthly


def temperature_change_over_time(
    dataframe: pd.DataFrame,
    group_by: str | Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return annual mean changes from each series' first observed annual mean."""
    annual = annual_temperature_trends(dataframe, group_by=group_by)
    groups = _group_columns(group_by)
    if groups:
        annual["baseline_temperature_c"] = annual.groupby(groups, dropna=False)[
            "average_temperature_c"
        ].transform("first")
    else:
        annual["baseline_temperature_c"] = annual["average_temperature_c"].iloc[0]
    annual["temperature_change_c"] = (
        annual["average_temperature_c"] - annual["baseline_temperature_c"]
    )
    return annual


def _series_trend(group: pd.DataFrame) -> dict[str, float | int]:
    annual = (
        group.groupby("year", as_index=False)
        .agg(average_temperature_c=("avg_temp_c", "mean"))
        .sort_values("year")
    )
    if len(annual) < 2:
        return {
            "temperature_change_c": float("nan"),
            "warming_rate_c_per_decade": float("nan"),
            "first_observed_year": int(annual["year"].iloc[0]) if len(annual) else 0,
            "last_observed_year": int(annual["year"].iloc[-1]) if len(annual) else 0,
        }
    slope = float(
        np.polyfit(annual["year"].astype(float), annual["average_temperature_c"], 1)[0]
    )
    return {
        "temperature_change_c": float(
            annual["average_temperature_c"].iloc[-1]
            - annual["average_temperature_c"].iloc[0]
        ),
        "warming_rate_c_per_decade": slope * 10,
        "first_observed_year": int(annual["year"].iloc[0]),
        "last_observed_year": int(annual["year"].iloc[-1]),
    }


def country_trend_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Country averages and descriptive annual warming rates, ranked by warming rate."""
    _validate_frame(dataframe)
    rows = []
    for country, group in dataframe.groupby("country", dropna=False):
        rows.append(
            {
                "country": country,
                "average_temperature_c": float(group["avg_temp_c"].mean()),
                "average_uncertainty_c": float(group["uncertainty_c"].mean()),
                "observation_count": len(group),
                **_series_trend(group),
            }
        )
    result = pd.DataFrame(rows)
    result["country_ranking"] = (
        result["warming_rate_c_per_decade"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    return result.sort_values(
        ["country_ranking", "country"], na_position="last"
    ).reset_index(drop=True)


def city_trend_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """City-country averages and warming trends, ranked by average temperature."""
    _validate_frame(dataframe)
    rows = []
    for (country, city), group in dataframe.groupby(["country", "city"], dropna=False):
        trend = _series_trend(group)
        rows.append(
            {
                "country": country,
                "city": city,
                "average_temperature_c": float(group["avg_temp_c"].mean()),
                "average_uncertainty_c": float(group["uncertainty_c"].mean()),
                "observation_count": len(group),
                "warming_trend_c_per_decade": trend["warming_rate_c_per_decade"],
                "temperature_change_c": trend["temperature_change_c"],
                "first_observed_year": trend["first_observed_year"],
                "last_observed_year": trend["last_observed_year"],
            }
        )
    result = pd.DataFrame(rows)
    result["city_ranking"] = (
        result["average_temperature_c"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    result["warming_rank"] = (
        result["warming_trend_c_per_decade"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    return result.sort_values(
        ["city_ranking", "country", "city"], na_position="last"
    ).reset_index(drop=True)


def seasonality_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Report pooled monthly means and hemisphere-aware seasonal profiles.

    Seasonal labels use meteorological seasons, reversed in the Southern
    Hemisphere. Equatorial observations are retained in pooled monthly means
    and are not assigned a four-season label.
    """
    _validate_frame(dataframe)
    source = dataframe.copy()
    monthly = source.groupby("month", as_index=False).agg(
        average_temperature_c=("avg_temp_c", "mean"),
        average_uncertainty_c=("uncertainty_c", "mean"),
        observation_count=("avg_temp_c", "size"),
    )
    monthly["report_section"] = "monthly_average"
    monthly["month_name"] = monthly["month"].map(
        lambda value: pd.Timestamp(2000, int(value), 1).strftime("%B")
    )
    monthly["hemisphere"] = "All locations (pooled)"
    monthly["season"] = pd.NA

    source["hemisphere"] = np.select(
        [source["latitude"] > 0, source["latitude"] < 0],
        ["Northern", "Southern"],
        default="Equatorial",
    )
    north = {
        12: "Winter",
        1: "Winter",
        2: "Winter",
        3: "Spring",
        4: "Spring",
        5: "Spring",
        6: "Summer",
        7: "Summer",
        8: "Summer",
        9: "Autumn",
        10: "Autumn",
        11: "Autumn",
    }
    south = {
        12: "Summer",
        1: "Summer",
        2: "Summer",
        3: "Autumn",
        4: "Autumn",
        5: "Autumn",
        6: "Winter",
        7: "Winter",
        8: "Winter",
        9: "Spring",
        10: "Spring",
        11: "Spring",
    }
    source["season"] = pd.NA
    northern = source["hemisphere"].eq("Northern")
    southern = source["hemisphere"].eq("Southern")
    source.loc[northern, "season"] = source.loc[northern, "month"].map(north)
    source.loc[southern, "season"] = source.loc[southern, "month"].map(south)
    seasonal = (
        source.dropna(subset=["season"])
        .groupby(["hemisphere", "season"], as_index=False)
        .agg(
            average_temperature_c=("avg_temp_c", "mean"),
            average_uncertainty_c=("uncertainty_c", "mean"),
            observation_count=("avg_temp_c", "size"),
        )
    )
    seasonal["report_section"] = "seasonal_profile"
    seasonal["month"] = pd.NA
    seasonal["month_name"] = pd.NA

    warmest = monthly.loc[monthly["average_temperature_c"].idxmax()]
    coldest = monthly.loc[monthly["average_temperature_c"].idxmin()]
    rows = (
        monthly.to_dict("records")
        + seasonal.to_dict("records")
        + [
            {
                "report_section": "pooled_monthly_summary",
                "month": pd.NA,
                "month_name": pd.NA,
                "hemisphere": "All locations (pooled)",
                "season": pd.NA,
                "average_temperature_c": pd.NA,
                "average_uncertainty_c": pd.NA,
                "observation_count": len(source),
                "warmest_month": warmest["month_name"],
                "coldest_month": coldest["month_name"],
                "temperature_spread_c": float(
                    warmest["average_temperature_c"] - coldest["average_temperature_c"]
                ),
            }
        ]
    )
    columns = [
        "report_section",
        "month",
        "month_name",
        "hemisphere",
        "season",
        "average_temperature_c",
        "average_uncertainty_c",
        "observation_count",
        "warmest_month",
        "coldest_month",
        "temperature_spread_c",
    ]
    return pd.DataFrame(rows).reindex(columns=columns)


def statistical_trend_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Fit OLS to annual pooled means and report slope CI, R², and correlation."""
    annual = annual_temperature_trends(dataframe)
    if len(annual) < 2:
        raise ValueError(
            "At least two observed years are required for statistical trend analysis."
        )
    x = annual["year"].astype(float)
    y = annual["average_temperature_c"].astype(float)
    model = sm.OLS(y, sm.add_constant(x)).fit()
    slope = float(model.params.iloc[1])
    if model.df_resid > 0:
        ci_low, ci_high = (float(value) for value in model.conf_int().iloc[1].tolist())
    else:
        ci_low = ci_high = float("nan")
    correlation = (
        float(x.corr(y)) if x.nunique() > 1 and y.nunique() > 1 else float("nan")
    )
    if len(annual) > 3 and np.isfinite(correlation):
        z_value = np.arctanh(np.clip(correlation, -0.999999, 0.999999))
        z_margin = 1.96 / np.sqrt(len(annual) - 3)
        corr_low, corr_high = (
            float(np.tanh(z_value - z_margin)),
            float(np.tanh(z_value + z_margin)),
        )
    else:
        corr_low = corr_high = float("nan")
    return pd.DataFrame(
        [
            {
                "annual_points": len(annual),
                "first_year": int(annual["year"].min()),
                "last_year": int(annual["year"].max()),
                "first_year_average_c": float(y.iloc[0]),
                "last_year_average_c": float(y.iloc[-1]),
                "temperature_change_c": float(y.iloc[-1] - y.iloc[0]),
                "trend_slope_c_per_year": slope,
                "trend_slope_c_per_decade": slope * 10,
                "slope_ci95_lower_c_per_year": ci_low,
                "slope_ci95_upper_c_per_year": ci_high,
                "r_squared": float(model.rsquared),
                "year_temperature_correlation": correlation,
                "correlation_ci95_lower": corr_low,
                "correlation_ci95_upper": corr_high,
                "p_value_slope": float(model.pvalues.iloc[1]),
                "interpretation": "Descriptive OLS on unweighted annual means; not causal attribution.",
            }
        ]
    )


def uncertainty_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarize reported uncertainty and a clearly labeled range-relative score."""
    _validate_frame(dataframe)
    temperature_range = float(
        dataframe["avg_temp_c"].max() - dataframe["avg_temp_c"].min()
    )

    def row(level: str, geography: str, group: pd.DataFrame) -> dict[str, object]:
        mean_uncertainty = float(group["uncertainty_c"].mean())
        relative_uncertainty = (
            mean_uncertainty / temperature_range
            if temperature_range > 0
            else float("nan")
        )
        score = (
            float(np.clip(100 * (1 - relative_uncertainty), 0, 100))
            if np.isfinite(relative_uncertainty)
            else float("nan")
        )
        return {
            "geography_level": level,
            "geography": geography,
            "average_uncertainty_c": mean_uncertainty,
            "observation_count": len(group),
            "temperature_range_reference_c": temperature_range,
            "uncertainty_reliability_score_0_100": score,
            "score_note": "Range-relative uncertainty heuristic; not a calibrated probability or full data-quality score.",
        }

    rows = [row("global", "All locations pooled", dataframe)]
    rows.extend(
        row("country", str(country), group)
        for country, group in dataframe.groupby("country")
    )
    rows.extend(
        row("city", f"{city}, {country}", group)
        for (country, city), group in dataframe.groupby(["country", "city"])
    )
    return pd.DataFrame(rows)


def generate_insights(
    dataframe: pd.DataFrame,
    countries: pd.DataFrame | None = None,
    cities: pd.DataFrame | None = None,
    decades: pd.DataFrame | None = None,
) -> list[str]:
    """Build concise factual insights from the same grouped metrics as the reports."""
    _validate_frame(dataframe)
    annual = annual_temperature_trends(dataframe)
    insights = []
    if len(annual) >= 2:
        first = annual.iloc[0]
        last = annual.iloc[-1]
        direction = (
            "increased"
            if last["average_temperature_c"] >= first["average_temperature_c"]
            else "decreased"
        )
        insights.append(
            f"The pooled annual mean {direction} from {first['average_temperature_c']:.2f} °C "
            f"in {int(first['year'])} to {last['average_temperature_c']:.2f} °C in {int(last['year'])} "
            f"({last['average_temperature_c'] - first['average_temperature_c']:+.2f} °C)."
        )
    countries = countries if countries is not None else country_trend_report(dataframe)
    eligible_countries = countries.dropna(subset=["warming_rate_c_per_decade"])
    if not eligible_countries.empty:
        country = eligible_countries.sort_values(
            "warming_rate_c_per_decade", ascending=False
        ).iloc[0]
        insights.append(
            f"The strongest country warming-rate estimate is {country['country']} "
            f"({country['warming_rate_c_per_decade']:+.3f} °C per decade, descriptive)."
        )
    cities = cities if cities is not None else city_trend_report(dataframe)
    if not cities.empty:
        city = cities.sort_values("average_temperature_c", ascending=False).iloc[0]
        insights.append(
            f"The highest city-country average is {city['city']}, {city['country']} "
            f"({city['average_temperature_c']:.2f} °C across {int(city['observation_count']):,} observations)."
        )
    decades = decades if decades is not None else decadal_temperature_trends(dataframe)
    changes = decades.dropna(subset=["decade_to_decade_change_c"])
    if not changes.empty:
        largest = changes.loc[changes["decade_to_decade_change_c"].idxmax()]
        insights.append(
            f"The largest increase between adjacent observed decades was {largest['decade_to_decade_change_c']:+.2f} °C "
            f"from {int(largest['previous_observed_decade'])}s to {int(largest['decade'])}s."
        )
    return insights


def generate_analytics_reports(
    dataframe: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Generate all Phase 2 analytics CSV reports."""
    _validate_frame(dataframe)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    reports = {
        "country_trend_report": country_trend_report(dataframe),
        "city_trend_report": city_trend_report(dataframe),
        "seasonality_report": seasonality_report(dataframe),
        "decade_trend_report": decadal_temperature_trends(dataframe),
        "statistical_trend_report": statistical_trend_report(dataframe),
        "uncertainty_report": uncertainty_report(dataframe),
    }
    paths = {}
    for name, report in reports.items():
        path = output / f"{name}.csv"
        report.to_csv(path, index=False)
        paths[name] = path
    return paths
