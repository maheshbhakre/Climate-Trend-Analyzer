import matplotlib.pyplot as plt
from statsmodels.tsa.arima.model import ARIMA


def forecast_temperature(df):

    # 🔹 Set Date as index
    df = df.set_index("Date")

    # 🔹 Use only Temperature
    data = df["Temperature"]

    # 🔹 Train ARIMA model
    model = ARIMA(data, order=(2,1,2))
    model_fit = model.fit()

    # 🔹 Forecast next 24 months
    forecast = model_fit.forecast(steps=24)

    print("\n🔮 FUTURE TEMPERATURE FORECAST:")
    print(forecast.head())

    # 🔹 Plot
    plt.figure()
    plt.plot(data, label="Historical")
    plt.plot(forecast, label="Forecast")
    plt.legend()
    plt.title("Temperature Forecast")
    plt.show()