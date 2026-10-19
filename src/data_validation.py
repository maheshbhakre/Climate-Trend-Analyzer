"""Transparent validation audits and CSV report generation for climate data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_loader import (
    CANONICAL_COLUMNS,
    RAW_TO_CANONICAL,
    TEMPERATURE_MAX_C,
    TEMPERATURE_MIN_C,
)

QUALITY_LEVELS = ((90, "Excellent"), (75, "Good"), (60, "Moderate"), (0, "Poor"))


def schema_validation(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Report required canonical columns and basic type/null facts per field."""
    rows = []
    for column in CANONICAL_COLUMNS:
        present = column in dataframe.columns
        values = dataframe[column] if present else pd.Series(dtype="object")
        rows.append(
            {
                "field": column,
                "required": True,
                "present": present,
                "dtype": str(values.dtype) if present else "missing",
                "record_count": len(dataframe),
                "missing_count": int(values.isna().sum())
                if present
                else len(dataframe),
                "status": "PASS" if present and not values.isna().any() else "FAIL",
            }
        )
    return pd.DataFrame(rows)


def missing_value_audit(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Count missing values and percentages for all columns in the supplied frame."""
    denominator = len(dataframe)
    return pd.DataFrame(
        [
            {
                "field": column,
                "record_count": denominator,
                "missing_count": int(dataframe[column].isna().sum()),
                "missing_percent": (
                    float(dataframe[column].isna().mean() * 100) if denominator else 0.0
                ),
            }
            for column in dataframe.columns
        ]
    )


def duplicate_detection(dataframe: pd.DataFrame) -> dict[str, int]:
    """Count exact duplicate rows and repeated city-country-date observations."""
    key_columns = [
        column for column in ("dt", "City", "Country") if column in dataframe
    ]
    if not key_columns:
        key_columns = [
            column for column in ("date", "city", "country") if column in dataframe
        ]
    return {
        "exact_duplicate_rows": int(dataframe.duplicated().sum()),
        "duplicate_observation_keys": (
            int(dataframe.duplicated(key_columns).sum()) if len(key_columns) == 3 else 0
        ),
    }


def coordinate_validation(dataframe: pd.DataFrame) -> dict[str, int]:
    """Count missing and out-of-range coordinate pairs in canonical data."""
    if not {"latitude", "longitude"}.issubset(dataframe.columns):
        return {
            "missing_coordinate_pairs": len(dataframe),
            "invalid_coordinate_pairs": 0,
        }
    lat = pd.to_numeric(dataframe["latitude"], errors="coerce")
    lon = pd.to_numeric(dataframe["longitude"], errors="coerce")
    missing = lat.isna() | lon.isna()
    valid = lat.between(-90, 90) & lon.between(-180, 180)
    return {
        "missing_coordinate_pairs": int(missing.sum()),
        "invalid_coordinate_pairs": int((~missing & ~valid).sum()),
    }


def date_validation(dataframe: pd.DataFrame) -> dict[str, object]:
    """Summarize parseable dates and observed date bounds."""
    column = "date" if "date" in dataframe else "dt" if "dt" in dataframe else None
    if column is None:
        return {
            "date_field_present": False,
            "invalid_date_count": len(dataframe),
            "date_start": "",
            "date_end": "",
        }
    values = pd.to_datetime(dataframe[column], errors="coerce")
    valid = values.dropna()
    return {
        "date_field_present": True,
        "invalid_date_count": int(values.isna().sum()),
        "date_start": str(valid.min().date()) if not valid.empty else "",
        "date_end": str(valid.max().date()) if not valid.empty else "",
    }


def temperature_validation(dataframe: pd.DataFrame) -> dict[str, object]:
    """Count missing, non-numeric, and out-of-screening-range temperatures."""
    column = "avg_temp_c" if "avg_temp_c" in dataframe else "AverageTemperature"
    if column not in dataframe:
        return {
            "temperature_field_present": False,
            "invalid_temperature_count": len(dataframe),
            "temperature_min_c": "",
            "temperature_max_c": "",
        }
    values = pd.to_numeric(dataframe[column], errors="coerce")
    valid = values.between(TEMPERATURE_MIN_C, TEMPERATURE_MAX_C)
    nonmissing = values.notna()
    return {
        "temperature_field_present": True,
        "invalid_temperature_count": int((nonmissing & ~valid).sum()),
        "missing_temperature_count": int(values.isna().sum()),
        "temperature_min_c": float(values.min()) if nonmissing.any() else "",
        "temperature_max_c": float(values.max()) if nonmissing.any() else "",
        "screening_range_c": f"{TEMPERATURE_MIN_C} to {TEMPERATURE_MAX_C}",
    }


def coverage_analysis(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Report per-country record, city, and date coverage from valid observations."""
    if dataframe.empty or not {"country", "city", "date"}.issubset(dataframe.columns):
        return pd.DataFrame(
            columns=[
                "country",
                "record_count",
                "city_count",
                "date_start",
                "date_end",
                "year_count",
                "observed_months",
            ]
        )
    grouped = (
        dataframe.groupby("country", dropna=False)
        .agg(
            record_count=("date", "size"),
            city_count=("city", "nunique"),
            date_start=("date", "min"),
            date_end=("date", "max"),
            year_count=("year", "nunique"),
            observed_months=("date", lambda values: values.dt.to_period("M").nunique()),
        )
        .reset_index()
    )
    grouped["date_start"] = grouped["date_start"].dt.strftime("%Y-%m-%d")
    grouped["date_end"] = grouped["date_end"].dt.strftime("%Y-%m-%d")
    month_bounds = dataframe.groupby("country")["date"].agg(["min", "max"])
    month_span = (month_bounds["max"].dt.year - month_bounds["min"].dt.year) * 12
    month_span += month_bounds["max"].dt.month - month_bounds["min"].dt.month + 1
    grouped["expected_months_in_country_span"] = grouped["country"].map(month_span)
    grouped["month_coverage_percent"] = (
        grouped["observed_months"] / grouped["expected_months_in_country_span"] * 100
    ).round(2)
    return grouped.sort_values("country").reset_index(drop=True)


def _quality_components(raw_dataframe: pd.DataFrame) -> dict[str, float]:
    total = len(raw_dataframe)
    if total == 0:
        return {
            "completeness": 0.0,
            "consistency": 0.0,
            "coverage": 0.0,
            "validity": 0.0,
        }

    expected_raw = list(RAW_TO_CANONICAL)
    present_raw = [column for column in expected_raw if column in raw_dataframe]
    completeness = (
        float(raw_dataframe[present_raw].notna().to_numpy().mean() * 100)
        if present_raw
        else 0.0
    )

    duplicates = duplicate_detection(raw_dataframe)
    consistency = max(
        0.0,
        100.0 * (1 - duplicates["duplicate_observation_keys"] / total),
    )

    dates = date_validation(raw_dataframe)
    start = pd.to_datetime(dates["date_start"], errors="coerce")
    end = pd.to_datetime(dates["date_end"], errors="coerce")
    observed = pd.to_datetime(
        raw_dataframe["dt"] if "dt" in raw_dataframe else raw_dataframe.get("date"),
        errors="coerce",
    ).dropna()
    if pd.isna(start) or pd.isna(end) or observed.empty:
        coverage = 0.0
    else:
        expected_months = (end.year - start.year) * 12 + end.month - start.month + 1
        coverage = min(
            100.0, observed.dt.to_period("M").nunique() / expected_months * 100
        )

    coords = pd.DataFrame()
    if {"Latitude", "Longitude"}.issubset(raw_dataframe.columns):
        coords = raw_dataframe.rename(
            columns={"Latitude": "latitude", "Longitude": "longitude"}
        )
        from src.data_loader import parse_coordinates

        coords = parse_coordinates(coords)
    coord_result = coordinate_validation(coords)
    temperatures = pd.to_numeric(
        raw_dataframe.get("AverageTemperature", raw_dataframe.get("avg_temp_c")),
        errors="coerce",
    )
    nonmissing_temperature = temperatures.notna()
    valid_temperature_share = (
        float(
            temperatures[nonmissing_temperature]
            .between(TEMPERATURE_MIN_C, TEMPERATURE_MAX_C)
            .mean()
            * 100
        )
        if nonmissing_temperature.any()
        else 0.0
    )
    coordinate_denominator = max(total, 1)
    valid_coordinate_share = max(
        0.0,
        100.0
        * (
            total
            - coord_result["missing_coordinate_pairs"]
            - coord_result["invalid_coordinate_pairs"]
        )
        / coordinate_denominator,
    )
    source_dates = (
        raw_dataframe["dt"] if "dt" in raw_dataframe else raw_dataframe.get("date")
    )
    date_values = pd.to_datetime(source_dates, errors="coerce")
    nonmissing_date = source_dates.notna()
    valid_date_share = (
        float(date_values[nonmissing_date].notna().mean() * 100)
        if nonmissing_date.any()
        else 0.0
    )
    uncertainty_column = (
        "AverageTemperatureUncertainty"
        if "AverageTemperatureUncertainty" in raw_dataframe
        else "uncertainty_c"
    )
    uncertainty = pd.to_numeric(raw_dataframe.get(uncertainty_column), errors="coerce")
    uncertainty_present = uncertainty.notna()
    uncertainty_valid_share = (
        float(uncertainty[uncertainty_present].ge(0).mean() * 100)
        if uncertainty_present.any()
        else 0.0
    )
    validity = (
        valid_temperature_share
        + valid_coordinate_share
        + valid_date_share
        + uncertainty_valid_share
    ) / 4
    return {
        "completeness": completeness,
        "consistency": consistency,
        "coverage": coverage,
        "validity": validity,
    }


def quality_score(raw_dataframe: pd.DataFrame) -> dict[str, object]:
    """Return equal-weight 0-100 quality score and component percentages."""
    components = _quality_components(raw_dataframe)
    score = round(sum(components.values()) / len(components), 2)
    level = next(label for threshold, label in QUALITY_LEVELS if score >= threshold)
    return {"quality_score": score, "quality_level": level, **components}


def _quality_report(
    raw_dataframe: pd.DataFrame, clean_dataframe: pd.DataFrame
) -> pd.DataFrame:
    score = quality_score(raw_dataframe)
    missing = missing_value_audit(raw_dataframe)
    duplicate = duplicate_detection(raw_dataframe)
    dates = date_validation(raw_dataframe)
    temperatures = temperature_validation(raw_dataframe)
    coords = raw_dataframe.rename(
        columns={"Latitude": "latitude", "Longitude": "longitude"}
    )
    if {"latitude", "longitude"}.issubset(coords.columns):
        from src.data_loader import parse_coordinates

        coords = parse_coordinates(coords)
    coordinate = coordinate_validation(coords)
    items: dict[str, object] = {
        **score,
        "raw_record_count": len(raw_dataframe),
        "clean_record_count": len(clean_dataframe),
        "excluded_record_count": len(raw_dataframe) - len(clean_dataframe),
        "missing_value_count": int(raw_dataframe.isna().sum().sum()),
        **duplicate,
        **dates,
        **temperatures,
        **coordinate,
    }
    rows = [{"indicator": key, "value": value} for key, value in items.items()]
    rows.extend(
        {"indicator": f"missing_{row.field}", "value": row.missing_count}
        for row in missing.itertuples(index=False)
    )
    rows.extend(
        {"indicator": f"missing_percent_{row.field}", "value": row.missing_percent}
        for row in missing.itertuples(index=False)
    )
    return pd.DataFrame(rows)


def generate_reports(
    raw_dataframe: pd.DataFrame,
    clean_dataframe: pd.DataFrame,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write requested quality, coverage, and schema reports under output_dir."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    reports = {
        "data_quality_report": _quality_report(raw_dataframe, clean_dataframe),
        "data_coverage_report": coverage_analysis(clean_dataframe),
        "schema_validation_report": schema_validation(clean_dataframe),
        "data_dictionary": data_dictionary_report(),
    }
    paths = {}
    for name, report in reports.items():
        path = output / f"{name}.csv"
        report.to_csv(path, index=False)
        paths[name] = path
    return paths


def data_dictionary_report() -> pd.DataFrame:
    """Machine-readable canonical field definitions and their source mappings."""
    definitions = [
        ("date", "datetime64[ns]", "Observation calendar date", "dt", "YYYY-MM-DD"),
        (
            "avg_temp_c",
            "float64",
            "Recorded average temperature",
            "AverageTemperature",
            "°C by canonical convention; source units are undocumented",
        ),
        (
            "uncertainty_c",
            "float64",
            "Recorded temperature uncertainty",
            "AverageTemperatureUncertainty",
            "°C by canonical convention; source definition is undocumented",
        ),
        ("city", "string", "Source city label", "City", "Name as supplied by source"),
        (
            "country",
            "string",
            "Source country label",
            "Country",
            "Name as supplied by source",
        ),
        (
            "latitude",
            "float64",
            "Signed latitude",
            "Latitude",
            "Decimal degrees; N positive, S negative",
        ),
        (
            "longitude",
            "float64",
            "Signed longitude",
            "Longitude",
            "Decimal degrees; E positive, W negative",
        ),
        (
            "year",
            "Int64",
            "Calendar year derived from date",
            "Derived from date",
            "Four-digit calendar year",
        ),
        (
            "month",
            "Int64",
            "Calendar month derived from date",
            "Derived from date",
            "Integer 1-12",
        ),
    ]
    return pd.DataFrame(
        definitions,
        columns=[
            "field",
            "canonical_type",
            "description",
            "source_or_derivation",
            "units_or_format",
        ],
    )
