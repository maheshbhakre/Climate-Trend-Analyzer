import pandas as pd
import streamlit as st
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Climate Pro Dashboard", layout="wide")

# ---------------- LOAD DATA ----------------
DATA_PATH = "data/processed/climate_cleaned.csv"

try:
    df = pd.read_csv(DATA_PATH)
except:
    st.error("Run preprocess first.")
    st.stop()

df.columns = df.columns.str.lower()

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Controls")

countries = sorted(df["country"].dropna().unique())
selected_countries = st.sidebar.multiselect(
    "Countries",
    countries,
    default=countries[:5]
)

year_range = st.sidebar.slider(
    "Year Range",
    int(df["year"].min()),
    int(df["year"].max()),
    (int(df["year"].min()), int(df["year"].max()))
)

metric = st.sidebar.selectbox(
    "Metric",
    ["avg_temp_c", "rainfall_mm", "co2_emissions"]
)

# ---------------- FILTER ----------------
filtered_df = df[
    (df["year"] >= year_range[0]) &
    (df["year"] <= year_range[1])
]

if selected_countries:
    filtered_df = filtered_df[
        filtered_df["country"].isin(selected_countries)
    ]

if filtered_df.empty:
    st.warning("No data for selected filters")
    st.stop()

# ---------------- HEADER ----------------
st.title("🌍 Climate Intelligence Dashboard")
st.caption("Advanced analytics on global climate indicators")

# ---------------- KPI SECTION ----------------
k1, k2, k3, k4 = st.columns(4)

avg_val = filtered_df[metric].mean()
max_val = filtered_df[metric].max()
min_val = filtered_df[metric].min()
countries_count = filtered_df["country"].nunique()

k1.metric("Average", f"{avg_val:.2f}")
k2.metric("Maximum", f"{max_val:.2f}")
k3.metric("Minimum", f"{min_val:.2f}")
k4.metric("Countries", countries_count)

# ---------------- TREND ----------------
st.markdown("### 📈 Trend Analysis")

yearly = filtered_df.groupby("year")[metric].mean().reset_index()

fig1 = px.line(
    yearly,
    x="year",
    y=metric,
    markers=True,
    title="Yearly Trend"
)

fig1.update_layout(template="plotly_dark")

st.plotly_chart(fig1, use_container_width=True)

# ---------------- COMPARISON ----------------
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🌍 Top Countries")

    country_df = (
        filtered_df.groupby("country")[metric]
        .mean()
        .reset_index()
        .sort_values(metric, ascending=False)
    )

    fig2 = px.bar(
        country_df.head(10),
        x=metric,
        y="country",
        orientation="h",
        title="Top Performers"
    )

    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.markdown("### 🔥 Distribution")

    fig3 = px.histogram(
        filtered_df,
        x=metric,
        nbins=30,
        title="Data Distribution"
    )

    fig3.update_layout(template="plotly_dark")
    st.plotly_chart(fig3, use_container_width=True)

# ---------------- INSIGHTS ----------------
st.markdown("### 🧠 Insights")

top_country = country_df.iloc[0]["country"]
bottom_country = country_df.iloc[-1]["country"]

st.info(f"""
- 📊 Metric Selected: **{metric}**
- 🌍 Top Country: **{top_country}**
- 📉 Lowest Country: **{bottom_country}**
- 📈 Trend: Check if slope is increasing visually
""")

# ---------------- DATA ----------------
st.markdown("### 📂 Data Preview")
st.dataframe(filtered_df.head(100))

# ---------------- DOWNLOAD ----------------
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download Data",
    csv,
    "climate_filtered.csv",
    "text/csv"
)