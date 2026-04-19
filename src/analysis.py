import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.linear_model import LinearRegression


# =========================
# 🔹 EDA FUNCTION
# =========================
def run_eda(df):

    # Sort data (important)
    df = df.sort_values("Date")

    # 1. Temperature over time
    plt.figure()
    plt.plot(df["Date"], df["Temperature"])
    plt.title("Temperature Trend Over Time")
    plt.xlabel("Year")
    plt.ylabel("Temperature")
    plt.show()

    # 2. Rolling Average (smooth trend)
    df["Rolling_Mean"] = df["Temperature"].rolling(window=12).mean()

    plt.figure()
    plt.plot(df["Date"], df["Temperature"], alpha=0.4, label="Actual")
    plt.plot(df["Date"], df["Rolling_Mean"], label="Rolling Mean")
    plt.legend()
    plt.title("Smoothed Temperature Trend")
    plt.show()

    # 3. Monthly pattern
    monthly_avg = df.groupby("Month")["Temperature"].mean()

    plt.figure()
    monthly_avg.plot(kind="bar")
    plt.title("Average Temperature by Month")
    plt.xlabel("Month")
    plt.ylabel("Temperature")
    plt.show()

    # 4. Distribution
    plt.figure()
    sns.histplot(df["Temperature"], kde=True)
    plt.title("Temperature Distribution")
    plt.show()


# =========================
# 🔹 TREND ANALYSIS
# =========================
def trend_analysis(df):

    yearly = df.groupby("Year")["Temperature"].mean().reset_index()

    X = yearly["Year"].values.reshape(-1, 1)
    y = yearly["Temperature"].values

    model = LinearRegression()
    model.fit(X, y)

    trend = model.predict(X)
    slope = model.coef_[0]

    print("\n📊 TREND ANALYSIS RESULT")
    print(f"Temperature change per year: {slope:.4f} °C")

    if slope > 0:
        print("📈 Increasing temperature trend (warming)")
    else:
        print("📉 Decreasing temperature trend")

    # Plot
    plt.figure()
    plt.plot(yearly["Year"], yearly["Temperature"], label="Actual")
    plt.plot(yearly["Year"], trend, label="Trend Line")
    plt.legend()
    plt.title("Yearly Temperature Trend")
    plt.xlabel("Year")
    plt.ylabel("Temperature")
    plt.show()


# =========================
# 🔹 ANOMALY DETECTION
# =========================
def detect_anomalies(df):

    mean = df["Temperature"].mean()
    std = df["Temperature"].std()

    df["Z_score"] = (df["Temperature"] - mean) / std

    anomalies = df[df["Z_score"].abs() > 2]

    print("\n⚠️ ANOMALIES DETECTED:")
    print(anomalies[["Date", "Temperature"]].head())

    # Plot anomalies
    plt.figure()
    plt.plot(df["Date"], df["Temperature"], label="Normal")
    plt.scatter(anomalies["Date"], anomalies["Temperature"], label="Anomaly")
    plt.legend()
    plt.title("Anomaly Detection")
    plt.show()