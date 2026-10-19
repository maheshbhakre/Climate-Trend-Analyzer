"""Location-specific anomaly detection using observed monthly temperatures only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data_loader import CANONICAL_COLUMNS

LOCATION = ["country", "city"]
ANOMALY_COLUMNS = [
    "date",
    "country",
    "city",
    "avg_temp_c",
    "expected_temperature_c",
    "deviation_c",
    "anomaly_score",
    "method_used",
    "severity",
    "year",
]
SEVERITY_ORDER = ["NORMAL", "MODERATE", "SEVERE", "EXTREME"]


def _validate(dataframe: pd.DataFrame) -> None:
    missing = [column for column in CANONICAL_COLUMNS if column not in dataframe]
    if missing:
        raise ValueError(
            "Anomaly analysis requires canonical fields: " + ", ".join(missing)
        )
    if dataframe.empty:
        raise ValueError("Anomaly analysis cannot run on an empty dataset.")
    if dataframe[["date", "avg_temp_c", "country", "city", "month"]].isna().any().any():
        raise ValueError(
            "Anomaly analysis requires valid dates, temperatures, and locations."
        )


def _with_location_month_baseline(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Estimate each city's baseline from its observations in the same calendar month."""
    _validate(dataframe)
    result = dataframe.copy()
    keys = [*LOCATION, "month"]
    grouped = result.groupby(keys, observed=True)["avg_temp_c"]
    baseline = grouped.agg(
        expected_temperature_c="mean",
        baseline_std_c="std",
        baseline_count="count",
        baseline_median_c="median",
        q1_c=lambda values: values.quantile(0.25),
        q3_c=lambda values: values.quantile(0.75),
    ).reset_index()
    result = result.merge(baseline, on=keys, how="left", validate="many_to_one")
    result["deviation_c"] = result["avg_temp_c"] - result["expected_temperature_c"]
    result["z_score"] = result["deviation_c"] / result["baseline_std_c"].replace(
        0, np.nan
    )
    iqr = result["q3_c"] - result["q1_c"]
    result["iqr_lower_fence_c"] = result["q1_c"] - 1.5 * iqr
    result["iqr_upper_fence_c"] = result["q3_c"] + 1.5 * iqr
    # Convert IQR distance to a robust standard-score scale (IQR / 1.349).
    result["iqr_score"] = result["deviation_c"].abs() / (iqr / 1.349).replace(0, np.nan)
    result.loc[iqr.eq(0), "iqr_score"] = np.where(
        result.loc[iqr.eq(0), "deviation_c"].eq(0),
        0.0,
        result.loc[iqr.eq(0), "deviation_c"].abs(),
    )
    return result


def calculate_z_scores(
    dataframe: pd.DataFrame,
    group_by: list[str] | tuple[str, ...] = ("country", "city", "month"),
) -> pd.DataFrame:
    """Return observation-level seasonal z-scores and their group mean baseline."""
    _validate(dataframe)
    keys = list(group_by)
    if not keys or any(key not in dataframe for key in keys):
        raise ValueError("z-score grouping fields must exist in the climate data.")
    result = dataframe.copy()
    grouped = result.groupby(keys, observed=True)["avg_temp_c"]
    result["expected_temperature_c"] = grouped.transform("mean")
    std = grouped.transform("std")
    result["deviation_c"] = result["avg_temp_c"] - result["expected_temperature_c"]
    result["z_score"] = result["deviation_c"] / std.replace(0, np.nan)
    result["baseline_count"] = grouped.transform("count")
    return result


def classify_severity(deviation_c: float, anomaly_score: float | None = None) -> str:
    """Classify event magnitude (2/4/6 °C) and standardized extremity."""
    magnitude = abs(float(deviation_c))
    score = (
        abs(float(anomaly_score))
        if anomaly_score is not None and np.isfinite(anomaly_score)
        else 0.0
    )
    if magnitude >= 6 or score >= 4:
        return "EXTREME"
    if magnitude >= 4 or score >= 3:
        return "SEVERE"
    if magnitude >= 2 or score >= 2:
        return "MODERATE"
    return "NORMAL"


