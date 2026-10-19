"""Run preprocessing, generate audit reports, and print descriptive summaries."""

from __future__ import annotations

from preprocess import run_pipeline
from src.analysis import detect_anomalies, run_eda, trend_analysis
from src.data_loader import DEFAULT_RAW_PATH


def main() -> None:
    dataframe = run_pipeline(DEFAULT_RAW_PATH)
    summaries = run_eda(dataframe)
    trend = trend_analysis(dataframe)
    review_flags = detect_anomalies(dataframe)
    print("\nAnnual summary preview:")
    print(summaries["annual_summary"].head().to_string(index=False))
    print("\nDescriptive linear trend (not causal attribution):")
    print(
        f"{trend['slope_c_per_year']:.6f} °C per year over {trend['year_count']} years"
    )
    print(f"Robust within-city review flags: {len(review_flags):,}")


if __name__ == "__main__":
    main()
