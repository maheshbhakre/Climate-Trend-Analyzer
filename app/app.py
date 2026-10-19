"""Premium Streamlit presentation layer for the Climate Intelligence Platform."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.anomaly_engine import generate_anomaly_reports
from src.data_loader import CANONICAL_COLUMNS, DEFAULT_RAW_PATH, load_raw_data
from src.data_validation import generate_reports
from src.forecast_engine import MODEL_NAMES, SUPPORTED_HORIZONS, forecast_risk_score, generate_forecast, generate_forecast_insights, prepare_forecast_series
from src.trend_analysis import ANALYTICS_REPORT_NAMES, annual_temperature_trends, decadal_temperature_trends, generate_analytics_reports, generate_insights, monthly_temperature_trends, rolling_temperature_average

PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "climate_cleaned.csv"
REPORTS_PATH = PROJECT_ROOT / "outputs" / "reports"

st.set_page_config(page_title="Climate Intelligence Platform", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
PLOTLY_TEMPLATE = {"layout": {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#A9B7C8"}, "margin": {"l": 52, "r": 18, "t": 32, "b": 48}, "hoverlabel": {"bgcolor": "#10243A", "font": {"color": "#F4F8FC"}}, "legend": {"bgcolor": "rgba(0,0,0,0)"}, "xaxis": {"gridcolor": "rgba(121,157,184,.14)"}, "yaxis": {"gridcolor": "rgba(121,157,184,.14)"}}}


def inject_theme() -> None:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root{--navy:#07111F;--panel:#0D1D30;--teal:#28E0C2;--cyan:#31C8FF;--purple:#A77BFF;--amber:#FFB85C;--red:#FF6B7A;--muted:#8EA3B8}
    .stApp{background:radial-gradient(circle at 75% -10%,#122949 0,var(--navy) 42%);color:#F4F8FC;font-family:'DM Sans',sans-serif;background-size:160% 160%;animation:ambientShift 18s ease-in-out infinite alternate}
    [data-testid='stHeader']{background:transparent}[data-testid='stSidebar']{background:linear-gradient(180deg,#091827 0%,#07111F 100%);border-right:1px solid #18314A}
    h1,h2,h3{font-family:'Space Grotesk',sans-serif;color:#F4F8FC!important;letter-spacing:-.03em}h1{font-size:2.25rem!important}
    .brand{padding:16px 0 24px}.brand-kicker,.eyebrow{color:var(--teal);font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;font-weight:700}.brand-title{font-family:'Space Grotesk';font-size:1.72rem;line-height:1.08;font-weight:800;margin-top:7px;background:linear-gradient(90deg,#F4F8FC,#31C8FF,#A77BFF,#F4F8FC);background-size:220% auto;-webkit-background-clip:text;background-clip:text;color:transparent;animation:brandShimmer 7s linear infinite}.author-credit{color:#B8C9D9;font-size:.78rem;margin-top:12px;letter-spacing:.03em}.author-credit span{color:#28E0C2;font-weight:700}.author-hero{display:inline-flex;align-items:center;gap:10px;margin-top:14px;padding:9px 16px;border:1px solid rgba(40,224,194,.4);border-radius:999px;background:linear-gradient(90deg,rgba(40,224,194,.15),rgba(49,200,255,.12));box-shadow:0 0 26px rgba(40,224,194,.16)}.author-hero-label{color:#9EB2C5;font-size:.72rem;letter-spacing:.1em;text-transform:uppercase}.author-hero-name{color:#FFFFFF;font-family:'Space Grotesk';font-size:1rem;font-weight:800;letter-spacing:.08em;text-shadow:0 0 16px rgba(40,224,194,.55)}.hero{padding:22px 0 14px}.hero p{color:var(--muted);margin:0;max-width:760px}.hero h1{background:linear-gradient(90deg,#F4F8FC 0%,#31C8FF 48%,#A77BFF 100%);-webkit-background-clip:text;background-clip:text;color:transparent!important;background-size:180% auto;animation:brandShimmer 9s ease-in-out infinite alternate}.glass{background:linear-gradient(145deg,rgba(17,39,61,.88),rgba(9,24,40,.88));border:1px solid rgba(109,157,190,.18);box-shadow:0 16px 40px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.03);border-radius:16px;padding:18px;min-height:116px;transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease;animation:cardRise .7s ease both}.glass:hover{transform:translateY(-4px);border-color:rgba(49,200,255,.5);box-shadow:0 20px 48px rgba(0,0,0,.28),0 0 24px rgba(49,200,255,.12),inset 0 1px 0 rgba(255,255,255,.06)}.metric-label{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em}.metric-value{color:#F4F8FC;font-family:'Space Grotesk';font-size:1.9rem;font-weight:700;margin-top:7px}.metric-foot{color:var(--teal);font-size:.77rem;margin-top:6px}.insight{border-left:3px solid var(--purple);background:linear-gradient(90deg,rgba(167,123,255,.14),rgba(49,200,255,.04));border-radius:0 12px 12px 0;padding:12px 14px;margin:8px 0;color:#DCE6F0;transition:transform .2s ease,background .2s ease}.insight:hover{transform:translateX(4px);background:linear-gradient(90deg,rgba(167,123,255,.22),rgba(49,200,255,.08))}.status{display:inline-block;border-radius:99px;padding:5px 10px;font-size:.72rem;font-weight:700;background:rgba(40,224,194,.12);color:var(--teal);box-shadow:0 0 18px rgba(40,224,194,.18);animation:statusPulse 2.4s ease-in-out infinite}.section{margin:22px 0 10px}.section-title{font-family:'Space Grotesk';font-size:1.05rem;font-weight:700}.section-sub{color:var(--muted);font-size:.82rem;margin-top:2px}.stButton button,.stDownloadButton button{border-radius:10px;border:1px solid #1C6D8A;background:linear-gradient(100deg,#0D3044,#173A55);color:#CDEFFF;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}.stButton button:hover,.stDownloadButton button:hover{border-color:var(--cyan);color:white;transform:translateY(-2px);box-shadow:0 0 20px rgba(49,200,255,.22)}[data-testid='stDataFrame']{border:1px solid rgba(109,157,190,.16);border-radius:12px;overflow:hidden}@keyframes ambientShift{0%{background-position:0% 0%}100%{background-position:100% 35%}}@keyframes brandShimmer{0%{background-position:0% 50%}100%{background-position:200% 50%}}@keyframes cardRise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}@keyframes statusPulse{0%,100%{box-shadow:0 0 12px rgba(40,224,194,.12)}50%{box-shadow:0 0 24px rgba(40,224,194,.35)}}@media(prefers-reduced-motion:reduce){.stApp,.brand-title,.hero h1,.glass,.status{animation:none!important;transition:none!important}.glass:hover{transform:none}.insight:hover{transform:none}}@media(max-width:700px){h1{font-size:1.75rem!important}.metric-value{font-size:1.45rem}.glass{min-height:95px;padding:14px}}
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading validated observations…")
def load_processed(path: str, mtime: float) -> pd.DataFrame:
    del mtime
    return pd.read_csv(path, parse_dates=["date"])


@st.cache_data(show_spinner="Loading source observations…")
def load_source(path: str, mtime: float) -> pd.DataFrame:
    del mtime
    return load_raw_data(path)


@st.cache_data(show_spinner="Loading intelligence reports…")
def load_report(name: str, mtime: float) -> pd.DataFrame:
    del mtime
    dated = {"anomalies", "climate_alerts", "historical_records"}
    return pd.read_csv(REPORTS_PATH / f"{name}.csv", parse_dates=["date"] if name in dated else None)


@st.cache_data(show_spinner="Calculating climate time series…")
def time_series(path: str, mtime: float) -> dict[str, pd.DataFrame]:
    frame = load_processed(path, mtime)
    return {"annual": annual_temperature_trends(frame), "monthly": monthly_temperature_trends(frame), "rolling": rolling_temperature_average(frame), "decadal": decadal_temperature_trends(frame)}


def ensure_reports(raw: pd.DataFrame, clean: pd.DataFrame) -> None:
    names = ["data_quality_report", "data_coverage_report", "schema_validation_report", "data_dictionary"]
    if not all((REPORTS_PATH / f"{name}.csv").is_file() for name in names): generate_reports(raw, clean, REPORTS_PATH)
    if not all((REPORTS_PATH / f"{name}.csv").is_file() for name in ANALYTICS_REPORT_NAMES): generate_analytics_reports(clean, REPORTS_PATH)
    anomaly_names = ["climate_alerts", "country_anomaly_report", "city_anomaly_report"]
    if not all((REPORTS_PATH / f"{name}.csv").is_file() for name in anomaly_names): generate_anomaly_reports(clean, REPORTS_PATH)


def reports(names: list[str]) -> dict[str, pd.DataFrame]:
    return {name: load_report(name, (REPORTS_PATH / f"{name}.csv").stat().st_mtime) for name in names}


def card(label: str, value: str, foot: str = "", accent: str = "teal") -> None:
    color = {"teal":"#28E0C2","purple":"#A77BFF","amber":"#FFB85C","red":"#FF6B7A","cyan":"#31C8FF"}.get(accent, "#28E0C2")
    st.markdown(f'<div class="glass"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-foot" style="color:{color}">{foot}</div></div>', unsafe_allow_html=True)


def section(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="section"><div class="section-title">{title}</div><div class="section-sub">{subtitle}</div></div>', unsafe_allow_html=True)


def chart(fig: go.Figure, height: int = 360) -> None:
    fig.update_layout(template=PLOTLY_TEMPLATE, height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "responsive": True})


def insight(text: str) -> None:
    st.markdown(f'<div class="insight">✦ {text}</div>', unsafe_allow_html=True)


def page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(f'<div class="hero"><div class="eyebrow">{kicker}</div><h1>{title}</h1><p>{description}</p><div class="author-hero"><span class="author-hero-label">Designed & built by</span><span class="author-hero-name">MAHESH BHAKRE</span></div></div>', unsafe_allow_html=True)


def overview(clean: pd.DataFrame, analytics: dict[str, pd.DataFrame], series: dict[str, pd.DataFrame], anomaly: dict[str, pd.DataFrame]) -> None:
    page_header("Climate intelligence / executive brief", "Executive Overview", "A decision-ready view of historical temperature signals, emerging risk, and model-backed outlooks.")
    quality = float(load_report("data_quality_report", (REPORTS_PATH / "data_quality_report.csv").stat().st_mtime).loc[lambda x: x.indicator == "quality_score", "value"].iloc[0])
    stats = analytics["statistical_trend_report"].iloc[0]; alerts = anomaly["climate_alerts"]
    for col, args in zip(st.columns(4), [("Average temperature", f"{clean.avg_temp_c.mean():.1f} °C", "pooled observation mean", "teal"),("Coverage range", f"{clean.date.min():%Y}–{clean.date.max():%Y}", f"{len(clean):,} observations", "cyan"),("Data quality", f"{quality:.1f}/100", "Excellent validation score", "teal"),("Anomaly alerts", f"{len(alerts):,}", f"{(alerts.severity == 'EXTREME').sum():,} extreme", "amber")]):
        with col: card(*args)
    section("Climate intelligence summary", "Signals derived directly from the existing trend, anomaly, forecast, and quality reports.")
    left, right = st.columns([1.35, 1])
    with left:
        annual = series["annual"]; fig = go.Figure(go.Scatter(x=annual.year, y=annual.average_temperature_c, mode="lines", line={"color":"#28E0C2", "width":3}, fill="tozeroy", fillcolor="rgba(40,224,194,.08)", name="Annual mean")); chart(fig, 330)
    with right:
        insight(f"Observed annual mean changed by {float(stats.temperature_change_c):+.2f} °C across the represented period.")
        insight(f"Descriptive warming slope is {float(stats.trend_slope_c_per_decade):+.3f} °C per decade with R² {float(stats.r_squared):.3f}.")
        top_country = analytics["country_anomaly_report"].sort_values("climate_risk_score", ascending=False).iloc[0]; top_city = analytics["city_anomaly_report"].sort_values("climate_risk_score", ascending=False).iloc[0]
        insight(f"Highest modeled risk in the report set: {top_country.country} ({top_country.risk_level}) and {top_city.city}, {top_city.country}.")
    section("Operational status")
    for col, label, value in zip(st.columns(4), ["Analytics pipeline","Forecast artifacts","Alert monitoring","Risk posture"], ["Online","Ready",f"{len(alerts):,} events",str(top_country.risk_level)]):
        with col: card(label, value, "Traceable report artifact", "red" if value == "High" else "teal")


def global_trends(clean: pd.DataFrame, series: dict[str, pd.DataFrame]) -> None:
    page_header("Signal monitoring", "Global Climate Trends", "Explore annual warming, rolling averages, decade shifts, and the distribution of observed temperatures.")
    annual, rolling, decade = series["annual"], series["rolling"], series["decadal"]; tabs = st.tabs(["Trend signal", "Distribution", "Decade lens"])
    with tabs[0]:
        fig = go.Figure(); fig.add_trace(go.Scatter(x=annual.year, y=annual.average_temperature_c, mode="lines", name="Annual mean", line={"color":"#31C8FF","width":2.5})); fig.add_trace(go.Scatter(x=rolling.date, y=rolling.rolling_average_c, mode="lines", name="12-month rolling", line={"color":"#A77BFF","width":2.5})); chart(fig); st.dataframe(annual.tail(20), hide_index=True, use_container_width=True)
    with tabs[1]:
        fig = go.Figure(go.Histogram(x=clean.avg_temp_c, nbinsx=42, marker_color="#28E0C2", opacity=.82)); fig.update_layout(xaxis_title="Average temperature (°C)", yaxis_title="Observations"); chart(fig, 340); pivot = series["monthly"].pivot(index="year", columns="month", values="average_temperature_c"); chart(go.Figure(go.Heatmap(z=pivot, colorscale=[[0,"#223C74"],[.5,"#31C8FF"],[1,"#FFB85C"]], colorbar={"title":"°C"})), 420)
    with tabs[2]: chart(go.Figure(go.Bar(x=decade.decade, y=decade.average_temperature_c, marker_color="#A77BFF", name="Decade mean"))); st.dataframe(decade, hide_index=True, use_container_width=True)


def explorer(clean: pd.DataFrame, analytics: dict[str, pd.DataFrame], location: str) -> None:
    report = analytics["country_trend_report" if location == "Country" else "city_trend_report"]; page_header(f"Location intelligence / {location.lower()}", f"{location} Explorer", f"Compare observed trends, anomalies, forecast signals, and risk for a selected {location.lower()}.")
    if location == "Country": selected = st.selectbox("Country", sorted(report.country.unique())); filtered = clean[clean.country == selected]; trend = annual_temperature_trends(filtered); row = report[report.country == selected].iloc[0]; title = selected
    else:
        country = st.selectbox("Country", sorted(clean.country.unique())); cities = sorted(clean.loc[clean.country == country, "city"].unique()); selected = st.selectbox("City", cities); filtered = clean[(clean.country == country) & (clean.city == selected)]; trend = annual_temperature_trends(filtered); row = report[(report.country == country) & (report.city == selected)].iloc[0]; title = f"{selected}, {country}"
    values = [("Mean temperature",f"{filtered.avg_temp_c.mean():.2f} °C"),("Trend",f"{float(row.get('warming_rate_c_per_decade',row.get('warming_trend_c_per_decade',0))):+.3f} °C/decade"),("Observations",f"{len(filtered):,}"),("Risk score",f"{float(row.get('climate_risk_score',0)):.1f}")]
    for col, (label, value) in zip(st.columns(4), values):
        with col: card(label, value, title, "purple" if label == "Risk score" else "teal")
    chart(go.Figure(go.Scatter(x=trend.year, y=trend.average_temperature_c, mode="lines+markers", line={"color":"#31C8FF","width":3}, name=title))); st.dataframe(pd.DataFrame([row]), hide_index=True, use_container_width=True)


def alerts_page(anomaly: dict[str, pd.DataFrame]) -> None:
    page_header("Signal response / alert operations", "Climate Alert Center", "Filter anomaly events by severity and location to move from signal discovery to action."); alerts = anomaly["climate_alerts"].copy()
    for col,args in zip(st.columns(4), [("Total alerts",f"{len(alerts):,}","All detected events","amber"),("Severe",f"{(alerts.severity == 'SEVERE').sum():,}","Escalated","red"),("Extreme",f"{(alerts.severity == 'EXTREME').sum():,}","Priority response","red"),("Countries",f"{alerts.country.nunique():,}","Affected locations","cyan")]):
        with col: card(*args)
    f1,f2,f3 = st.columns(3); severity = f1.multiselect("Severity", sorted(alerts.severity.unique()), default=sorted(alerts.severity.unique())); country = f2.selectbox("Country", ["All countries"] + sorted(alerts.country.unique())); query = f3.text_input("Search city", placeholder="e.g. Berlin")
    filtered = alerts[alerts.severity.isin(severity)]
    if country != "All countries": filtered = filtered[filtered.country == country]
    if query: filtered = filtered[filtered.city.str.contains(query, case=False, na=False)]
    fig = go.Figure(go.Scatter(x=filtered.date, y=filtered.anomaly_score, mode="markers", marker={"size":7,"color":"#FF6B7A"}, text=filtered.city, hovertemplate="%{text}<br>%{x|%Y-%m-%d}<br>Score %{y:.2f}<extra></extra>")); chart(fig, 320); risk = anomaly["country_anomaly_report"].sort_values("climate_risk_score", ascending=False).head(15); chart(go.Figure(go.Bar(x=risk.climate_risk_score, y=risk.country, orientation="h", marker_color="#FFB85C")), 390); st.dataframe(filtered.head(500), hide_index=True, use_container_width=True)


def forecast_lab(clean: pd.DataFrame) -> None:
    page_header("Model workspace / forward view", "Forecast Lab", "Run a transparent forecast with selectable horizon, model, location, confidence bands, and future risk."); c1,c2,c3,c4 = st.columns(4); forecast_type = c1.radio("Forecast level", ["country", "city"], horizontal=True); country = c2.selectbox("Country", sorted(clean.country.unique())); city = c3.selectbox("City", sorted(clean.loc[clean.country == country, "city"].unique())) if forecast_type == "city" else None; horizon = c4.selectbox("Horizon", SUPPORTED_HORIZONS, format_func=lambda x:f"{x} months"); model = st.selectbox("Model", MODEL_NAMES)
    result = generate_forecast(clean, horizon_months=horizon, forecast_type=forecast_type, country=country, city=city, model_name=model); history = prepare_forecast_series(clean, forecast_type=forecast_type, country=country, city=city); fig = go.Figure(); fig.add_trace(go.Scatter(x=history.date, y=history.avg_temp_c, mode="lines", name="Historical", line={"color":"#31C8FF"})); fig.add_trace(go.Scatter(x=result.date, y=result.forecast_avg_temp_c, mode="lines", name="Forecast", line={"color":"#A77BFF","width":3})); fig.add_trace(go.Scatter(x=result.date.tolist()+result.date.tolist()[::-1], y=result.upper_95_c.tolist()+result.lower_95_c.tolist()[::-1], fill="toself", fillcolor="rgba(167,123,255,.16)", line={"color":"rgba(0,0,0,0)"}, name="95% confidence")); chart(fig, 430)
    risk = forecast_risk_score(result, history.set_index("date")["avg_temp_c"]); values = [("Model used",model),("Forecast mean",f"{result.forecast_avg_temp_c.mean():.2f} °C"),("End temperature",f"{result.forecast_avg_temp_c.iloc[-1]:.2f} °C"),("Future risk",f"{risk.get('future_climate_risk_score',0):.1f}")]
    for col,(label,value) in zip(st.columns(4),values):
        with col: card(label,value,"Selected configuration" if label == "Model used" else risk.get("risk_level","Forward view"),"purple" if label == "Model used" else "teal")
    section("AI forecast insights","Generated from the existing forecast output and model calculations.")
    metric_report = load_report("forecast_metrics", (REPORTS_PATH / "forecast_metrics.csv").stat().st_mtime)
    metric_report = metric_report[metric_report.forecast_type == forecast_type]
    if forecast_type == "country": metric_report = metric_report[metric_report.country == country]
    else: metric_report = metric_report[(metric_report.country == country) & (metric_report.city == city)]
    for text in generate_forecast_insights(result, metric_report, risk): insight(text)


def stats_page(clean: pd.DataFrame, analytics: dict[str, pd.DataFrame]) -> None:
    page_header("Evidence layer / statistical signal", "Statistical Intelligence", "Interpret the trend with slope, fit, correlation, confidence intervals, and explicit methodological caveats."); row = analytics["statistical_trend_report"].iloc[0]
    values = [("Trend slope",f"{float(row.trend_slope_c_per_decade):+.3f} °C/decade"),("R²",f"{float(row.r_squared):.3f}"),("Correlation",f"{float(row.year_temperature_correlation):.3f}"),("Slope 95% CI",f"[{float(row.slope_ci95_lower_c_per_year)*10:.3f}, {float(row.slope_ci95_upper_c_per_year)*10:.3f}]")]
    for col,(label,value) in zip(st.columns(4),values):
        with col: card(label,value,"Descriptive report metric","purple")
    st.dataframe(pd.DataFrame([row]), hide_index=True, use_container_width=True); insight(str(row.interpretation))
    for text in generate_insights(clean, analytics["country_trend_report"], analytics["city_trend_report"], analytics["decade_trend_report"]): insight(text)


def quality_page(clean: pd.DataFrame, raw: pd.DataFrame) -> None:
    page_header("Trust layer / data operations", "Data Quality Center", "Inspect completeness, consistency, coverage, validity, and the evidence behind the quality score."); q = reports(["data_quality_report","data_coverage_report","schema_validation_report"]); score = q["data_quality_report"].query("indicator == 'quality_score'").iloc[0]; card("Data quality score",f"{float(score.value):.1f}/100","Excellent","teal"); st.dataframe(q["data_quality_report"], hide_index=True, use_container_width=True); coverage = q["data_coverage_report"].sort_values("month_coverage_percent"); chart(go.Figure(go.Bar(x=coverage.month_coverage_percent.tail(30), y=coverage.country.tail(30), orientation="h", marker_color="#28E0C2")), 500); st.dataframe(q["schema_validation_report"], hide_index=True, use_container_width=True); st.caption(f"Raw source rows: {len(raw):,}. Validated rows: {len(clean):,}. Quality calculations are unchanged from the existing validation engine.")


def dataset_page(clean: pd.DataFrame, raw: pd.DataFrame) -> None:
    page_header("Evidence layer / provenance", "Dataset Explorer", "Understand the source fields, coverage boundaries, sample records, and exportable validated observations."); st.dataframe(reports(["data_dictionary"])["data_dictionary"], hide_index=True, use_container_width=True); st.subheader("Sample data"); st.dataframe(clean.head(100), hide_index=True, use_container_width=True); st.download_button("Export validated dataset", clean.to_csv(index=False).encode("utf-8"), "climate_validated.csv", "text/csv"); st.caption(f"Source fields: {len(raw.columns)} · Canonical fields: {len(CANONICAL_COLUMNS)} · Coverage: {clean.date.min():%Y-%m-%d} to {clean.date.max():%Y-%m-%d}")


def platform_page() -> None:
    page_header("Platform context", "Platform Information", "A traceable climate intelligence workspace built for fast executive scanning and careful analytical follow-through.")
    for title, body in [("Architecture","Raw CSV → preprocessing → validation → trend, anomaly, forecast, and risk engines → cached report artifacts → Streamlit presentation layer."),("Models","Trend reports use descriptive aggregation and OLS summaries. Forecast outputs use the existing supported model implementations and confidence bands."),("Methodology","Every insight on this dashboard is derived from repository reports. Unweighted city observations are not automatically population-, area-, or globally representative."),("Limitations","The dataset contains average temperature and uncertainty only. Source publisher, licensing, and causal attribution are outside the repository evidence.")]: st.markdown(f'<div class="glass" style="margin:10px 0"><h3>{title}</h3><p style="color:#A9B7C8">{body}</p></div>', unsafe_allow_html=True)


def main() -> None:
    inject_theme()
    if not PROCESSED_PATH.is_file(): st.error("Processed dataset missing. Run preprocess.py first."); st.stop()
    clean = load_processed(str(PROCESSED_PATH), PROCESSED_PATH.stat().st_mtime); raw = load_source(str(DEFAULT_RAW_PATH), DEFAULT_RAW_PATH.stat().st_mtime); ensure_reports(raw, clean); analytics = reports([*ANALYTICS_REPORT_NAMES,"country_anomaly_report","city_anomaly_report"]); series = time_series(str(PROCESSED_PATH), PROCESSED_PATH.stat().st_mtime); anomaly = reports(["climate_alerts","country_anomaly_report","city_anomaly_report"])
    pages = ["Executive Overview","Global Climate Trends","Country Explorer","City Explorer","Climate Alert Center","Forecast Lab","Statistical Intelligence","Data Quality Center","Dataset Explorer","Platform Information"]
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-kicker">AI climate intelligence</div><div class="brand-title">Climate Trend Analyzer</div><div class="author-credit">By <span>MAHESH BHAKRE</span></div><div style="color:#8EA3B8;font-size:.75rem;margin-top:8px">Decision support for a changing planet</div></div>', unsafe_allow_html=True); page = st.radio("Navigate", pages); st.divider(); st.markdown('<span class="status">● SYSTEM ONLINE</span>', unsafe_allow_html=True); st.caption("Phase 5 · Enterprise dashboard")
    if page == "Executive Overview": overview(clean, analytics, series, anomaly)
    elif page == "Global Climate Trends": global_trends(clean, series)
    elif page == "Country Explorer": explorer(clean, analytics, "Country")
    elif page == "City Explorer": explorer(clean, analytics, "City")
    elif page == "Climate Alert Center": alerts_page(anomaly)
    elif page == "Forecast Lab": forecast_lab(clean)
    elif page == "Statistical Intelligence": stats_page(clean, analytics)
    elif page == "Data Quality Center": quality_page(clean, raw)
    elif page == "Dataset Explorer": dataset_page(clean, raw)
    else: platform_page()


if __name__ == "__main__": main()
