"""Load and normalize the repository's historical temperature dataset."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "climate.csv"

RAW_TO_CANONICAL = {
    "dt": "date",
    "AverageTemperature": "avg_temp_c",
    "AverageTemperatureUncertainty": "uncertainty_c",
    "City": "city",
    "Country": "country",
    "Latitude": "latitude",
    "Longitude": "longitude",
}
REQUIRED_RAW_COLUMNS = tuple(RAW_TO_CANONICAL)
CANONICAL_COLUMNS = (
    "date",
    "avg_temp_c",
    "uncertainty_c",
    "city",
    "country",
    "latitude",
    "longitude",
    "year",
    "month",
)
TEMPERATURE_MIN_C = -90.0
TEMPERATURE_MAX_C = 60.0


def load_raw_data(path: str | Path = DEFAULT_RAW_PATH) -> pd.DataFrame:
    """Read the source CSV and report missing or unreadable inputs clearly."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Climate source file was not found: {source}")
    try:
        return pd.read_csv(source)
    except (pd.errors.ParserError, UnicodeDecodeError, OSError) as exc:
        raise ValueError(
            f"Could not read climate source file '{source}': {exc}"
        ) from exc


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: tuple[str, ...] = REQUIRED_RAW_COLUMNS,
) -> None:
    """Raise a useful error when source fields required by this project are absent."""
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(
            "Climate data is missing required source column(s): " + ", ".join(missing)
        )


def normalize_schema(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Rename source columns and normalize text values without changing measurements."""
    validate_required_columns(dataframe)
    normalized = dataframe.rename(columns=RAW_TO_CANONICAL).copy()
    for column in ("city", "country"):
        normalized[column] = normalized[column].astype("string").str.strip()
        normalized[column] = normalized[column].replace("", pd.NA)
    for column in ("avg_temp_c", "uncertainty_c"):
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
    return normalized


def parse_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, representing malformed or missing values as NaT for auditing."""
    date_column = "date" if "date" in dataframe.columns else "dt"
    if date_column not in dataframe.columns:
        raise ValueError(
            "Cannot parse dates: neither 'date' nor source field 'dt' exists."
        )
    parsed = dataframe.copy()
    parsed["date"] = pd.to_datetime(
        parsed[date_column], errors="coerce", format="mixed"
    )
    if date_column != "date":
        parsed = parsed.drop(columns=[date_column])
    return parsed


def _parse_coordinate(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().upper()
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([NSEW])?", text)
    if not match:
        return float("nan")
    number = float(match.group(1))
    hemisphere = match.group(2)
    if hemisphere in {"S", "W"}:
        number = -abs(number)
    elif hemisphere in {"N", "E"}:
        number = abs(number)
    return number


def parse_coordinates(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert decimal hemisphere strings (for example ``3.23W``) to signed floats."""
    parsed = dataframe.copy()
    for column in ("latitude", "longitude"):
        if column not in parsed.columns:
            raise ValueError(
                f"Cannot parse coordinates: required field '{column}' is absent."
            )
        parsed[column] = parsed[column].map(_parse_coordinate).astype("float64")
    return parsed


def return_clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return canonical, usable observations; excluded rows remain visible in raw reports."""
    cleaned = normalize_schema(dataframe)
    cleaned = parse_dates(cleaned)
    cleaned = parse_coordinates(cleaned)
    cleaned["year"] = cleaned["date"].dt.year.astype("Int64")
    cleaned["month"] = cleaned["date"].dt.month.astype("Int64")

    coordinates_valid = cleaned["latitude"].between(-90, 90) & cleaned[
        "longitude"
    ].between(-180, 180)
    temperature_valid = cleaned["avg_temp_c"].between(
        TEMPERATURE_MIN_C, TEMPERATURE_MAX_C
    )
    uncertainty_valid = cleaned["uncertainty_c"].ge(0)
    required_values_present = (
        cleaned[["date", "avg_temp_c", "uncertainty_c", "city", "country"]]
        .notna()
        .all(axis=1)
    )
    keep = (
        required_values_present
        & coordinates_valid
        & temperature_valid
        & uncertainty_valid
    )
    return cleaned.loc[keep, list(CANONICAL_COLUMNS)].reset_index(drop=True)