def _format_events(frame: pd.DataFrame, method: str, score_col: str) -> pd.DataFrame:
    events = frame.copy()
    events["method_used"] = method
    events["anomaly_score"] = events[score_col].abs()
    events["severity"] = [
        classify_severity(deviation, score)
        for deviation, score in zip(events["deviation_c"], events["anomaly_score"])
    ]
    events["year"] = events["date"].dt.year
    return (
        events.reindex(columns=ANOMALY_COLUMNS)
        .sort_values(["date", "country", "city", "method_used"])
        .reset_index(drop=True)
    )


def _rolling_deviation(dataframe: pd.DataFrame, window: int = 12) -> pd.DataFrame:
    if window < 2:
        raise ValueError("Rolling baseline window must be at least two observations.")
    source = (
        _with_location_month_baseline(dataframe).sort_values([*LOCATION, "date"]).copy()
    )
    source["seasonal_residual_c"] = (
        source["avg_temp_c"] - source["expected_temperature_c"]
    )
    source["prior_residual_mean_c"] = source.groupby(LOCATION, observed=True)[
        "seasonal_residual_c"
    ].transform(
        lambda values: values.shift(1).rolling(window, min_periods=window).mean()
    )
    source["rolling_std_c"] = source.groupby(LOCATION, observed=True)[
        "seasonal_residual_c"
    ].transform(
        lambda values: values.shift(1).rolling(window, min_periods=window).std()
    )
    source["expected_temperature_c"] += source["prior_residual_mean_c"]
    source["deviation_c"] = source["avg_temp_c"] - source["expected_temperature_c"]
    source["rolling_score"] = source["deviation_c"].abs() / source[
        "rolling_std_c"
    ].replace(0, np.nan)
    return source


def detect_temperature_anomalies(
    dataframe: pd.DataFrame,
    z_threshold: float = 2.0,
    rolling_window: int = 12,
    rolling_deviation_threshold_c: float = 2.0,
) -> pd.DataFrame:
    """Detect seasonal Z-score, seasonal IQR, and trailing rolling deviations.

    Z-score and IQR baselines compare a city with its own history in that calendar
    month. The rolling baseline uses only prior observations for the same city.
    Candidate baselines need at least five same-month observations; rolling events
    need the requested full number of previous observations.
    """
    if z_threshold <= 0 or rolling_deviation_threshold_c <= 0:
        raise ValueError("Detection thresholds must be positive.")
    seasonal = _with_location_month_baseline(dataframe)
    enough = seasonal["baseline_count"].ge(5)
    z_events = seasonal.loc[enough & seasonal["z_score"].abs().ge(z_threshold)]

    iqr_events = seasonal.loc[
        enough
        & (
            (seasonal["avg_temp_c"] < seasonal["iqr_lower_fence_c"])
            | (seasonal["avg_temp_c"] > seasonal["iqr_upper_fence_c"])
        )
    ].copy()
    iqr_events["expected_temperature_c"] = iqr_events["baseline_median_c"]
    iqr_events["deviation_c"] = (
        iqr_events["avg_temp_c"] - iqr_events["baseline_median_c"]
    )
    robust_scale = (iqr_events["q3_c"] - iqr_events["q1_c"]) / 1.349
    iqr_events["iqr_score"] = iqr_events["deviation_c"].abs() / robust_scale.replace(
        0, np.nan
    )
    zero_scale = robust_scale.eq(0)
    iqr_events.loc[zero_scale, "iqr_score"] = np.where(
        iqr_events.loc[zero_scale, "deviation_c"].eq(0),
        0.0,
        iqr_events.loc[zero_scale, "deviation_c"].abs(),
    )

    rolling = _rolling_deviation(dataframe, rolling_window)
    rolling_events = rolling.loc[
        rolling["expected_temperature_c"].notna()
        & rolling["deviation_c"].abs().ge(rolling_deviation_threshold_c)
    ]
    event_frames = [
        _format_events(z_events, "Seasonal Z-Score", "z_score"),
        _format_events(iqr_events, "Seasonal IQR", "iqr_score"),
        _format_events(
            rolling_events, f"Rolling Mean ({rolling_window})", "rolling_score"
        ),
    ]
    events = pd.concat(event_frames, ignore_index=True)
    if events.empty:
        return pd.DataFrame(columns=ANOMALY_COLUMNS)
    return events.sort_values(["date", "country", "city", "method_used"]).reset_index(
        drop=True
    )


