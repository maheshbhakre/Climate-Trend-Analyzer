import pandas as pd
import pytest

from src.trend_analysis import (
    annual_temperature_trends,
    city_trend_report,
    country_trend_report,
    decadal_temperature_trends,
    generate_analytics_reports,
    generate_insights,
    monthly_temperature_trends,
    rolling_temperature_average,
    seasonality_report,
    statistical_trend_report,
    temperature_change_over_time,
)


@pytest.fixture
def climate_frame() -> pd.DataFrame:
    rows = []
    for year in (1999, 2000, 2001, 2010):
        for month in range(1, 13):
            for country, city, base, rate, latitude in (
                ("A", "North City", 10.0, 1.0, 40.0),
                ("B", "South City", 20.0, 0.5, -30.0),
            ):
                temperature = base + (year - 1999) * rate + (month - 1)
                rows.append(
                    {
                        "date": pd.Timestamp(year, month, 1),
                        "avg_temp_c": temperature,
                        "uncertainty_c": 0.2 if country == "A" else 0.4,
                        "city": city,
                        "country": country,
                        "latitude": latitude,
                        "longitude": 10.0,
                        "year": year,
                        "month": month,
                    }
                )
    return pd.DataFrame(rows)


def test_country_metrics_and_warming_rank(climate_frame: pd.DataFrame) -> None:
    report = country_trend_report(climate_frame).set_index("country")
    assert report.loc["A", "warming_rate_c_per_decade"] == pytest.approx(10.0)
    assert report.loc["B", "warming_rate_c_per_decade"] == pytest.approx(5.0)
    assert report.loc["A", "country_ranking"] == 1
    assert report.loc["A", "observation_count"] == 48
    assert report.loc["A", "average_uncertainty_c"] == pytest.approx(0.2)


def test_city_metrics_and_average_temperature_ranking(
    climate_frame: pd.DataFrame,
) -> None:
    report = city_trend_report(climate_frame)
    assert report.iloc[0]["city"] == "South City"
    assert report.iloc[0]["city_ranking"] == 1
    assert report.loc[
        report["city"] == "North City", "warming_trend_c_per_decade"
    ].iloc[0] == pytest.approx(10.0)


def test_monthly_annual_and_rolling_trends(climate_frame: pd.DataFrame) -> None:
    monthly = monthly_temperature_trends(climate_frame)
    annual = annual_temperature_trends(climate_frame)
    assert len(monthly) == 48
    assert annual.loc[annual["year"] == 1999, "observation_count"].iloc[0] == 24
    rolling = rolling_temperature_average(climate_frame, window=2)
    assert pd.isna(rolling.loc[0, "rolling_average_c"])
    assert rolling["rolling_average_c"].notna().any()
    changes = temperature_change_over_time(climate_frame)
    assert changes.iloc[0]["temperature_change_c"] == pytest.approx(0.0)


def test_seasonality_monthly_and_hemisphere_profiles(
    climate_frame: pd.DataFrame,
) -> None:
    report = seasonality_report(climate_frame)
    monthly = report[report["report_section"] == "monthly_average"]
    assert len(monthly) == 12
    summary = report[report["report_section"] == "pooled_monthly_summary"].iloc[0]
    assert summary["warmest_month"] == "December"
    assert summary["coldest_month"] == "January"
    assert summary["temperature_spread_c"] == pytest.approx(11.0)
    seasonal = report[report["report_section"] == "seasonal_profile"]
    assert set(seasonal["hemisphere"]) == {"Northern", "Southern"}


def test_decadal_changes_and_extreme_decades(climate_frame: pd.DataFrame) -> None:
    report = decadal_temperature_trends(climate_frame)
    assert report["decade"].tolist() == [1990, 2000, 2010]
    assert report.loc[report["decade"] == 2000, "decade_to_decade_change_c"].iloc[
        0
    ] == pytest.approx(1.125)
    assert report.loc[report["decade"] == 2010, "decade_to_decade_change_c"].iloc[
        0
    ] == pytest.approx(7.125)
    assert report["highest_temperature_decade"].iloc[0] == 2010


def test_statistical_trend_calculation_and_confidence_interval(
    climate_frame: pd.DataFrame,
) -> None:
    report = statistical_trend_report(climate_frame).iloc[0]
    assert report["trend_slope_c_per_year"] == pytest.approx(0.75)
    assert report["r_squared"] == pytest.approx(1.0)
    assert report["year_temperature_correlation"] == pytest.approx(1.0)
    assert report["slope_ci95_lower_c_per_year"] <= report["trend_slope_c_per_year"]
    assert report["slope_ci95_upper_c_per_year"] >= report["trend_slope_c_per_year"]


def test_insights_are_generated_from_reported_metrics(
    climate_frame: pd.DataFrame,
) -> None:
    insights = generate_insights(climate_frame)
    assert any("increased from" in insight for insight in insights)
    assert any("strongest country warming-rate" in insight for insight in insights)
    assert any("highest city-country average" in insight for insight in insights)
    assert any("between adjacent observed decades" in insight for insight in insights)


def test_report_generation_writes_all_phase_two_files(
    climate_frame: pd.DataFrame, tmp_path
) -> None:
    reports = generate_analytics_reports(climate_frame, tmp_path)
    assert len(reports) == 6
    assert all(path.is_file() for path in reports.values())
    assert {path.name for path in reports.values()} == {
        "country_trend_report.csv",
        "city_trend_report.csv",
        "seasonality_report.csv",
        "decade_trend_report.csv",
        "statistical_trend_report.csv",
        "uncertainty_report.csv",
    }


def test_invalid_rolling_window_and_empty_input_fail_clearly(
    climate_frame: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="positive number"):
        rolling_temperature_average(climate_frame, window=0)
    with pytest.raises(ValueError, match="empty dataset"):
        annual_temperature_trends(climate_frame.iloc[0:0])
