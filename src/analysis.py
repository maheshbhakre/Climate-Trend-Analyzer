"""Descriptive analyses over the canonical climate observation schema."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_loader import CANONICAL_COLUMNS


def _require_canonical(dataframe: pd.DataFrame) -> None:
    missing = [
        column for column in CANONICAL_COLUMNS if column not in dataframe.columns
    ]
    if missing:
        raise ValueError(
            "Analysis requires the canonical schema; missing: " + ", ".join(missing)
        )
    if dataframe.empty:
        raise ValueError("Analysis cannot run on an empty climate dataset.")


def run_eda(dataframe: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return transparent annual and monthly observation summaries."""
    _require_canonical(dataframe)
    annual = dataframe.groupby("year", as_index=False).agg(
        mean_avg_temp_c=("avg_temp_c", "mean"),
        median_avg_temp_c=("avg_temp_c", "median"),
        observation_count=("avg_temp_c", "size"),
        mean_uncertainty_c=("uncertainty_c", "mean"),
    )
    monthly = dataframe.groupby("month", as_index=False).agg(
        mean_avg_temp_c=("avg_temp_c", "mean"),
        observation_count=("avg_temp_c", "size"),
    )
    return {"annual_summary": annual, "month_of_year_summary": monthly}


def trend_analysis(dataframe: pd.DataFrame) -> dict[str, float | int]:
    """Estimate a descriptive linear slope across annual observation means.

    This is a simple unweighted fit to annual rows, not a causal attribution
    analysis or a population/area-weighted global temperature estimate.
    """
    _require_canonical(dataframe)
    annual = dataframe.groupby("year", as_index=False)["avg_temp_c"].mean()
    if len(annual) < 2:
        raise ValueError(
            "At least two distinct years are required to estimate a trend."
        )
    slope, intercept = np.polyfit(annual["year"].astype(float), annual["avg_temp_c"], 1)
    return {
        "slope_c_per_year": float(slope),
        "intercept": float(intercept),
        "year_count": len(annual),
        "first_year": int(annual["year"].min()),
        "last_year": int(annual["year"].max()),
    }


def detect_anomalies(dataframe: pd.DataFrame, threshold: float = 3.5) -> pd.DataFrame:
    """Flag within-city robust deviations for review; flags are not event labels."""
    _require_canonical(dataframe)
    if threshold <= 0:
        raise ValueError("Anomaly threshold must be greater than zero.")
    result = dataframe.copy()
    grouped = result.groupby("city")["avg_temp_c"]
    medians = grouped.transform("median")
    absolute_deviation = (result["avg_temp_c"] - medians).abs()
    mad = absolute_deviation.groupby(result["city"]).transform("median")
    denominator = 1.4826 * mad.replace(0, np.nan)
    result["robust_city_score"] = (result["avg_temp_c"] - medians) / denominator
    result["is_review_flag"] = (
        result["robust_city_score"].abs().gt(threshold).fillna(False)
    )
    return result.loc[result["is_review_flag"]].reset_index(drop=True)
