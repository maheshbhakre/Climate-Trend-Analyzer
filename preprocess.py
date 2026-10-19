"""Reusable preprocessing pipeline for the source temperature observations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.anomaly_engine import generate_anomaly_reports
from src.data_loader import (
    DEFAULT_RAW_PATH,
    PROJECT_ROOT,
    normalize_schema,
    parse_dates,
    return_clean_dataframe,
    validate_required_columns,
)
from src.data_loader import (
    load_raw_data as _load_raw_data,
)
from src.data_validation import (
    coordinate_validation,
    date_validation,
    duplicate_detection,
    generate_reports,
    missing_value_audit,
    quality_score,
    temperature_validation,
)
from src.forecast_engine import generate_forecast_reports
from src.trend_analysis import generate_analytics_reports

DEFAULT_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "climate_cleaned.csv"
DEFAULT_REPORTS_PATH = PROJECT_ROOT / "outputs" / "reports"


def load_raw_data(path: str | Path = DEFAULT_RAW_PATH) -> pd.DataFrame:
    return _load_raw_data(path)


def clean_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize, parse, validate screening ranges, and retain canonical rows."""
    return create_features(return_clean_dataframe(dataframe))


def validate_data(dataframe: pd.DataFrame) -> dict[str, object]:
    """Return raw-input audit results without hiding invalid or missing records."""
    validate_required_columns(dataframe)
    canonical = normalize_schema(dataframe)
    canonical = parse_dates(canonical)
    from src.data_loader import parse_coordinates

    canonical = parse_coordinates(canonical)
    return {
        "missing_values": missing_value_audit(dataframe),
        "duplicates": duplicate_detection(dataframe),
        "coordinates": coordinate_validation(canonical),
        "dates": date_validation(dataframe),
        "temperatures": temperature_validation(dataframe),
        "quality": quality_score(dataframe),
    }


def create_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Derive calendar year and month from actual observation dates."""
    featured = dataframe.copy()
    if "date" not in featured.columns:
        featured = parse_dates(featured)
    featured["year"] = featured["date"].dt.year.astype("Int64")
    featured["month"] = featured["date"].dt.month.astype("Int64")
    return featured


def save_processed_data(
    dataframe: pd.DataFrame,
    path: str | Path = DEFAULT_PROCESSED_PATH,
) -> Path:
    """Persist only the documented canonical schema."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(destination, index=False, date_format="%Y-%m-%d")
    return destination


def run_pipeline(
    raw_path: str | Path = DEFAULT_RAW_PATH,
    processed_path: str | Path = DEFAULT_PROCESSED_PATH,
    reports_path: str | Path = DEFAULT_REPORTS_PATH,
) -> pd.DataFrame:
    raw = load_raw_data(raw_path)
    validate_required_columns(raw)
    cleaned = clean_data(raw)
    if cleaned.empty:
        raise ValueError("No valid climate observations remain after data validation.")
    saved_path = save_processed_data(cleaned, processed_path)
    reports = generate_reports(raw, cleaned, reports_path)
    analytics_reports = generate_analytics_reports(cleaned, reports_path)
    anomaly_reports = generate_anomaly_reports(cleaned, reports_path)
    forecast_reports = generate_forecast_reports(cleaned, reports_path)
    print(f"Processed {len(cleaned):,} valid records from {len(raw):,} source rows.")
    print(f"Canonical dataset: {saved_path}")
    for report_path in reports.values():
        print(f"Report: {report_path}")
    for report_path in analytics_reports.values():
        print(f"Report: {report_path}")
    for report_path in anomaly_reports.values():
        print(f"Report: {report_path}")
    for report_path in forecast_reports.values():
        print(f"Report: {report_path}")
    print(
        f"Quality: {quality_score(raw)['quality_score']}/100 ({quality_score(raw)['quality_level']})"
    )
    return cleaned


if __name__ == "__main__":
    run_pipeline()
