import pandas as pd
import pytest

from src.data_loader import return_clean_dataframe
from src.data_validation import (
    coordinate_validation,
    coverage_analysis,
    duplicate_detection,
    generate_reports,
    quality_score,
    schema_validation,
)


@pytest.fixture
def raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dt": ["2000-01-01", "2000-02-01", "2000-02-01"],
            "AverageTemperature": [12.5, 13.0, 13.0],
            "AverageTemperatureUncertainty": [0.2, 0.3, 0.3],
            "City": ["A", "A", "A"],
            "Country": ["X", "X", "X"],
            "Latitude": ["5.63N", "5.63N", "5.63N"],
            "Longitude": ["3.23W", "3.23W", "3.23W"],
        }
    )


def test_duplicate_detection_counts_exact_and_observation_duplicates(
    raw_frame: pd.DataFrame,
) -> None:
    result = duplicate_detection(raw_frame)
    assert result["exact_duplicate_rows"] == 1
    assert result["duplicate_observation_keys"] == 1


def test_coordinate_validation_flags_out_of_range_values() -> None:
    data = pd.DataFrame({"latitude": [91.0, 0.0], "longitude": [0.0, -181.0]})
    result = coordinate_validation(data)
    assert result["invalid_coordinate_pairs"] == 2
    assert result["missing_coordinate_pairs"] == 0


def test_schema_validation_enforces_every_canonical_field(
    raw_frame: pd.DataFrame,
) -> None:
    canonical = return_clean_dataframe(raw_frame)
    report = schema_validation(canonical)
    assert len(report) == 9
    assert report["present"].all()
    assert (report["status"] == "PASS").all()


def test_quality_score_is_bounded_and_has_documented_components(
    raw_frame: pd.DataFrame,
) -> None:
    result = quality_score(raw_frame)
    assert 0 <= result["quality_score"] <= 100
    assert result["quality_level"] in {"Excellent", "Good", "Moderate", "Poor"}
    assert {"completeness", "consistency", "coverage", "validity"}.issubset(result)


def test_coverage_report_has_country_counts(raw_frame: pd.DataFrame) -> None:
    report = coverage_analysis(return_clean_dataframe(raw_frame))
    assert report.loc[0, "country"] == "X"
    assert report.loc[0, "city_count"] == 1
    assert report.loc[0, "record_count"] == 3


def test_report_generation_writes_requested_csvs(
    raw_frame: pd.DataFrame, tmp_path
) -> None:
    clean = return_clean_dataframe(raw_frame)
    paths = generate_reports(raw_frame, clean, tmp_path)
    assert set(paths) == {
        "data_quality_report",
        "data_coverage_report",
        "schema_validation_report",
        "data_dictionary",
    }
    assert all(path.is_file() for path in paths.values())


def test_empty_quality_input_has_poor_zero_score() -> None:
    empty = pd.DataFrame(
        columns=[
            "dt",
            "AverageTemperature",
            "AverageTemperatureUncertainty",
            "City",
            "Country",
            "Latitude",
            "Longitude",
        ]
    )
    result = quality_score(empty)
    assert result["quality_score"] == 0
    assert result["quality_level"] == "Poor"
