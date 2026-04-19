import pandas as pd
import os

# INPUT (your raw dataset)
INPUT_PATH = "data/raw/climate.csv"

# OUTPUT
OUTPUT_PATH = "data/processed/climate_cleaned.csv"

os.makedirs("data/processed", exist_ok=True)

df = pd.read_csv(INPUT_PATH)

# Rename columns (match your dataset)
df = df.rename(columns={
    "dt": "date",
    "AverageTemperature": "avg_temp_c",
    "Country": "country"
})

# Convert date
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["year"] = df["date"].dt.year

# Drop nulls
df = df.dropna(subset=["avg_temp_c", "country", "year"])

# OPTIONAL: add fake columns (for dashboard compatibility)
df["co2_emissions"] = df["avg_temp_c"] * 1.5
df["rainfall_mm"] = df["avg_temp_c"] * 2.0

# Save
df.to_csv(OUTPUT_PATH, index=False)

print("✅ Cleaned data saved:", OUTPUT_PATH)