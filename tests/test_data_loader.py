import pandas as pd
import pytest

from src.data_loader import (
    CANONICAL_COLUMNS,
    load_raw_data,
    parse_coordinates,
    parse_dates,
    return_clean_dataframe,
    validate_required_columns,
)


@pytest.fixture
def raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dt": ["2000-01-01", "2000-02-01"],
            "AverageTemperature": [12.5, 13.0],
            "AverageTemperatureUncertainty": [0.2, 0.3],
            "City": ["Test City", "Test City"],
            "Country": ["Test Country", "Test Country"],
            "Latitude": ["5.63N", "5.63N"],
            "Longitude": ["3.23W", "3.23W"],
        }
    )


def test_clean_dataframe_enforces_canonical_schema(raw_frame: pd.DataFrame) -> None:
    clean = return_clean_dataframe(raw_frame)
    assert clean.columns.tolist() == list(CANONICAL_COLUMNS)
    assert clean["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2000-01-01",
        "2000-02-01",
    ]
    assert clean["year"].tolist() == [2000, 2000]
    assert clean["month"].tolist() == [1, 2]
    assert clean["latitude"].tolist() == [5.63, 5.63]
    assert clean["longitude"].tolist() == [-3.23, -3.23]


def test_missing_required_source_column_is_reported(raw_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="AverageTemperature"):
        validate_required_columns(raw_frame.drop(columns="AverageTemperature"))


def test_malformed_dates_are_retained_as_nat_for_audit(raw_frame: pd.DataFrame) -> None:
    malformed = raw_frame.copy()
    malformed.loc[0, "dt"] = "not-a-date"
    parsed = parse_dates(malformed)
    assert pd.isna(parsed.loc[0, "date"])
    assert parsed.loc[1, "date"] == pd.Timestamp("2000-02-01")
    assert len(return_clean_dataframe(malformed)) == 1


def test_coordinate_parsing_handles_hemispheres_and_invalid_values() -> None:
    frame = pd.DataFrame(
        {"latitude": ["12.5S", "90N", "unknown"], "longitude": ["45E", "180W", "0"]}
    )
    parsed = parse_coordinates(frame)
    assert parsed["latitude"].iloc[0] == -12.5
    assert parsed["latitude"].iloc[1] == 90
    assert pd.isna(parsed["latitude"].iloc[2])
    assert parsed["longitude"].tolist() == [45, -180, 0]


def test_missing_source_file_has_actionable_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Climate source file was not found"):
        load_raw_data(tmp_path / "missing.csv")