def detect_extreme_heat(
    dataframe: pd.DataFrame, threshold_c: float = 2.0
) -> pd.DataFrame:
    """Return detected positive deviations at least ``threshold_c`` above baseline."""
    if threshold_c <= 0:
        raise ValueError("Extreme heat threshold must be positive.")
    events = detect_temperature_anomalies(dataframe)
    return events.loc[events["deviation_c"].ge(threshold_c)].reset_index(drop=True)


def detect_extreme_cold(
    dataframe: pd.DataFrame, threshold_c: float = 2.0
) -> pd.DataFrame:
    """Return detected negative deviations at least ``threshold_c`` below baseline."""
    if threshold_c <= 0:
        raise ValueError("Extreme cold threshold must be positive.")
    events = detect_temperature_anomalies(dataframe)
    return events.loc[events["deviation_c"].le(-threshold_c)].reset_index(drop=True)


def seasonal_anomaly_detection(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return only same-calendar-month location anomalies from Z-score and IQR."""
    events = detect_temperature_anomalies(dataframe)
    return events.loc[
        events["method_used"].isin(["Seasonal Z-Score", "Seasonal IQR"])
    ].reset_index(drop=True)


def _unique_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()
    return (
        events.sort_values("anomaly_score", ascending=False)
        .drop_duplicates(["date", "country", "city"])
        .copy()
    )


def climate_risk_score(
    observation_count: int,
    anomalies: pd.DataFrame,
) -> dict[str, float | str]:
    """Score frequency (40%), magnitude (35%), and consecutive persistence (25%)."""
    unique = _unique_events(anomalies)
    frequency = min(100.0, 100.0 * len(unique) / max(1, observation_count))
    magnitude = (
        float(np.clip(unique["deviation_c"].abs().mean() / 10.0 * 100, 0, 100))
        if not unique.empty
        else 0.0
    )
    persistence = 0.0
    if not unique.empty:
        dates = pd.to_datetime(unique["date"].drop_duplicates().sort_values())
        # A run is consecutive calendar-month event dates; gaps break persistence.
        month_ordinals = dates.dt.year * 12 + dates.dt.month
        runs = month_ordinals.diff().ne(1).cumsum()
        longest = int(month_ordinals.groupby(runs).size().max())
        persistence = min(100.0, longest / 12.0 * 100)
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
        "climate_risk_score": score,
        "risk_level": level,
    }


def _location_report(
    dataframe: pd.DataFrame, events: pd.DataFrame, groups: list[str]
) -> pd.DataFrame:
    _validate(dataframe)
    unique = _unique_events(events)
    bases = (
        dataframe.groupby(groups, dropna=False, observed=True)
        .agg(observation_count=("avg_temp_c", "size"))
        .reset_index()
    )
    if unique.empty:
        summary = pd.DataFrame(
            columns=[
                *groups,
                "anomaly_count",
                "severe_count",
                "extreme_count",
                "average_severity",
                "highest_anomaly_score",
            ]
        )
    else:
        unique["severity_numeric"] = unique["severity"].map(
            dict(zip(SEVERITY_ORDER, range(4)))
        )
        summary = (
            unique.groupby(groups, dropna=False, observed=True)
            .agg(
                anomaly_count=("date", "size"),
                severe_count=(
                    "severity",
                    lambda values: values.isin(["SEVERE", "EXTREME"]).sum(),
                ),
                extreme_count=("severity", lambda values: values.eq("EXTREME").sum()),
                average_severity=("severity_numeric", "mean"),
                highest_anomaly_score=("anomaly_score", "max"),
            )
            .reset_index()
        )
    result = bases.merge(summary, on=groups, how="left")
    for column in ("anomaly_count", "severe_count", "extreme_count"):
        result[column] = result[column].fillna(0).astype(int)
    result["average_severity"] = result["average_severity"].fillna(0.0)
    result["highest_anomaly_score"] = result["highest_anomaly_score"].fillna(0.0)
    risk_rows = []
    for _, row in bases.iterrows():
        mask = pd.Series(True, index=unique.index)
        for key in groups:
            mask &= unique[key].eq(row[key])
        risk_rows.append(
            climate_risk_score(int(row["observation_count"]), unique.loc[mask])
        )
    return pd.concat([result.reset_index(drop=True), pd.DataFrame(risk_rows)], axis=1)


def country_anomaly_analysis(
    dataframe: pd.DataFrame, anomalies: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Summarize anomaly frequency, severity, and risk by country."""
    events = (
        anomalies if anomalies is not None else detect_temperature_anomalies(dataframe)
    )
    report = _location_report(dataframe, events, ["country"])
    return report.sort_values(
        ["climate_risk_score", "anomaly_count"], ascending=False
    ).reset_index(drop=True)


def city_anomaly_analysis(
    dataframe: pd.DataFrame, anomalies: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Summarize anomaly frequency, severity, and risk by city-country pair."""
    events = (
        anomalies if anomalies is not None else detect_temperature_anomalies(dataframe)
    )
    report = _location_report(dataframe, events, ["city", "country"])
    return report.sort_values(
        ["climate_risk_score", "anomaly_count"], ascending=False
    ).reset_index(drop=True)


def historical_records(
    dataframe: pd.DataFrame, anomalies: pd.DataFrame
) -> pd.DataFrame:
    """Return observed absolute temperature records and largest detected deviations."""
    _validate(dataframe)
    highest = dataframe.loc[dataframe["avg_temp_c"].idxmax()]
    lowest = dataframe.loc[dataframe["avg_temp_c"].idxmin()]
    rows: list[dict[str, Any]] = []
    for label, row in (
        ("Highest observed temperature", highest),
        ("Lowest observed temperature", lowest),
    ):
        rows.append(
            {
                "record_type": label,
                "date": row["date"],
                "country": row["country"],
                "city": row["city"],
                "observed_temperature_c": row["avg_temp_c"],
                "expected_temperature_c": np.nan,
                "deviation_c": np.nan,
                "anomaly_score": np.nan,
                "severity": "RECORD",
                "method_used": "Observed record",
            }
        )
    if not anomalies.empty:
        positive = anomalies.loc[anomalies["deviation_c"].idxmax()]
        negative = anomalies.loc[anomalies["deviation_c"].idxmin()]
        for label, row in (
            ("Largest positive deviation", positive),
            ("Largest negative deviation", negative),
        ):
            rows.append(
                {
                    "record_type": label,
                    "date": row["date"],
                    "country": row["country"],
                    "city": row["city"],
                    "observed_temperature_c": row["avg_temp_c"],
                    "expected_temperature_c": row["expected_temperature_c"],
                    "deviation_c": row["deviation_c"],
                    "anomaly_score": row["anomaly_score"],
                    "severity": row["severity"],
                    "method_used": row["method_used"],
                }
            )
    return pd.DataFrame(rows)


def _generate_insights(
    dataframe: pd.DataFrame,
    anomalies: pd.DataFrame,
    countries: pd.DataFrame,
    cities: pd.DataFrame,
) -> list[str]:
    insights: list[str] = []
    if not anomalies.empty:
        positive = anomalies.loc[anomalies["deviation_c"].idxmax()]
        insights.append(
            f"The strongest positive anomaly was {positive['deviation_c']:+.2f} °C in {positive['city']}, {positive['country']} on {positive['date']:%Y-%m-%d}."
        )
        negative = anomalies.loc[anomalies["deviation_c"].idxmin()]
        insights.append(
            f"The strongest negative anomaly was {negative['deviation_c']:+.2f} °C in {negative['city']}, {negative['country']} on {negative['date']:%Y-%m-%d}."
        )
        if not countries.empty:
            leader = countries.sort_values("severe_count", ascending=False).iloc[0]
            insights.append(
                f"{leader['country']} contains the highest count of severe or extreme anomalies ({int(leader['severe_count']):,}); {int(leader['extreme_count']):,} are EXTREME."
            )
        decade = (
            anomalies.assign(decade=(anomalies["year"] // 10) * 10)
            .groupby("decade")
            .size()
        )
        if not decade.empty:
            most = int(decade.idxmax())
            insights.append(
                f"The largest number of method-specific detections occurred in the {most}s ({int(decade.max()):,} alerts)."
            )
        by_year = _unique_events(anomalies).groupby("year").size()
        if len(by_year) >= 4:
            split_year = float(np.median(by_year.index))
            early = float(by_year.loc[by_year.index <= split_year].mean())
            late = float(by_year.loc[by_year.index > split_year].mean())
            direction = (
                "more" if late > early else "fewer" if late < early else "about as many"
            )
            insights.append(
                f"The later half of represented years had {direction} flagged observations per represented year on average ({late:.1f}) than the earlier half ({early:.1f}); changing coverage may affect this comparison."
            )
    if not cities.empty:
        risk = cities.iloc[0]
        insights.append(
            f"The highest location risk score is {risk['city']}, {risk['country']} ({risk['climate_risk_score']:.1f}/100, {risk['risk_level']})."
        )
    if not dataframe.empty:
        insights.append(
            "Alerts identify unusual behavior relative to each location's observed monthly history; they are not evidence of climate attribution or impacts."
        )
    return insights


def generate_anomaly_reports(
    dataframe: pd.DataFrame, output_dir: str | Path
) -> dict[str, Path]:
    """Generate anomaly, alert, location-risk, historical-record, and JSON reports."""
    _validate(dataframe)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    anomalies = detect_temperature_anomalies(dataframe)
    countries = country_anomaly_analysis(dataframe, anomalies)
    cities = city_anomaly_analysis(dataframe, anomalies)
    alerts = anomalies.loc[anomalies["severity"].isin(["SEVERE", "EXTREME"])].copy()
    records = historical_records(dataframe, anomalies)
    unique = _unique_events(anomalies)
    severity_counts = (
        anomalies.groupby("severity").size().reindex(SEVERITY_ORDER, fill_value=0)
    )
    overall_risk = climate_risk_score(len(dataframe), anomalies)
    insights = _generate_insights(dataframe, anomalies, countries, cities)
    summary = {
        "observation_count": len(dataframe),
        "unique_anomaly_observations": len(unique),
        "method_specific_anomaly_count": len(anomalies),
        "severe_alert_count": len(alerts),
        "severity_counts_method_specific": {
            str(key): int(value) for key, value in severity_counts.items()
        },
        "climate_risk": overall_risk,
        "detection_methods": [
            "Seasonal Z-Score",
            "Seasonal IQR",
            "Trailing rolling mean deviation",
        ],
        "insights": insights,
        "limitations": [
            "Coverage changes across years and locations; historical frequency comparisons may reflect changing observations.",
            "Monthly location-specific baselines are descriptive and do not adjust for measurement-system changes or spatial dependence.",
            "A detected anomaly is unusual relative to available local history and is not causal attribution or proof of impacts.",
        ],
    }
    reports: dict[str, pd.DataFrame] = {
        "anomalies": anomalies,
        "climate_alerts": alerts,
        "country_anomaly_report": countries,
        "city_anomaly_report": cities,
        "historical_records": records,
    }
    paths: dict[str, Path] = {}
    for name, report in reports.items():
        path = output / f"{name}.csv"
        report.to_csv(path, index=False)
        paths[name] = path
    summary_path = output / "anomaly_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    paths["anomaly_summary"] = summary_path
    return paths
