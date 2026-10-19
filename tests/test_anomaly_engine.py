import pandas as pd
import pytest

from src.anomaly_engine import (
    calculate_z_scores,
    city_anomaly_analysis,
    classify_severity,
    climate_risk_score,
    country_anomaly_analysis,
    detect_extreme_cold,
    detect_extreme_heat,
    detect_temperature_anomalies,
    generate_anomaly_reports,
    seasonal_anomaly_detection,
)


@pytest.fixture
def anomaly_frame() -> pd.DataFrame:
    rows = []
    for year in range(2010, 2025):
        for month in range(1, 13):
            for country, city, offset in (
                ("A", "North City", 0.0),
                ("B", "South City", 5.0),
            ):
                baseline = 10 + month + offset + (year % 3) * 0.1
                if year == 2024 and month == 1 and city == "North City":
                    baseline += 8
                rows.append(
                    {
                        "date": pd.Timestamp(year, month, 1),
                        "avg_temp_c": baseline,
                        "uncertainty_c": 0.2,
                        "city": city,
                        "country": country,
                        "latitude": 40.0 if country == "A" else -30.0,
                        "longitude": 10.0,
                        "year": year,
                        "month": month,
                    }
                )
    return pd.DataFrame(rows)


def test_z_score_baseline_is_location_and_month_specific(
    anomaly_frame: pd.DataFrame,
) -> None:
    scored = calculate_z_scores(anomaly_frame)
    north_january = scored[(scored.city == "North City") & (scored.month == 1)]
    outlier = north_january.loc[north_january.date.dt.year == 2024].iloc[0]
    assert outlier.z_score > 2
    assert outlier.expected_temperature_c < outlier.avg_temp_c
    assert north_january.baseline_count.eq(15).all()


def test_all_detection_methods_find_inserted_warm_observation(
    anomaly_frame: pd.DataFrame,
) -> None:
    events = detect_temperature_anomalies(anomaly_frame)
    outlier = events[
        (events.city == "North City")
        & (events.date.dt.year == 2024)
        & (events.date.dt.month == 1)
    ]
    assert {"Seasonal Z-Score", "Seasonal IQR", "Rolling Mean (12)"}.issubset(
        set(outlier.method_used)
    )
    assert outlier.severity.eq("EXTREME").all()
    assert outlier.deviation_c.gt(6).all()
    assert (
        (outlier.expected_temperature_c + outlier.deviation_c)
        .eq(outlier.avg_temp_c)
        .all()
    )


def test_heat_cold_and_seasonal_selectors(anomaly_frame: pd.DataFrame) -> None:
    heat = detect_extreme_heat(anomaly_frame)
    cold = detect_extreme_cold(anomaly_frame)
    seasonal = seasonal_anomaly_detection(anomaly_frame)
    assert not heat.empty and heat.deviation_c.ge(2).all()
    assert cold.deviation_c.le(-2).all()
    assert set(seasonal.method_used).issubset({"Seasonal Z-Score", "Seasonal IQR"})


@pytest.mark.parametrize(
    ("deviation", "score", "expected"),
    [
        (0.5, 0.5, "NORMAL"),
        (2.1, 1.0, "MODERATE"),
        (1.0, 3.0, "SEVERE"),
        (6.0, 2.0, "EXTREME"),
    ],
)
def test_severity_classification(deviation: float, score: float, expected: str) -> None:
    assert classify_severity(deviation, score) == expected


def test_risk_score_uses_frequency_magnitude_and_persistence() -> None:
    events = pd.DataFrame(
        {
            "date": pd.to_datetime(["2000-01-01", "2000-02-01", "2000-04-01"]),
            "country": ["A"] * 3,
            "city": ["X"] * 3,
            "deviation_c": [6.0, 6.0, 6.0],
            "anomaly_score": [4.0] * 3,
            "severity": ["EXTREME"] * 3,
        }
    )
    risk = climate_risk_score(10, events)
    assert risk["frequency_score"] == pytest.approx(30.0)
    assert risk["magnitude_score"] == pytest.approx(60.0)
    assert risk["persistence_score"] == pytest.approx(16.6667, rel=1e-4)
    assert 0 <= risk["climate_risk_score"] <= 100
    assert risk["risk_level"] in {"Low", "Medium", "High", "Critical"}


def test_country_and_city_reports(anomaly_frame: pd.DataFrame) -> None:
    events = detect_temperature_anomalies(anomaly_frame)
    countries = country_anomaly_analysis(anomaly_frame, events).set_index("country")
    cities = city_anomaly_analysis(anomaly_frame, events).set_index(["country", "city"])
    assert countries.loc["A", "anomaly_count"] > 0
    assert countries.loc["A", "extreme_count"] > 0
    assert countries.loc["A", "climate_risk_score"] > 0
    assert cities.loc[("A", "North City"), "highest_anomaly_score"] > 0
    assert cities.loc[("B", "South City"), "anomaly_count"] == 0


def test_report_generation_writes_csv_and_json(
    tmp_path, anomaly_frame: pd.DataFrame
) -> None:
    paths = generate_anomaly_reports(anomaly_frame, tmp_path)
    assert {
        "climate_alerts",
        "anomalies",
        "anomaly_summary",
        "historical_records",
        "country_anomaly_report",
        "city_anomaly_report",
    }.issubset(paths)
    assert all(path.is_file() for path in paths.values())
