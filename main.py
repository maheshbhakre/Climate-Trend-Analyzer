import pandas as pd

from preprocess import clean_data
from src.analysis import run_eda, trend_analysis, detect_anomalies


# LOAD DATA
df = pd.read_csv("data/raw/climate.csv")

# CLEAN DATA
df = clean_data(df)

print("\n✅ Cleaned Data Preview:")
print(df.head())

# SAVE CLEAN DATA
df.to_csv("data/processed/cleaned_climate.csv", index=False)

print("\n💾 Cleaned data saved successfully!")

# EDA
run_eda(df)

# TREND ANALYSIS
trend_analysis(df)

# ANOMALY DETECTION
detect_anomalies(df)

print("\n🚀 PROJECT EXECUTED SUCCESSFULLY")