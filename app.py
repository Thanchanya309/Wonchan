"""
Thailand Labor Market Analytics Dashboard
Global Cross-filtering Edition

Main features
-------------
1. Years 2561-2568 only.
2. Shared filters across all three tabs.
3. Clicking a year updates the global year filter.
4. The clicked year drills into Q1-Q4.
5. Clicking a region updates all compatible charts.
6. Clicking an age group updates all compatible charts.
7. Full-country map at first; regional detail after selection.
8. Regional comparison charts retain all regions for reselection.
9. Uses actual data only; never averages percentage rates
   to fabricate missing observations.
10. MapLibre GL JS regional map (custom component) with animated
    camera; the clicked region returns to Python as a global filter.
11. Wage / headcount charts drill from yearly to Q1-Q4 of one year.
12. Active-filter bar with per-dimension clear and full reset.
"""

import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Thailand Labor Market Analytics",
    page_icon="🇹🇭",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.styles import get_custom_css
from src.data_loader import get_cached_labor_data, AGE_ORDER

from src.filters import (
    SIDEBAR_KEYS,
    init_filter_state,
    get_current_filters,
    sanitize_filters,
    clear_filter,
    reset_all_filters,
    on_sidebar_change,
    chart_key,
    get_regions_for_year,
    get_quarters_for_year,
)

from src.metrics import (
    get_kpis,
    get_time_series_data,
    get_regional_comparison_data,
    get_demographics_age_data,
    get_area_wage_comparison_data,
    get_wage_period_series,
    get_headcount_period_series,
)
from src.map_component import render_region_map

from src.charts import (
    create_wage_trend_chart,
    create_headcount_trend_chart,
    create_wage_period_chart,
    create_headcount_period_chart,
    create_regional_ranking_chart,
    create_wage_vs_employment_scatter,
    create_dumbbell_wage_chart,
    create_gender_headcount_donut,
    create_age_wage_chart,
    create_youth_unemployment_chart,
    create_demographic_matrix_heatmap,
    create_thailand_map,
)


# ============================================================
# CONSTANTS
# ============================================================

ALL = "ทั้งหมด"
START_YEAR = 2561
END_YEAR = 2568

PINK = "#E83C91"
PURPLE = "#843A7D"
DARK = "#43334C"
GRID = "#F0E8EE"

MAP_FULL_HEIGHT = 610
MAP_SELECTED_HEIGHT = 560

PLOT_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
}

LABELS = {
    "emp_rate": "อัตราการมีงานทำ (%)",
    "unemp_rate": "อัตราการว่างงาน (%)",
    "avg_wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)",
}

REGION_LIST_5 = [
    "กรุงเทพมหานคร",
    "ภาคกลาง",
    "ภาคเหนือ",
    "ภาคตะวันออกเฉียงเหนือ",
    "ภาคใต้",
]

REGION_LIST_7 = REGION_LIST_5 + [
    "ภาคตะวันออก",
    "ภาคใต้ชายแดน",
]


# ============================================================
# CSS
# ============================================================

st.markdown(
    get_custom_css(),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    .dashboard-section-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #552B65;
        margin: 18px 0 10px;
    }

    .filter-banner {
        background: #FBEAF5;
        border: 1px solid #EEC8DF;
        border-radius: 12px;
        padding: 10px 15px;
        color: #713574;
        font-weight: 600;
        margin: 10px 0;
    }

    .region-head {
        background: linear-gradient(
            110deg, #FCE4F2, #F0DFF4
        );
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
        color: #552B65;
    }

    .region-head h3 {
        margin: 0;
        font-size: 1.4rem;
        color: #552B65;
    }

    .detail-metric {
        background: #FFF9FD;
        border: 1px solid #EED8E7;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }

    .detail-label {
        color: #856985;
        font-size: 0.86rem;
        font-weight: 600;
    }

    .detail-value {
        color: #713574;
        font-size: 1.6rem;
        font-weight: 800;
        margin-top: 4px;
    }

    .age-insight {
        background: linear-gradient(
            110deg, #FFF3FA, #F8E4F2
        );
        border: 1px solid #F1CDDF;
        border-radius: 14px;
        padding: 14px;
        margin: 8px 0 12px;
    }

    .age-insight .label {
        color: #795D78;
        font-size: 0.85rem;
    }

    .age-insight .value {
        color: #D52D86;
        font-size: 1.5rem;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# Visual-only design layer: no changes to shared filters, data or chart events.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
:root { --labor-bg:#F5F1FA; --labor-text:#43334C; --labor-pink:#E83C91; --labor-purple:#843A7D; }
html, body, .stApp, .stApp *, [data-testid="stSidebar"] * {
  font-family:'Prompt',sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:#F5F1FA !important;
  color:#43334C;
}
.block-container { padding-top:1.25rem !important; }
section[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#35243F 0%,#281B33 100%) !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
  border-radius:12px !important;
  background:#FCF5FC !important;
}
.sidebar-brand-card {
  background:linear-gradient(135deg,#70376F,#C73A89) !important;
  border-radius:20px !important;
  box-shadow:0 10px 24px rgba(232,60,145,.17) !important;
}
.main-header-banner {
  background:linear-gradient(115deg,#FFF9FE 0%,#F9E6F5 63%,#EDE0F7 100%) !important;
  border:1px solid #E9D6EB !important;
  border-radius:22px !important;
  box-shadow:0 7px 28px rgba(67,51,76,.055) !important;
  padding:22px 26px !important;
}
.main-header-title {font-weight:700 !important;letter-spacing:-.025em;color:#35243F !important;}
.main-header-subtitle {color:#77667F !important;}
.kpi-card {
  border-radius:20px !important;
  padding:21px 22px !important;
  min-height:134px;
  box-shadow:0 10px 25px rgba(76,37,84,.12) !important;
}
.kpi-card-1 {background:linear-gradient(135deg,#EE398F,#C71B76) !important;}
.kpi-card-2 {background:linear-gradient(135deg,#743578,#54255B) !important;}
.kpi-card-3 {background:linear-gradient(135deg,#9B4593,#743475) !important;}
.kpi-card-4 {background:linear-gradient(135deg,#65466F,#3D2B49) !important;}
.kpi-title {font-size:.95rem !important;font-weight:600 !important;letter-spacing:0 !important;text-transform:none !important;}
.kpi-value {font-size:2.2rem !important;font-weight:700 !important;}
.kpi-subtext {opacity:.9 !important;}
/* Native Streamlit bordered chart cards */
[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] ,
[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-radius:19px;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius:19px !important;
  border-color:#E6DCEB !important;
  background:rgba(255,255,255,.96) !important;
  box-shadow:0 5px 20px rgba(67,51,76,.045);
}
/* Chart card headings: strong contrast and hierarchy */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> strong) {
  color:#472B57 !important;
  font-size:1.13rem !important;
  font-weight:700 !important;
  line-height:1.55 !important;
  margin-bottom:3px !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p > strong {
  color:#472B57 !important;
  font-weight:700 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] {
  color:#82718C !important;
  font-size:.83rem !important;
}
.dashboard-section-title {
  color:#4B295A !important;
  font-weight:700 !important;
  font-size:1.48rem !important;
  margin-top:26px !important;
  margin-bottom:13px !important;
}
.stTabs [data-baseweb="tab-list"] {gap:8px !important;border-bottom:1px solid #E5D9E9 !important;}
.stTabs [data-baseweb="tab"] {
  border-radius:12px 12px 0 0 !important;
  font-size:.97rem !important;
  font-weight:600 !important;
  padding:12px 18px !important;
}
.stTabs [aria-selected="true"] {
  background:#E83C91 !important;
  color:white !important;
}
.stButton button {border-radius:12px !important;font-weight:600 !important;}
[data-testid="stPlotlyChart"] {border-radius:16px;overflow:hidden;}
</style>
""", unsafe_allow_html=True)

# Clean floating white cards: applied after the existing theme to win CSS cascade.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
:root{--page:#F5F1FA;--ink:#35243F;--accent:#E83C91;}
html,body,.stApp,.stApp *,[data-testid="stSidebar"] *{
 font-family:'Prompt',sans-serif !important;
}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],
[data-testid="stMainBlockContainer"]{background-color:var(--page) !important;}
/* Borders are applied by the inner block in several Streamlit releases. */
div[data-testid="stVerticalBlockBorderWrapper"]{
 background:#fff !important;
 border:1px solid rgba(112,77,125,.10) !important;
 border-radius:23px !important;
 box-shadow:0 9px 24px rgba(54,38,66,.09),0 2px 5px rgba(54,38,66,.035) !important;
 overflow:hidden !important;
 padding:8px 10px !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div,
div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] > div > div > div[data-testid="stVerticalBlock"]{
 background:#fff !important;
 border-radius:20px !important;
}
/* Fallback selectors for Streamlit versions that use a border via data attributes. */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] > div[data-testid="stPlotlyChart"]){
 background-color:#fff;
}
[data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"],
[data-testid="stArrowVegaLiteChart"]{background-color:#fff !important;border-radius:16px !important;}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p:has(>strong){
 color:var(--ink) !important;
 font-size:1.19rem !important;
 line-height:1.55 !important;
 font-weight:700 !important;
 letter-spacing:-.015em;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p >strong{
 color:var(--ink) !important;font-weight:700 !important;
}
/* Visual hierarchy: pink marker ahead of each graph heading. */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p:has(>strong)::before{
 content:"";display:inline-block;width:6px;height:23px;
 vertical-align:-5px;margin-right:11px;border-radius:9px;
 background:linear-gradient(180deg,#F56CB1,#E83C91);
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"]{
 color:#85798E !important;font-size:.84rem !important;
}
.dashboard-section-title{font-size:1.55rem !important;color:var(--ink) !important;font-weight:700 !important;}
.stTabs [data-baseweb="tab"]{font-weight:600 !important;}
/* Preserve the high-contrast KPI cards and dark sidebar. */
.kpi-card{box-shadow:0 12px 27px rgba(64,33,81,.16) !important;}
/* Chart backgrounds stay white even when the page is lavender. */
.js-plotly-plot,.plot-container,.svg-container{background-color:transparent !important;}
@media(max-width:760px){div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px !important;padding:3px !important;}}
</style>
""", unsafe_allow_html=True)

# Final presentation layer: native Streamlit containers are the white card.
# CSS-only override; all chart and filter callbacks below stay unchanged.
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');
:root { --page-lavender:#F5F1FA; --card-white:#FFFFFF; --ink-dark:#35243F; --pink-accent:#E83C91; }
html, body, .stApp, .stApp * { font-family:'Prompt',sans-serif !important; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stMainBlockContainer"] { background-color:var(--page-lavender) !important; }

/* Apply the white surface to the ACTUAL native bordered-container wrapper,
   rather than making a white rectangle only around the Plotly canvas. */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stVerticalBlockBorderWrapper"]:first-child,
[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] > div > div > div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--card-white) !important;
  background-color:var(--card-white) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border:0 !important;
  border-width:0 !important;
  outline:none !important;
  border-radius:23px !important;
  box-shadow:0 12px 32px rgba(52,36,63,.10),0 2px 6px rgba(52,36,63,.035) !important;
  overflow:hidden !important;
  padding:13px 16px 16px !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] > div > div {
  border-color:transparent !important;
  border-radius:20px !important;
}
/* Streamlit can draw a native outline on an inner vertical block. */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
  background:var(--card-white) !important;
  border-color:transparent !important;
}

/* Promote the first chart heading of each card, not arbitrary bold copy. */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> strong),
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> b) {
  font-family:'Prompt',sans-serif !important;
  font-size:1.28rem !important;
  font-weight:700 !important;
  line-height:1.52 !important;
  color:var(--ink-dark) !important;
  margin:1px 0 5px !important;
  letter-spacing:-.015em !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p > strong,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p > b {
  font-weight:700 !important;
  color:var(--ink-dark) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> strong)::before,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> b)::before {
  content:""; display:inline-block; width:6px; height:25px;
  background:linear-gradient(180deg,#FF71B9,var(--pink-accent));
  border-radius:10px; margin-right:12px; vertical-align:-6px;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"],
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stCaptionContainer"] p {
  font-size:.91rem !important;
  color:#81758C !important;
  line-height:1.6 !important;
}
.dashboard-section-title {font-size:1.68rem !important;font-weight:700 !important;color:var(--ink-dark) !important;}
/* One seamless white card; the Plotly canvas must not appear like a second card. */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stPlotlyChart"],
[data-testid="stVerticalBlockBorderWrapper"] .js-plotly-plot,
[data-testid="stVerticalBlockBorderWrapper"] .plot-container,
[data-testid="stVerticalBlockBorderWrapper"] .svg-container {
  background:transparent !important; background-color:transparent !important;
  border:0 !important;box-shadow:none !important;
}
/* MapLibre iframe: keep its interactions / sizing untouched. */
[data-testid="stVerticalBlockBorderWrapper"] iframe {border:0 !important;}
@media(max-width:800px){
 [data-testid="stVerticalBlockBorderWrapper"]{padding:10px 11px 12px !important;border-radius:18px !important;}
 [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] > p:has(> strong){font-size:1.08rem !important;}
}
</style>
""", unsafe_allow_html=True)

# Named chart cards avoid Streamlit's version-dependent native border wrapper.
# Each key generates a stable st-key-labor_card_* CSS class.
st.markdown(r"""
<style>
/* Target the named containers themselves, not the inner Plotly canvas. */
[class*="st-key-labor_card_"] {
  background: #FFFFFF !important;
  background-color: #FFFFFF !important;
  border: 0 !important;
  outline: none !important;
  border-radius: 23px !important;
  box-shadow: 0 11px 30px rgba(52,36,63,.11), 0 2px 6px rgba(52,36,63,.025) !important;
  padding: 20px 22px 22px !important;
}
/* Do not paint a separate white rectangle inside the outer card. */
[class*="st-key-labor_card_"] [data-testid="stPlotlyChart"],
[class*="st-key-labor_card_"] .js-plotly-plot,
[class*="st-key-labor_card_"] .plot-container,
[class*="st-key-labor_card_"] .svg-container {
  box-shadow: none !important;
  border: 0 !important;
  background: transparent !important;
}
/* Style only titles rendered as the first bold Markdown paragraph in a chart card. */
[class*="st-key-labor_card_"] [data-testid="stMarkdownContainer"] > p:has(>strong) {
  color:#35243F !important;
  font:700 1.35rem/1.55 'Prompt',sans-serif !important;
  letter-spacing:-.015em !important;
  margin:1px 0 6px !important;
}
[class*="st-key-labor_card_"] [data-testid="stMarkdownContainer"] > p:has(>strong)::before {
  content:"";
  display:inline-block;
  background:linear-gradient(180deg,#FF6AB2,#E83C91);
  border-radius:9px;
  width:6px;
  height:27px;
  vertical-align:-7px;
  margin-right:12px;
}
[class*="st-key-labor_card_"] [data-testid="stCaptionContainer"],
[class*="st-key-labor_card_"] [data-testid="stCaptionContainer"] p {
  font:400 .92rem/1.65 'Prompt',sans-serif !important;
  color:#7F7188 !important;
}
@media(max-width:760px) {
 [class*="st-key-labor_card_"] {border-radius:18px !important;padding:14px 14px 16px !important;}
 [class*="st-key-labor_card_"] [data-testid="stMarkdownContainer"] > p:has(>strong) {font-size:1.12rem !important;}
}
</style>
""", unsafe_allow_html=True)

# UI redesign overrides only; widgets, callbacks and calculations are unchanged.
st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700;800&display=swap');
:root{--lavender-page:#F5F1FA;--ink-main:#35243F;--pink-main:#E83C91;}
/* Header */
.labor-hero{position:relative;display:flex;align-items:center;gap:22px;min-height:164px;padding:29px 34px;background:linear-gradient(111deg,#FFF5FD 0%,#FAE4F4 54%,#EEE1FC 100%);border:1px solid #F0D8EC;border-radius:26px;box-shadow:0 12px 30px rgba(80,39,86,.09);overflow:hidden;margin:6px 0 20px}
.labor-hero-icon{width:72px;height:72px;display:flex;align-items:center;justify-content:center;flex:none;border-radius:22px;background:rgba(255,255,255,.8);color:#D92B8C;font-size:44px;font-weight:800;box-shadow:0 8px 24px rgba(198,67,145,.13)}
.labor-hero-copy{position:relative;z-index:2;min-width:0;flex:1}
.labor-hero-copy h1{color:#312044 !important;font-family:'Prompt',sans-serif !important;font-size:clamp(1.65rem,2.65vw,2.65rem)!important;line-height:1.38!important;font-weight:800!important;letter-spacing:-.025em!important;margin:0 0 8px!important;overflow-wrap:anywhere}
.labor-hero-copy p{color:#76637E!important;font-size:1rem!important;line-height:1.6!important;margin:0!important}
.labor-hero-period{z-index:2;display:flex;flex-direction:column;gap:2px;white-space:nowrap;border-radius:19px;padding:12px 20px;background:rgba(255,255,255,.75);box-shadow:0 6px 18px rgba(90,43,100,.06);color:#76637E;font-size:.78rem}
.labor-hero-period strong{color:#D92B8C;font-size:1.05rem}
.labor-hero-art{position:absolute;right:-8px;bottom:-10px;height:105px;display:flex;gap:8px;align-items:flex-end;opacity:.27;pointer-events:none}
.labor-hero-art i{width:20px;background:linear-gradient(180deg,#E83C91,#833A9A);border-radius:7px 7px 0 0}
.labor-hero-art i:nth-child(1){height:23%}.labor-hero-art i:nth-child(2){height:37%}.labor-hero-art i:nth-child(3){height:55%}.labor-hero-art i:nth-child(4){height:75%}.labor-hero-art i:nth-child(5){height:98%}
/* Round, spacious tabs; only appearance changes */
.stTabs [data-baseweb="tab-list"]{display:flex!important;gap:8px!important;align-items:stretch!important;padding:8px!important;border:1px solid #EFE4F2!important;border-radius:20px!important;background:#FFFFFF!important;box-shadow:0 8px 24px rgba(62,35,79,.06)!important;margin-bottom:18px!important;overflow-x:auto}
.stTabs [data-baseweb="tab"]{flex:0 0 auto!important;height:auto!important;min-height:49px!important;border:0!important;border-radius:14px!important;padding:12px 20px!important;background:transparent!important;color:#4D3B5B!important;white-space:nowrap!important;font:600 .96rem/1.45 'Prompt',sans-serif!important}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(110deg,#F23A9D,#D32A88)!important;color:#FFFFFF!important;box-shadow:0 6px 16px rgba(228,45,137,.22)!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important}
.stTabs [data-baseweb="tab"] p{color:inherit!important;font:inherit!important;margin:0!important;line-height:1.45!important}
/* White chart cards, no additional painted Plotly box */
[class*="st-key-labor_card_"]{background:#FFFFFF!important;border:1px solid #F1E8F3!important;border-radius:23px!important;box-shadow:0 11px 27px rgba(58,32,70,.095)!important;padding:19px 23px 22px!important}
[class*="st-key-labor_card_"] [data-testid="stPlotlyChart"], [class*="st-key-labor_card_"] .js-plotly-plot{background:transparent!important;box-shadow:none!important}
[class*="st-key-labor_card_"] [data-testid="stMarkdownContainer"] > p:has(>strong){font:700 1.25rem/1.55 'Prompt',sans-serif!important;color:#35243F!important;margin:0 0 7px!important}
/* Selected region information */
.region-head{background:linear-gradient(115deg,#FFF3FB,#F3DFF7)!important;border:1px solid #F0D4EC!important;border-radius:19px!important;padding:19px 20px!important;margin:0 0 15px!important;box-shadow:none!important}
.region-head-kicker{font-size:.8rem;font-weight:600;color:#B43B91;margin-bottom:4px}
.region-head h3{font:800 1.65rem/1.35 'Prompt',sans-serif!important;color:#3F2450!important;margin:0 0 3px!important}
.region-head-period{color:#806887!important;font-size:.86rem!important;line-height:1.5!important}
.detail-metric{display:grid!important;grid-template-columns:1fr auto;gap:1px 8px;align-items:baseline;background:#FFFFFF!important;border:1px solid #F0DDEC!important;border-radius:16px!important;padding:14px 17px!important;margin:0 0 10px!important;box-shadow:0 4px 14px rgba(80,40,89,.045)!important;min-width:0}
.detail-label{grid-column:1/-1;color:#806687!important;font:600 .86rem/1.45 'Prompt',sans-serif!important;margin:0 0 3px!important}
.detail-value{min-width:0;overflow-wrap:anywhere;color:#572661!important;font:800 1.58rem/1.35 'Prompt',sans-serif!important;margin:0!important}
.detail-unit{color:#907F97;font:500 .76rem/1.5 'Prompt',sans-serif;white-space:nowrap}
/* Sources expander: restore proper layout and prevent title overlap */
[data-testid="stExpander"]{border:1px solid #EADBEF!important;border-radius:16px!important;background:#FFFFFF!important;overflow:hidden!important;margin:12px 0 20px!important}
[data-testid="stExpander"] details, [data-testid="stExpander"] summary{min-height:unset!important;height:auto!important;line-height:1.5!important}
[data-testid="stExpander"] summary{display:flex!important;align-items:center!important;gap:10px!important;padding:15px 18px!important}
[data-testid="stExpander"] summary p,[data-testid="stExpander"] summary span{font:600 .98rem/1.55 'Prompt',sans-serif!important;white-space:normal!important;position:static!important;transform:none!important;letter-spacing:normal!important}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{padding:10px 22px 19px!important}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li{line-height:1.75!important;margin:4px 0!important}
@media(max-width:900px){.labor-hero{flex-wrap:wrap;padding:23px;gap:15px}.labor-hero-period{margin-left:0}.labor-hero-copy h1{font-size:1.7rem!important}}
@media(max-width:620px){.labor-hero-icon{height:52px;width:52px;font-size:29px;border-radius:15px}.labor-hero-period{width:100%}.stTabs [data-baseweb="tab"]{padding:10px 12px!important;font-size:.82rem!important}.detail-value{font-size:1.35rem!important}}
</style>
""", unsafe_allow_html=True)

# Final UI-only refinement: dark cover, readable tabs, robust notes and regional cards.
st.markdown(r"""
<style>
/* Header: selected dark plum -> magenta gradient. Existing text stays untouched. */
.labor-hero {
 background:linear-gradient(112deg,#291B3D 0%,#603066 55%,#B52E83 100%)!important;
 border:1px solid rgba(255,255,255,.12)!important;
 box-shadow:0 18px 38px rgba(50,24,63,.20)!important;
 min-height:184px!important;padding:31px 36px!important;isolation:isolate;
}
.labor-hero::after{content:"";position:absolute;right:-75px;top:-105px;width:420px;height:350px;border-radius:50%;background:radial-gradient(circle,rgba(255,190,229,.24),transparent 68%);z-index:0;pointer-events:none}
.labor-hero-copy h1{color:#FFFFFF!important;font-weight:700!important;letter-spacing:-.018em!important;font-size:clamp(1.6rem,2.45vw,2.55rem)!important;text-shadow:0 2px 5px rgba(36,10,42,.14)}
.labor-hero-copy p{color:#F5DDEA!important;font-weight:400!important;line-height:1.65!important}
.labor-hero-icon{background:rgba(255,255,255,.13)!important;color:#FFFFFF!important;border:1px solid rgba(255,255,255,.22)!important;box-shadow:0 8px 20px rgba(20,6,32,.14)!important}
.labor-hero-period{background:rgba(255,255,255,.14)!important;color:#F9E6F4!important;border:1px solid rgba(255,255,255,.25)!important;box-shadow:none!important;backdrop-filter:blur(7px)}
.labor-hero-period strong{color:#FFFFFF!important}
.labor-hero-art{opacity:.3!important;z-index:0}
.labor-hero-art i{background:linear-gradient(180deg,#FFD3F0,#E83C91)!important}
/* Tabs: stable white surface and prominent pink selected state. */
.stTabs [data-baseweb="tab-list"]{background:#FFFFFF!important;padding:9px!important;border:0!important;border-radius:20px!important;gap:10px!important;box-shadow:0 8px 22px rgba(57,34,71,.09)!important;margin:5px 0 22px!important}
.stTabs [data-baseweb="tab"]{border-radius:13px!important;padding:13px 20px!important;min-height:53px!important;color:#45314F!important;font-weight:600!important;line-height:1.55!important}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(120deg,#F03795,#C72C8F)!important;color:#FFF!important;box-shadow:0 5px 13px rgba(202,43,133,.22)!important}
.stTabs [data-baseweb="tab"] p{font:inherit!important;color:inherit!important;white-space:nowrap!important}
/* White floating map and chart cards, without nested surface effects. */
[class*="st-key-labor_card_"]{background:#FFF!important;border:0!important;box-shadow:0 12px 30px rgba(46,28,58,.10)!important;border-radius:23px!important}
[class*="st-key-labor_card_"] [data-testid="stPlotlyChart"]{background:transparent!important}
/* Regional panel: make the existing four values visibly distinct; no data changes. */
.region-head{background:linear-gradient(115deg,#FDEBF7,#F0DDF7)!important;border:0!important;border-radius:19px!important;padding:19px 20px!important;box-shadow:0 5px 14px rgba(110,42,116,.07)!important}
.region-head h3{font-size:1.78rem!important;color:#3B214B!important}
.detail-metric{border:1px solid #F0DFED!important;border-radius:17px!important;padding:17px 18px!important;box-shadow:0 7px 19px rgba(58,25,73,.065)!important;margin-bottom:12px!important;background:linear-gradient(115deg,#FFFFFF,#FFFAFD)!important}
.detail-label{font-size:.95rem!important;color:#785B80!important}
.detail-value{font-size:1.85rem!important;font-weight:700!important;color:#562363!important}
.detail-unit{font-size:.82rem!important}
/* Notes expander: isolate text layout from chart heading pseudo markers. */
[data-testid="stExpander"]{background:#FFFFFF!important;border:0!important;border-radius:17px!important;box-shadow:0 9px 25px rgba(59,37,74,.085)!important;overflow:hidden!important}
[data-testid="stExpander"] summary{padding:15px 18px!important;min-height:56px!important;display:flex!important;align-items:center!important;gap:11px!important;position:relative!important}
[data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
[data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p{display:block!important;white-space:normal!important;line-height:1.65!important;font-size:1rem!important;font-weight:600!important;color:#422D51!important;margin:0!important;position:static!important;text-indent:0!important}
[data-testid="stExpander"] summary p::before,
[data-testid="stExpander"] summary p::after,
[data-testid="stExpander"] summary strong::before{content:none!important;display:none!important}
[data-testid="stExpander"] [data-testid="stExpanderDetails"]{padding:8px 22px 22px!important}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] p,
[data-testid="stExpander"] [data-testid="stExpanderDetails"] li{line-height:1.8!important;letter-spacing:normal!important}
@media(max-width:850px){.labor-hero{padding:23px!important;flex-wrap:wrap!important}.labor-hero-period{margin-left:0!important}.stTabs [data-baseweb="tab"]{padding:11px 12px!important;font-size:.85rem!important}}
</style>
""", unsafe_allow_html=True)

# Dedicated final UI styles: targets actual tab DOM and safe standalone source section.
st.markdown(r"""
<style>
/* Active tabs: remove old underline/pink blocks and create actual pill surfaces */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
  display:flex!important;align-items:center!important;gap:12px!important;padding:11px!important;
  background:#FFFFFF!important;border:0!important;border-radius:21px!important;
  box-shadow:0 12px 28px rgba(49,26,65,.11)!important;margin:10px 0 23px!important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] {
  display:flex!important;justify-content:center!important;align-items:center!important;
  padding:14px 22px!important;min-height:56px!important;min-width:170px!important;
  background:#F8F4FA!important;color:#51395F!important;border-radius:15px!important;
  border:1px solid #EFE5F1!important;box-shadow:none!important;white-space:nowrap!important;
  font-family:'Prompt',sans-serif!important;font-weight:600!important;font-size:.97rem!important;
}
div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
  background:linear-gradient(115deg,#E83C91,#B52E83)!important;color:white!important;
  box-shadow:0 8px 17px rgba(210,48,141,.27)!important;border-color:transparent!important;
}
div[data-testid="stTabs"] [data-baseweb="tab"] p,
div[data-testid="stTabs"] [data-baseweb="tab"] span {color:inherit!important;font:inherit!important;line-height:1.5!important}
div[data-testid="stTabs"] [data-baseweb="tab-highlight"],
div[data-testid="stTabs"] [data-baseweb="tab-border"] {display:none!important}
/* A single predictable white notes card, completely independent of Streamlit expander */
.labor-notes {display:block;position:relative;clear:both;margin:28px 0 40px;
  background:#FFFFFF;border:1px solid #F0E7F3;border-radius:22px;
  box-shadow:0 12px 28px rgba(52,32,68,.10);overflow:hidden;color:#35243F;}
.labor-notes>summary {list-style:none;cursor:pointer;display:flex!important;align-items:center;
  gap:13px;min-height:66px;padding:18px 24px!important;font:700 1.14rem/1.65 'Prompt',sans-serif!important;
  white-space:normal!important;color:#392545!important;}
.labor-notes>summary::-webkit-details-marker{display:none}
.labor-notes-icon{display:grid;place-items:center;flex:none;width:35px;height:35px;border-radius:12px;
  background:#FCE0F0;color:#D62F8A;font-size:1.2rem}
.labor-notes-chev{margin-left:auto;font-size:1.45rem;color:#9C73A4;transition:transform .2s}
.labor-notes[open] .labor-notes-chev{transform:rotate(180deg)}
.labor-notes-body{padding:3px 28px 26px;border-top:1px solid #F4EAF6;font:400 .94rem/1.85 'Prompt',sans-serif!important}
.labor-notes-body p{margin:17px 0 9px!important}
.labor-notes-body ul{padding-left:24px!important;margin:8px 0!important}
.labor-notes-body li{padding:3px 0!important;line-height:1.85!important}
@media(max-width:760px){div[data-testid="stTabs"] [data-baseweb="tab"]{min-width:140px!important;padding:11px 12px!important;font-size:.82rem!important}.labor-notes>summary{padding:15px!important}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# INITIAL STATE
# ============================================================

init_filter_state()

if "filters" not in st.session_state:
    st.session_state["filters"] = {}

if "trend_drill_year" not in st.session_state:
    st.session_state["trend_drill_year"] = None

if "crossfilter_version" not in st.session_state:
    st.session_state["crossfilter_version"] = 0

if "trend_view_version" not in st.session_state:
    st.session_state["trend_view_version"] = 0

if "_pending_chart_filter" not in st.session_state:
    st.session_state["_pending_chart_filter"] = None


# ============================================================
# SHARED FILTER ENGINE
# ============================================================

def chart_version():
    """
    One version number for every chart key.
    It changes whenever ANY filter changes (sidebar, chart click, map
    click, chip, reset) so no chart keeps a stale selection.
    """
    return (
        st.session_state.get("crossfilter_version", 0)
        + st.session_state.get("chart_nonce", 0)
    )


def _normalise_selected_value(dimension, value):
    """Convert Plotly-selected values to sidebar types."""
    if value is None:
        return None

    if dimension in ("year", "quarter"):
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    return str(value)


def _read_selected_point(event):
    """Read a Plotly selected point safely."""
    try:
        if isinstance(event, dict):
            points = event.get(
                "selection", {}
            ).get("points", [])
        else:
            points = event.selection.points
    except (AttributeError, KeyError, TypeError):
        return None

    if not points:
        return None

    return points[0]


def _value_from_point(point, dimension):
    """
    Obtain the actual filter value from a plotted point.

    Most existing charts use customdata:
    - Region charts: customdata = region
    - Age charts: customdata = age group
    - Quarterly bars: customdata = quarter

    For geographic charts, location is a fallback.
    """
    custom = point.get("customdata")

    if isinstance(custom, (list, tuple, np.ndarray)):
        value = custom[0] if len(custom) else None
    else:
        value = custom

    if value is not None:
        return value

    if dimension == "region":
        return (
            point.get("location")
            or point.get("y")
        )

    if dimension == "age_group":
        return (
            point.get("y")
            or point.get("x")
        )

    if dimension == "quarter":
        return point.get("x")

    if dimension == "year":
        return point.get("x")

    return None


def queue_chart_filter(
    chart_widget_key,
    dimension,
    valid_values=None,
    drill_down=False,
):
    """
    Runs as a Plotly on_select callback.

    IMPORTANT:
    The chart click is queued first, then applied
    before sidebar widgets are constructed on rerun.
    This avoids modifying an already-created widget.
    """
    event = st.session_state.get(chart_widget_key)
    point = _read_selected_point(event)

    if point is None:
        return

    raw_value = _value_from_point(
        point, dimension
    )
    value = _normalise_selected_value(
        dimension, raw_value
    )

    if value is None:
        return

    if valid_values is not None:
        allowed = {
            _normalise_selected_value(
                dimension, item
            )
            for item in valid_values
        }

        if value not in allowed:
            return

    st.session_state["_pending_chart_filter"] = {
        "dimension": dimension,
        "value": value,
        "drill_down": bool(drill_down),
    }


def apply_pending_chart_filter():
    """
    Apply a chart selection BEFORE rendering the sidebar.

    Both the shared filter dictionary and sidebar widget
    state are synchronized here.
    """
    pending = st.session_state.get(
        "_pending_chart_filter"
    )

    if pending is None:
        return

    st.session_state["_pending_chart_filter"] = None

    dimension = pending["dimension"]
    value = pending["value"]

    current = dict(
        st.session_state.get("filters", {})
    )

    current[dimension] = value

    # Switching the year should not preserve a quarter
    # that might not exist in the destination year.
    if dimension == "year":
        current["quarter"] = ALL

    st.session_state["filters"] = current

    # Mirror selections into sidebar widget keys.
    sidebar_key = SIDEBAR_KEYS.get(dimension)

    if sidebar_key is not None:
        st.session_state[sidebar_key] = value

    if dimension == "year":
        quarter_key = SIDEBAR_KEYS.get("quarter")
        if quarter_key is not None:
            st.session_state[quarter_key] = ALL

    # The clicked year both filters the dashboard
    # AND switches the trend to quarterly mode.
    if dimension == "year" and pending["drill_down"]:
        st.session_state["trend_drill_year"] = value

    # A fresh chart key clears stale Plotly selections.
    st.session_state["crossfilter_version"] += 1


def reset_trend_view():
    """
    Return the trend to annual view.
    KEEP the currently selected global year.
    """
    st.session_state["trend_drill_year"] = None
    st.session_state["trend_view_version"] += 1
    st.session_state["crossfilter_version"] += 1


def reset_dashboard_view():
    """
    Reset the chart drill-down and sidebar filters together.
    """
    reset_all_filters()
    st.session_state["trend_drill_year"] = None
    st.session_state["trend_view_version"] += 1
    st.session_state["crossfilter_version"] += 1
    st.session_state["_pending_chart_filter"] = None


def on_sidebar_year_change():
    """Year chosen in the sidebar should drill the same as clicking the year chart."""
    on_sidebar_change("year")
    new_year = st.session_state[SIDEBAR_KEYS["year"]]
    st.session_state["trend_drill_year"] = None if new_year == ALL else int(new_year)
    st.session_state["trend_view_version"] += 1
    # Reset stale quarter when changing year; leave other compatible filters.
    updated = dict(st.session_state.get("filters", {}))
    updated["quarter"] = ALL
    st.session_state["filters"] = updated
    st.session_state[SIDEBAR_KEYS["quarter"]] = ALL
    st.session_state["crossfilter_version"] += 1


# Apply any incoming chart click first.
apply_pending_chart_filter()


# ============================================================
# GENERAL UTILITIES
# ============================================================

def plot_chart(fig, **kwargs):
    if fig is not None:
        fig.update_layout(font=dict(family="Prompt, sans-serif"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return st.plotly_chart(
        fig,
        use_container_width=True,
        config=PLOT_CONFIG,
        **kwargs,
    )


def safe_number(value):
    try:
        value = float(value)
        return (
            value
            if np.isfinite(value)
            else None
        )
    except (TypeError, ValueError):
        return None


def format_number(value, suffix="", decimals=2):
    value = safe_number(value)

    if value is None:
        return "—"

    return f"{value:,.{decimals}f}{suffix}"


def filter_frame(frame, metric):
    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or metric not in frame.columns
    ):
        return pd.DataFrame(
            columns=["region", metric]
        )

    result = frame.copy()
    result[metric] = pd.to_numeric(
        result[metric],
        errors="coerce",
    )
    return result.dropna(subset=[metric])


def render_interactive_chart(
    figure,
    title,
    description,
    chart_name,
    dimension=None,
    valid_values=None,
    drill_down=False,
):
    with st.container(border=False, key=f"labor_card_{chart_name}"):
        st.markdown(f"**{title}**")

        if description:
            st.caption(description)

        if figure is None:
            st.info("ไม่มีข้อมูลตามตัวกรองที่เลือก")
            return

        key = (
            f"cross_{chart_name}_"
            f"{chart_version()}"
        )

        if dimension is None:
            plot_chart(
                figure,
                key=key,
            )
        else:
            plot_chart(
                figure,
                key=key,
                on_select=(
                    lambda k=key,
                           d=dimension,
                           v=valid_values,
                           dr=drill_down:
                    queue_chart_filter(
                        k, d, v, dr
                    )
                ),
                selection_mode="points",
            )


def render_kpi(
    title,
    value,
    unit,
    note,
    css_class,
):
    if unit == "บาท/เดือน":
        rendered = format_number(
            value, decimals=0
        )
    else:
        rendered = format_number(value)

    st.markdown(
        f"""
        <div class="kpi-card {css_class}">
            <div class="kpi-title">
                {html.escape(title)}
            </div>
            <div class="kpi-value">
                {rendered}
                <span class="kpi-unit">
                    {html.escape(unit)}
                </span>
            </div>
            <div class="kpi-subtext">
                {html.escape(note)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



# ============================================================
# MAP EVENT / ACTIVE FILTERS / DRILL-DOWN HELPERS
# ============================================================

def handle_map_event(event, valid_regions, current_filters):
    """
    Turn a click coming back from the MapLibre component into the
    shared region filter. The component also returns its LAST event on
    every later rerun, so each event (identified by seq) is processed
    exactly once.
    """
    if not isinstance(event, dict):
        return

    try:
        seq = int(event.get("seq", 0))
    except (TypeError, ValueError):
        return

    if seq <= st.session_state.get("map_last_seq", 0):
        return

    st.session_state["map_last_seq"] = seq

    kind = event.get("type")
    region = event.get("region")

    if kind == "select" and region in set(valid_regions):
        value = region
    elif kind == "clear":
        value = ALL
    else:
        return

    if str(current_filters.get("region")) != str(value):
        st.session_state["_pending_chart_filter"] = {
            "dimension": "region",
            "value": value,
            "drill_down": False,
        }

    # Rerun in both cases: applies the filter before the sidebar is
    # built, and lets the map receive the new ack_seq.
    st.rerun()


FILTER_CHIPS = [
    ("year", "📅 ปี {v}"),
    ("quarter", "⏱️ ไตรมาส {v}"),
    ("region", "📍 {v}"),
    ("area", "🏙️ {v}"),
    ("sex", "👤 {v}"),
    ("age_group", "🎂 {v}"),
]


def render_active_filters(current_filters):
    """Active-filter bar: one chip per active dimension + reset all."""
    chips = []

    for dimension, template in FILTER_CHIPS:
        value = current_filters.get(dimension, ALL)

        if dimension == "year":
            chips.append((dimension, template.format(v=value), True))
        elif value not in (ALL, None):
            chips.append((dimension, template.format(v=value), False))

    st.markdown(
        '<div class="filter-banner">'
        '🎯 ตัวกรองที่ใช้อยู่ (ใช้ร่วมกันทุกแท็บ) · '
        'กดที่ตัวกรองเพื่อล้างทีละมิติ'
        '</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(len(chips) + 1)

    for column, (dimension, label, is_year) in zip(columns, chips):
        with column:
            st.button(
                ("↺ " if is_year else "✕ ") + label,
                key=f"chip_{dimension}",
                on_click=clear_filter,
                args=(dimension,),
                use_container_width=True,
                help=(
                    "รีเซ็ตปีเป็นค่าเริ่มต้น (2568)"
                    if is_year else "ล้างตัวกรองนี้"
                ),
            )

    with columns[-1]:
        st.button(
            "🔄 รีเซ็ตทั้งหมด",
            key="chip_reset_all",
            on_click=reset_dashboard_view,
            use_container_width=True,
        )


def missing_quarters_note(series, value_column):
    """Name the quarters that have no real value (never filled in)."""
    if series is None or series.empty:
        return ""

    have = set(
        series.loc[series[value_column].notna(), "quarter"]
        .astype(int)
        .tolist()
    )
    missing = [q for q in (1, 2, 3, 4) if q not in have]

    if not missing or not have.intersection({1, 2, 3, 4}):
        return ""

    return (
        "ไม่มีข้อมูลไตรมาส "
        + ", ".join(f"Q{q}" for q in missing)
        + " ในชุดข้อมูลภายใต้ตัวกรองนี้ (ไม่มีการนำค่าจากช่วงอื่นมาแทน)"
    )


def render_period_chart(
    figure,
    series,
    value_column,
    title,
    description,
    chart_name,
    drill_year,
):
    """
    Yearly chart (click a year -> year filter + drill to quarters)
    or Q1-Q4 chart (click a quarter -> quarter filter).
    """
    drilled = drill_year is not None

    if drilled:
        valid = (
            series.loc[
                series[value_column].notna()
                & series["quarter"].isin([1, 2, 3, 4]),
                "quarter",
            ].astype(int).tolist()
            if not series.empty else []
        )
    else:
        valid = (
            series.loc[series[value_column].notna(), "year"]
            .astype(int).tolist()
            if not series.empty else []
        )

    render_interactive_chart(
        figure,
        title,
        description,
        f"{chart_name}_{'q' if drilled else 'y'}",
        dimension="quarter" if drilled else "year",
        valid_values=valid,
        drill_down=not drilled,
    )

    if drilled:
        st.button(
            "↩️ กลับไปรายปี",
            key=f"back_{chart_name}",
            on_click=reset_trend_view,
        )

        note = missing_quarters_note(series, value_column)
        if note:
            st.caption("ℹ️ " + note)


# ============================================================
# MAP HIGHLIGHT
# ============================================================

def build_map(
    region_data,
    metric,
    selected_year,
    selected_region,
):
    is_selected = (
        selected_region not in (ALL, None)
    )

    height = (
        MAP_SELECTED_HEIGHT
        if is_selected
        else MAP_FULL_HEIGHT
    )

    fig = create_thailand_map(
        region_data,
        metric=metric,
        year=selected_year,
        selected_region=(
            selected_region if is_selected else ALL
        ),
        height=height,
    )

    if fig is None:
        return None

    fig.update_layout(
        height=height,
        autosize=False,
        margin=dict(l=5, r=5, t=5, b=5),
        clickmode="event+select",
        dragmode=False,
    )

    choropleths = [
        trace
        for trace in fig.data
        if trace.type == "choropleth"
    ]

    if not choropleths:
        return fig

    trace = choropleths[0]

    if not is_selected:
        fig.update_geos(
            fitbounds="locations",
            visible=False,
        )
        return fig

    region_names = list(trace.locations)

    if selected_region not in region_names:
        return fig

    original_values = dict(
        zip(region_names, list(trace.z))
    )

    # Fade every region but keep the selection targets.
    trace.z = [0] * len(region_names)
    trace.zmin = 0
    trace.zmax = 1
    trace.colorscale = [
        [0, "#EAE1EA"],
        [1, "#EAE1EA"],
    ]
    trace.showscale = False

    trace.marker.line.color = "#FFFFFF"
    trace.marker.line.width = 1.2

    selected_value = original_values.get(
        selected_region
    )

    fig.add_trace(
        go.Choropleth(
            geojson=trace.geojson,
            locations=[selected_region],
            z=[1],
            customdata=[[selected_region]],
            featureidkey=trace.featureidkey,
            colorscale=[
                [0, PINK],
                [1, PINK],
            ],
            zmin=0,
            zmax=1,
            showscale=False,
            marker=dict(
                line=dict(
                    color="#552B65",
                    width=3,
                )
            ),
            hovertemplate=(
                f"<b>{html.escape(str(selected_region))}</b>"
                f"<br>{LABELS.get(metric, metric)}: "
                f"{format_number(selected_value)}"
                "<extra></extra>"
            ),
        )
    )

    return fig


def regional_metric_value(
    frame,
    region,
    candidate_columns,
):
    if (
        not isinstance(frame, pd.DataFrame)
        or frame.empty
        or "region" not in frame.columns
    ):
        return None

    rows = frame[
        frame["region"] == region
    ]

    if rows.empty:
        return None

    for column in candidate_columns:
        if column in rows.columns:
            value = safe_number(
                rows.iloc[0][column]
            )

            if value is not None:
                return value

    return None


def render_regional_detail(
    region,
    frame,
    period_label,
):
    st.markdown(
        f"""
        <div class="region-head">
            <div class="region-head-kicker">ข้อมูลภูมิภาคที่เลือก</div>
            <h3>📍 {html.escape(str(region))}</h3>
            <div class="region-head-period">{html.escape(str(period_label))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    details = [
        (
            "💵 ค่าจ้างเฉลี่ย",
            ["avg_wage"],
            " บาท/เดือน",
        ),
        (
            "📈 อัตราการมีงานทำ",
            ["emp_rate"],
            "%",
        ),
        (
            "⚠️ อัตราการว่างงาน",
            ["unemp_rate"],
            "%",
        ),
        (
            "👥 จำนวนผู้มีงานทำ",
            ["headcount_m", "emp_headcount_m"],
            " ล้านคน",
        ),
    ]

    for label, columns, suffix in details:
        value = regional_metric_value(
            frame, region, columns
        )

        st.markdown(
            f"""
            <div class="detail-metric">
                <div class="detail-label">{label}</div>
                <div class="detail-value">{format_number(value)}</div>
                <div class="detail-unit">{html.escape(suffix.strip())}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# HISTORICAL TREND: KEEP EVERY YEAR AVAILABLE
# ============================================================

def get_historical_observations(
    data,
    filters,
):
    """
    Annual trend always retains all available years
    from 2561 to 2568.

    Region, age, sex and area are applied.
    Year and quarter sidebar filters are excluded here.

    This lets users click a different year even while
    their current global year is already selected.
    """

    required = [
        "year",
        "quarter",
        "emp_rate",
        "unemp_rate",
    ]

    if not set(required).issubset(data.columns):
        return pd.DataFrame(columns=required)

    frame = data.copy()

    dimensions = {
        "region": "clean_region",
        "area": "clean_area",
        "sex": "clean_sex",
        "age_group": "clean_age",
    }

    for dimension, column in dimensions.items():
        if column not in frame.columns:
            continue

        value = filters.get(dimension, ALL)

        target = (
            "รวม"
            if value in (ALL, "รวม", None)
            else str(value)
        )

        if (
            dimension == "area"
            and target == "รวม"
            and filters.get("region") == "กรุงเทพมหานคร"
        ):
            target = "ในเขตเทศบาล"

        frame = frame[
            frame[column].astype(str) == target
        ]

    frame = frame[required].copy()

    for column in required:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        )

    frame = frame[
        frame["year"].between(
            START_YEAR, END_YEAR
        )
        & frame["quarter"].isin([1, 2, 3, 4])
    ]

    if frame.empty:
        return pd.DataFrame(columns=required)

    # A unique observation must have a unique rate.
    # Identical duplicate records do not change the value.
    rows = []

    for (year, quarter), group in frame.groupby(
        ["year", "quarter"],
        sort=True,
    ):
        row = {
            "year": int(year),
            "quarter": int(quarter),
        }

        for metric in [
            "emp_rate",
            "unemp_rate",
        ]:
            values = group[metric].dropna().unique()

            row[metric] = (
                float(values[0])
                if len(values) == 1
                else np.nan
            )

        if (
            pd.notna(row["emp_rate"])
            or pd.notna(row["unemp_rate"])
        ):
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=required)

    return pd.DataFrame(rows).sort_values(
        ["year", "quarter"]
    )


def build_historical_trend(
    observations,
    selected_year=None,
):
    """
    If selected_year is None:
        Show every year.

    Otherwise:
        Show Q1-Q4 of selected_year.

    The global filter is updated by the chart callback.
    """

    if observations.empty:
        return None

    quarterly = selected_year is not None

    fig = go.Figure()

    for metric, label, color, axis in [
        (
            "emp_rate",
            "อัตราการมีงานทำ",
            PINK,
            "y",
        ),
        (
            "unemp_rate",
            "อัตราการว่างงาน",
            PURPLE,
            "y2",
        ),
    ]:
        frame = observations.dropna(
            subset=[metric]
        ).sort_values(["year", "quarter"])

        if quarterly:
            frame = frame[
                frame["year"] == int(selected_year)
            ]
            x = frame["quarter"].astype(int).tolist()
        else:
            frame = frame.drop_duplicates(
                "year",
                keep="last",
            ).sort_values("year")
            x = frame["year"].astype(int).tolist()

        if frame.empty:
            continue

        fig.add_trace(
            go.Scatter(
                x=x,
                y=frame[metric].tolist(),
                customdata=[
                    [int(value)] for value in x
                ],
                mode="lines+markers",
                name=label,
                yaxis=axis,
                line=dict(
                    color=color,
                    width=3,
                    dash=(
                        "dot"
                        if metric == "unemp_rate"
                        else "solid"
                    ),
                ),
                marker=dict(
                    size=11,
                    color=color,
                    line=dict(
                        color="white",
                        width=1,
                    ),
                ),
                hovertemplate=(
                    "<b>%{x}</b>"
                    "<br>" + label
                    + ": %{y:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

    if not fig.data:
        return None

    if quarterly:
        ticks = [1, 2, 3, 4]
        labels = ["Q1", "Q2", "Q3", "Q4"]
        x_title = f"ไตรมาส ปี พ.ศ. {selected_year}"
    else:
        ticks = list(range(
            START_YEAR,
            END_YEAR + 1,
        ))
        labels = [str(v) for v in ticks]
        x_title = "ปี พ.ศ."

    fig.update_layout(
        height=390,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="IBM Plex Sans Thai, sans-serif",
            color=DARK,
        ),
        margin=dict(
            l=60,
            r=65,
            t=70,
            b=55,
        ),
        clickmode="event+select",
        dragmode=False,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.12,
            yanchor="bottom",
        ),
        xaxis=dict(
            title=x_title,
            type="linear",
            tickmode="array",
            tickvals=ticks,
            ticktext=labels,
            gridcolor=GRID,
        ),
        yaxis=dict(
            title="อัตราการมีงานทำ (%)",
            gridcolor=GRID,
            tickfont=dict(color=PINK),
        ),
        yaxis2=dict(
            title="อัตราการว่างงาน (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=PURPLE),
        ),
    )

    return fig


# ============================================================
# AGE UNEMPLOYMENT PRESENTATION
# ============================================================

def prepare_age_chart(
    age_data,
    selected_age=None,
):
    figure = create_youth_unemployment_chart(
        age_data,
        selected_age=selected_age,
    )

    if figure is None:
        return None, None

    # Remove overlapping insight annotations.
    figure.update_layout(
        annotations=[],
        height=430,
        margin=dict(
            l=110, r=65, t=20, b=55
        ),
    )

    summary = None

    if (
        isinstance(age_data, pd.DataFrame)
        and not age_data.empty
        and {"age_group", "unemp_rate"}
        .issubset(age_data.columns)
    ):
        candidates = []

        for age, group in age_data.groupby(
            "age_group"
        ):
            unique = pd.to_numeric(
                group["unemp_rate"],
                errors="coerce",
            ).dropna().unique()

            if len(unique) == 1:
                candidates.append(
                    (str(age), float(unique[0]))
                )

        if candidates:
            summary = max(
                candidates,
                key=lambda item: item[1],
            )

    return figure, summary


# ============================================================
# LOAD DATA / YEAR SCOPE
# ============================================================

try:
    raw_df = get_cached_labor_data()
except Exception as error:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {error}")
    st.stop()

# Work with a scoped copy only.
# The original CSV remains unchanged.
df = raw_df[
    pd.to_numeric(
        raw_df["year"],
        errors="coerce",
    ).between(
        START_YEAR,
        END_YEAR,
    )
].copy()

if df.empty:
    st.error(
        "ไม่พบข้อมูลระหว่างปี 2561–2568"
    )
    st.stop()

# Restore a valid year if an older session
# retained a value outside the permitted scope.
valid_years = sorted(
    pd.to_numeric(
        df["year"],
        errors="coerce",
    ).dropna().astype(int).unique().tolist(),
    reverse=True,
)

current_filter_state = dict(
    st.session_state.get("filters", {})
)

current_year = current_filter_state.get("year")

if current_year not in [ALL, *valid_years]:
    current_filter_state["year"] = ALL

    st.session_state["filters"] = (
        current_filter_state
    )

    sidebar_year_key = SIDEBAR_KEYS.get("year")

    if sidebar_year_key is not None:
        st.session_state[
            sidebar_year_key
        ] = ALL

sanitize_filters(df)

filters = dict(get_current_filters())

# ALL is the global year selection. Single-period charts still require a
# reference year; use the latest AVAILABLE year, never a fabricated aggregate.
all_years_selected = filters["year"] == ALL
selected_year = valid_years[0] if all_years_selected else int(filters["year"])
# Keep the actual year selection for all calculations. The reference year
# is used only for historical drill-down controls and map geometry.
ui_filters = dict(filters)
selected_region = filters["region"]

# While the trend is in quarterly mode it always shows the GLOBAL
# year, so changing the year from the sidebar, a chip or a chart
# keeps every drill-down chart consistent.
if st.session_state.get("trend_drill_year") is not None:
    st.session_state["trend_drill_year"] = None if all_years_selected else selected_year

region_selected = selected_region not in (
    ALL, None
)

available_regions = get_regions_for_year(
    df,
    ALL if all_years_selected else selected_year,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-brand-card">
            <h2>🇹🇭 Labor Analytics</h2>
            <p>สถิติตลาดแรงงานไทย (NSO Thailand)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔍 ตัวกรองข้อมูลหลัก")

    st.selectbox(
        "📅 ปี พ.ศ.",
        options=[ALL, *valid_years],
        format_func=lambda value: "ทุกปี" if value == ALL else str(value),
        key=SIDEBAR_KEYS["year"],
        on_change=on_sidebar_year_change,
    )

    st.selectbox(
        "⏱️ ไตรมาส",
        options=[
            ALL,
            *get_quarters_for_year(
                df, ALL if all_years_selected else selected_year
            ),
        ],
        key=SIDEBAR_KEYS["quarter"],
        on_change=on_sidebar_change,
        args=("quarter",),
        format_func=lambda value: (
            f"ไตรมาส {value}"
            if isinstance(value, (int, np.integer))
            else "ทั้งหมด (ภาพรวม)"
        ),
    )

    st.selectbox(
        "📍 ภูมิภาค",
        options=[ALL, *available_regions],
        key=SIDEBAR_KEYS["region"],
        on_change=on_sidebar_change,
        args=("region",),
    )

    st.selectbox(
        "🏙️ เขตการปกครอง",
        options=[
            ALL,
            "ในเขตเทศบาล",
            "นอกเขตเทศบาล",
        ],
        key=SIDEBAR_KEYS["area"],
        on_change=on_sidebar_change,
        args=("area",),
    )

    st.selectbox(
        "👤 เพศ",
        options=[
            ALL,
            "ชาย",
            "หญิง",
        ],
        key=SIDEBAR_KEYS["sex"],
        on_change=on_sidebar_change,
        args=("sex",),
    )

    st.selectbox(
        "🎂 กลุ่มอายุ",
        options=[
            ALL,
            *[
                age
                for age in AGE_ORDER
                if age != "รวม"
            ],
        ],
        key=SIDEBAR_KEYS["age_group"],
        on_change=on_sidebar_change,
        args=("age_group",),
    )

    st.markdown("---")

    st.button(
        "🔄 รีเซ็ตตัวกรองทั้งหมด",
        type="primary",
        use_container_width=True,
        on_click=reset_dashboard_view,
    )

    st.caption(
        "ข้อมูล: สำนักงานสถิติแห่งชาติ (NSO)"
    )


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    """
    <section class="labor-hero">
      <div class="labor-hero-icon">▥</div>
      <div class="labor-hero-copy">
        <h1>ศูนย์วิเคราะห์ตลาดแรงงานไทย</h1>
        <p>สำรวจภาพรวม แนวโน้ม และความแตกต่างของตลาดแรงงานไทย</p>
      </div>
      <div class="labor-hero-period"><span>ข้อมูลสถิติ</span><strong>พ.ศ. 2561–2568</strong></div>
      <div class="labor-hero-art" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>
    </section>
    """,
    unsafe_allow_html=True,
)

scope = (
    selected_region
    if region_selected
    else "ประเทศไทย"
)

kpis = get_kpis(
    df,
    filters,
)

period_label = (
    "ทุกปี (2561–2568)" if all_years_selected else
    (kpis.get("period_label") or f"ปี พ.ศ. {selected_year}")
)

# The regional comparison remains complete:
# changing a region must not hide other choices.
comparison_filters = dict(filters)
comparison_filters["region"] = ALL

all_region_data = get_regional_comparison_data(
    df,
    comparison_filters,
)

# The actual selected filter combination.
selected_region_data = (
    get_regional_comparison_data(
        df,
        filters,
    )
)


# ============================================================
# ACTIVE FILTERS
# ============================================================

# The duplicate active-filter chip bar was removed by design; Sidebar remains the source of controls.



# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs([
    "📊 ภาพรวมตลาดแรงงานไทย",
    "🗺️ เปรียบเทียบภูมิภาค",
    "👥 วิเคราะห์กลุ่มแรงงาน",
])


# ============================================================
# TAB 1 - OVERVIEW
# ============================================================

with tab1:

    st.caption(
        f"📍 {scope} · {period_label}"
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    kpi_definitions = [
        (
            "💵 ค่าจ้างเฉลี่ย",
            kpis.get("avg_wage"),
            "บาท/เดือน",
            "ผู้มีงานทำที่เป็นลูกจ้าง",
            "kpi-card-1",
        ),
        (
            "📈 อัตราการมีงานทำ",
            kpis.get("emp_rate"),
            "%",
            "ข้อมูลตามนิยาม NSO",
            "kpi-card-2",
        ),
        (
            "⚠️ อัตราการว่างงาน",
            kpis.get("unemp_rate"),
            "%",
            "ผู้ว่างงานต่อกำลังแรงงาน",
            "kpi-card-3",
        ),
        (
            "👥 จำนวนผู้มีงานทำ",
            kpis.get("emp_headcount_m"),
            "ล้านคน",
            "หน่วยล้านคน",
            "kpi-card-4",
        ),
    ]

    for column, item in zip(
        st.columns(4),
        kpi_definitions,
    ):
        with column:
            render_kpi(*item)

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    st.markdown(
        '<div class="dashboard-section-title">'
        '🗺️ สำรวจตลาดแรงงานรายภูมิภาค'
        '</div>',
        unsafe_allow_html=True,
    )

    # Fixed map metric. The side panel still shows all indicators.
    map_metric = "emp_rate"

    map_frame = filter_frame(
        all_region_data,
        map_metric,
    )

    map_regions = (
        map_frame["region"].astype(str).tolist()
        if not map_frame.empty
        else []
    )

    # Slots keep a FIXED position in the page, so the map iframe is
    # never re-created when a region is selected / cleared.
    map_banner_slot = st.container()
    map_box = st.container(border=False, key="labor_card_map")

    with map_banner_slot:
        if region_selected:
            st.markdown(
                '<div class="filter-banner">'
                '📍 กำลังดูข้อมูล: '
                + html.escape(str(selected_region))
                + ' · แผนที่และกราฟอื่นใช้ตัวกรองเดียวกัน'
                '</div>',
                unsafe_allow_html=True,
            )

    all_map_regions = (
        all_region_data["region"].astype(str).tolist()
        if not all_region_data.empty
        else []
    )

    map_values = {
        str(row["region"]): row[map_metric]
        for _, row in map_frame.iterrows()
    }

    map_details = {
        str(row["region"]): {
            "avg_wage": row.get("avg_wage"),
            "emp_rate": row.get("emp_rate"),
            "unemp_rate": row.get("unemp_rate"),
            "headcount_m": row.get("headcount_m"),
        }
        for _, row in all_region_data.iterrows()
    }

    map_note_parts = []
    if not all_years_selected and selected_year >= 2567:
        map_note_parts.append(
            f"ค่าจ้างปี {selected_year} ไม่แยกไตรมาส (quarter = 0)"
        )
    if filters.get("area", ALL) != ALL:
        map_note_parts.append(
            "จำนวนผู้มีงานทำไม่มีข้อมูลแยกเขตเทศบาล"
        )

    with map_box:
        st.markdown("**🗺️ แผนที่ประเทศไทย**")
        st.caption(
            "คลิกภูมิภาคเพื่อซูมและกรองข้อมูลทุกแท็บ · "
            "แผนที่ใช้ MapLibre GL JS"
        )

        map_event, map_ok = render_region_map(
            year=selected_year,
            values=map_values,
            details=map_details,
            metric_key=map_metric,
            metric_label=LABELS[map_metric],
            selected=(
                selected_region
                if region_selected
                and selected_region in all_map_regions
                else None
            ),
            ack_seq=st.session_state.get("map_last_seq", 0),
            period_label=period_label,
            note=" · ".join(map_note_parts),
            height=MAP_FULL_HEIGHT,
        )

        if not map_ok:
            st.warning(
                "ไม่สามารถแสดงแผนที่ได้: อ่านไฟล์ขอบเขตภูมิภาคไม่ได้ "
                "หรือยังไม่ได้ติดตั้ง shapely (pip install shapely)"
            )

    handle_map_event(map_event, all_map_regions, filters)

    # --------------------------------------------------------
    # YEARLY TREND / GLOBAL FILTER DRILL-DOWN
    # --------------------------------------------------------

    st.markdown(
        '<div class="dashboard-section-title">'
        '📈 แนวโน้มตลาดแรงงาน'
        '</div>',
        unsafe_allow_html=True,
    )

    trend_data = get_historical_observations(
        df, filters
    )

    drill_year = st.session_state[
        "trend_drill_year"
    ]

    available_trend_years = (
        trend_data["year"].astype(int).unique().tolist()
        if not trend_data.empty
        else []
    )

    with st.container(border=False, key="labor_card_trend"):

        if drill_year is None:

            st.markdown(
                "**📈 แนวโน้มอัตราการมีงานทำ"
                "และอัตราการว่างงานรายปี**"
            )

            st.caption(
                "คลิกปีใดก็ได้บนกราฟ → "
                "กราฟนี้เปลี่ยนเป็นรายไตรมาส "
                "และ Dashboard ทุกแท็บเปลี่ยนเป็นปีนั้น"
            )

            yearly_fig = build_historical_trend(
                trend_data
            )

            if yearly_fig is None:
                st.info(
                    "ไม่มีข้อมูลแนวโน้มรายปี"
                )
            else:

                year_key = (
                    "global_year_trend_"
                    f"{chart_version()}_"
                    f"{st.session_state['trend_view_version']}"
                )

                plot_chart(
                    yearly_fig,
                    key=year_key,
                    on_select=(
                        lambda k=year_key,
                               v=available_trend_years:
                        queue_chart_filter(
                            k,
                            "year",
                            v,
                            drill_down=True,
                        )
                    ),
                    selection_mode="points",
                )

        else:

            heading, back = st.columns(
                [4, 1]
            )

            with heading:
                st.markdown(
                    f"**📊 รายไตรมาส ปี พ.ศ. "
                    f"{drill_year}**"
                )

                st.caption(
                    "ปีนี้ถูกเลือกใน Global Filter แล้ว "
                    "กราฟอื่นทุกแท็บใช้ปีเดียวกัน"
                )

            with back:
                st.button(
                    "↩️ กลับไปรายปี",
                    key="back_to_yearly",
                    on_click=reset_trend_view,
                    use_container_width=True,
                )

            quarter_fig = build_historical_trend(
                trend_data,
                selected_year=drill_year,
            )

            if quarter_fig is None:
                st.info(
                    f"ไม่มีข้อมูลรายไตรมาสปี "
                    f"{drill_year} ภายใต้เงื่อนไขนี้"
                )
            else:
                plot_chart(
                    quarter_fig,
                    key=f"trend_quarters_{drill_year}",
                )

    # --------------------------------------------------------
    # SECONDARY TREND CHARTS: AVERAGE WAGE + EMPLOYED HEADCOUNT
    # (yearly 2561-2568  ->  Q1-Q4 of the clicked year)
    # --------------------------------------------------------

    chart_year = st.session_state["trend_drill_year"]
    drilled_now = chart_year is not None

    selected_quarter = filters.get("quarter", ALL)
    selected_quarter = (
        int(selected_quarter)
        if selected_quarter not in (ALL, None)
        else None
    )

    wage_series = get_wage_period_series(
        df, filters, chart_year
    )
    headcount_series = get_headcount_period_series(
        df, filters, chart_year
    )

    wage_col, headcount_col = st.columns(2)

    with wage_col:
        wage_figure = create_wage_period_chart(
            wage_series,
            selected_year=selected_year,
            selected_quarter=selected_quarter,
            drilled=drilled_now,
        )
        # In this app-only update, switch the quarterly wage bars to a line
        # without changing the shared chart module.
        if drilled_now and chart_year <= 2566 and wage_figure is not None:
            present = wage_series.dropna(subset=["avg_wage"]).copy()
            if not present.empty:
                wage_figure = go.Figure(go.Scatter(
                    x=present["label"].astype(str), y=present["avg_wage"],
                    customdata=present["quarter"].astype(int).tolist(),
                    mode="lines+markers", line=dict(color=PURPLE, width=3),
                    marker=dict(color=PINK, size=10),
                    hovertemplate="ไตรมาส %{x}<br>ค่าจ้าง %{y:,.0f} บาท/เดือน<extra></extra>",
                ))
                wage_figure.update_layout(
                    height=350, paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="IBM Plex Sans Thai, sans-serif", color=DARK),
                    margin=dict(l=55, r=25, t=55, b=55),
                    xaxis=dict(title="ไตรมาส", type="category"),
                    yaxis=dict(title="ค่าจ้างเฉลี่ย (บาท/เดือน)", tickformat=","),
                )

        if not drilled_now:
            wage_title = "💵 ค่าจ้างเฉลี่ยรายปี"
            wage_caption = (
                "ปี 2561–2566 ใช้ค่าจ้างของไตรมาสล่าสุดของปี · "
                "คลิกปีเพื่อดู Q1–Q4"
            )
        elif chart_year <= 2566:
            wage_title = f"💵 ค่าจ้างเฉลี่ยรายไตรมาส ปี {chart_year}"
            wage_caption = "คลิกจุดบนเส้นเพื่อเปลี่ยนตัวกรองไตรมาส"
        else:
            wage_title = f"💵 ค่าจ้างเฉลี่ย ปี {chart_year} (ไม่แยกไตรมาส)"
            wage_caption = (
                "ปีนี้ชุดข้อมูลมีค่าจ้างเฉพาะ quarter = 0 "
                "จึงไม่มีค่า Q1–Q4"
            )

        render_period_chart(
            wage_figure,
            wage_series,
            "avg_wage",
            wage_title,
            wage_caption,
            "wage_period",
            chart_year,
        )

        if (
            (not drilled_now and not wage_series.empty
             and (wage_series["kind"] == "unlabeled").any())
            or (drilled_now and chart_year > 2566)
        ):
            st.caption(
                "⚠️ ค่าจ้างปี 2567–2568 ไม่มีป้ายไตรมาส และมีหลายค่าต่อกลุ่ม "
                "ระบบแสดงค่าเฉลี่ยของค่าที่รายงาน (จุดสีส้ม) "
                "ระดับค่าจ้างอาจเทียบกับปี 2566 ตรง ๆ ไม่ได้"
            )

    with headcount_col:
        headcount_figure = create_headcount_period_chart(
            headcount_series,
            selected_year=selected_year,
            selected_quarter=selected_quarter,
            drilled=drilled_now,
        )

        render_period_chart(
            headcount_figure,
            headcount_series,
            "headcount_m",
            (
                "👥 จำนวนผู้มีงานทำรายปี"
                if not drilled_now
                else f"👥 จำนวนผู้มีงานทำรายไตรมาส ปี {chart_year}"
            ),
            (
                "หน่วยล้านคน (ไตรมาสล่าสุดของปี) · คลิกปีเพื่อดู Q1–Q4"
                if not drilled_now
                else "หน่วยล้านคน · คลิกแท่งเพื่อเปลี่ยนตัวกรองไตรมาส"
            ),
            "headcount_period",
            chart_year,
        )

        if filters.get("area", ALL) != ALL:
            st.caption(
                "ℹ️ จำนวนผู้มีงานทำไม่มีข้อมูลแยกเขตเทศบาล "
                "ตัวกรองเขตการปกครองจึงไม่มีผลกับกราฟนี้"
            )


# ============================================================
# REGION DRILL-DOWN CHARTS (APP-ONLY, KEEP charts.py UNCHANGED)
# ============================================================

def _regional_aligned_yearly_figure(df, filters, region, selected_year):
    """Two yearly lines. Wage and rate MUST be sourced from the SAME quarter.

    Only periods 2561-2566 have labeled quarterly wages in the source.
    No imputation or Q0 wage-to-quarter matching is performed.
    """
    records = []
    region_filters = dict(filters, region=region, quarter=ALL)
    for year in range(START_YEAR, min(END_YEAR, 2566) + 1):
        candidates = []
        for quarter in (1, 2, 3, 4):
            f = dict(region_filters, year=year, quarter=quarter)
            r = get_regional_comparison_data(df, f)
            hit = r[r["region"] == region]
            if hit.empty:
                continue
            wage = safe_number(hit.iloc[0]["avg_wage"])
            rate = safe_number(hit.iloc[0]["emp_rate"])
            if wage is not None and rate is not None:
                candidates.append((quarter, wage, rate))
        if candidates:
            quarter, wage, rate = candidates[-1]
            records.append((year, quarter, wage, rate))

    if not records:
        return None
    years = [str(r[0]) for r in records]
    raw_years = [r[0] for r in records]
    wage_values = [r[2] for r in records]
    rate_values = [r[3] for r in records]
    quarter_ids = [r[1] for r in records]
    marker_sizes = [13 if y == selected_year else 8 for y in raw_years]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=wage_values, name="ค่าจ้างเฉลี่ย", mode="lines+markers",
        yaxis="y", customdata=[[y, q] for y, q in zip(raw_years, quarter_ids)],
        line=dict(color=PINK, width=3), marker=dict(size=marker_sizes, color=PINK),
        hovertemplate="ปี %{x} · Q%{customdata[1]}<br>ค่าจ้าง %{y:,.0f} บาท/เดือน<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=rate_values, name="อัตราการมีงานทำ", mode="lines+markers",
        yaxis="y2", customdata=[[y, q] for y, q in zip(raw_years, quarter_ids)],
        line=dict(color=PURPLE, width=3, dash="dot"),
        marker=dict(size=marker_sizes, color=PURPLE),
        hovertemplate="ปี %{x} · Q%{customdata[1]}<br>อัตราการมีงานทำ %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans Thai, sans-serif", color=DARK), hovermode="x unified",
        margin=dict(l=55, r=55, t=78, b=50),
        legend=dict(orientation="h", x=.5, xanchor="center", y=1.14),
        xaxis=dict(title="ปี พ.ศ.", type="category", showgrid=False),
        yaxis=dict(title="ค่าจ้างเฉลี่ย (บาท/เดือน)", tickformat=",", tickfont=dict(color=PINK)),
        yaxis2=dict(title="อัตราการมีงานทำ (%)", overlaying="y", side="right",
                    showgrid=False, tickfont=dict(color=PURPLE)),
    )
    return fig


def _regional_municipal_yearly_figure(df, filters, region, selected_year):
    """Compare municipal and non-municipal wages per year; never synthesize quarters."""
    records = []
    for year in range(START_YEAR, END_YEAR + 1):
        f = dict(filters, year=year, quarter=ALL)
        reg = get_area_wage_comparison_data(df, f)
        hit = reg[reg["region"] == region]
        if hit.empty:
            continue
        a = safe_number(hit.iloc[0]["wage_in"])
        b = safe_number(hit.iloc[0]["wage_out"])
        if a is not None or b is not None:
            records.append((year, a, b))
    if not records:
        return None
    years = [str(row[0]) for row in records]
    markers = [13 if row[0] == selected_year else 8 for row in records]
    fig = go.Figure()
    for col, label, color in [(1, "ในเขตเทศบาล", PINK), (2, "นอกเขตเทศบาล", PURPLE)]:
        fig.add_trace(go.Scatter(
            x=years, y=[r[col] for r in records], mode="lines+markers",
            name=label, customdata=[r[0] for r in records],
            line=dict(color=color, width=3), marker=dict(color=color, size=markers),
            connectgaps=False,
            hovertemplate="ปี %{x}<br>" + label + ": %{y:,.0f} บาท/เดือน<extra></extra>",
        ))
    fig.update_layout(
        height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans Thai, sans-serif", color=DARK),
        margin=dict(l=60, r=20, t=70, b=50),
        legend=dict(orientation="h", x=.5, xanchor="center", y=1.1),
        xaxis=dict(title="ปี พ.ศ.", type="category", showgrid=False),
        yaxis=dict(title="ค่าจ้างเฉลี่ย (บาท/เดือน)", tickformat=","),
    )
    return fig



def create_all_years_heatmap(df, filters):
    """For 'ทุกปี', plot annual mean headcount per sex-age cell (millions)."""
    if filters.get("year") != ALL:
        return create_demographic_matrix_heatmap(df, filters)
    figures = []
    for yr in sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique()):
        fig = create_demographic_matrix_heatmap(df, dict(filters, year=yr))
        if fig is not None and fig.data:
            figures.append(fig)
    if not figures:
        return None
    # Align axis labels before averaging to avoid mixing age groups.
    ages = list(figures[0].data[0].x)
    sexes = list(figures[0].data[0].y)
    stacks = []
    for fig in figures:
        trace = fig.data[0]
        if list(trace.x) == ages and list(trace.y) == sexes:
            stacks.append(np.asarray(trace.z, dtype=float))
    if not stacks:
        return None
    with np.errstate(invalid="ignore"):
        counts = np.sum(np.isfinite(stacks), axis=0)
        totals = np.nansum(stacks, axis=0)
        average = np.divide(totals, counts, out=np.full_like(totals, np.nan), where=counts > 0)
    figure = figures[0]
    figure.data[0].z = average
    return figure

# Keep the ECharts custom component visible inside Streamlit tab/card layouts.
# Avoid global iframe size overrides: the map component has its own dimensions.
st.markdown("""
<style>
[class*="st-key-labor_card_gender"] [data-testid="stCustomComponentV1"],
[class*="st-key-labor_card_gender"] [data-testid="stCustomComponent"],
[class*="st-key-labor_card_gender"] [data-testid="stCustomComponentV1"] iframe,
[class*="st-key-labor_card_gender"] [data-testid="stCustomComponent"] iframe {
    min-height: 390px !important;
    width: 100% !important;
    display: block !important;
    visibility: visible !important;
}
[class*="st-key-labor_card_gender"] iframe[title*="streamlit_echarts"] {
    min-height: 390px !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

def _render_clickable_gender_donut(df, filters):
    """Clickable ECharts donut with gender cross-filter and all-years support."""
    # Keep both genders available regardless of the active sex filter.
    chart_filters = dict(filters)
    chart_filters["sex"] = ALL

    if chart_filters.get("year") == ALL:
        # Average snapshots by year; don't sum the same population across years.
        annual_counts = []
        years = sorted(pd.to_numeric(df["year"], errors="coerce").dropna().astype(int).unique())
        for yr in years:
            annual_fig = create_gender_headcount_donut(
                df, dict(chart_filters, year=int(yr))
            )
            if annual_fig is None or not annual_fig.data:
                continue
            counts = {
                str(label): float(value)
                for label, value in zip(
                    annual_fig.data[0].labels, annual_fig.data[0].values
                )
                if pd.notna(value)
            }
            if all(s in counts for s in ("ชาย", "หญิง")):
                annual_counts.append(counts)
        by_sex = {
            sex: float(np.mean([r[sex] for r in annual_counts]))
            for sex in ("ชาย", "หญิง")
        } if annual_counts else {}
    else:
        fig = create_gender_headcount_donut(df, chart_filters)
        by_sex = (
            {str(k): float(v) for k, v in zip(fig.data[0].labels, fig.data[0].values)
             if pd.notna(v)}
            if fig is not None and fig.data else {}
        )

    with st.container(border=False, key="labor_card_gender"):
        st.markdown("**👫 สัดส่วนผู้มีงานทำแยกตามเพศ**")
        st.caption("คลิกบนวงสีฟ้า (ชาย) หรือสีชมพู (หญิง) เพื่อกรองทุกแท็บ · คลิกเพศเดิมซ้ำเพื่อยกเลิก")
        if not by_sex or sum(by_sex.values()) <= 0:
            st.info("ไม่มีข้อมูลผู้มีงานทำสำหรับตัวกรองที่เลือก")
            return

        selected_sex = filters.get("sex", ALL)
        if selected_sex in ("ชาย", "หญิง"):
            names = [selected_sex]
        else:
            names = [sex for sex in ("ชาย", "หญิง") if by_sex.get(sex, 0) > 0]
        display_values = [max(0.0, by_sex.get(sex, 0.0)) for sex in names]
        center_k = sum(display_values)
        color_by_sex = {"ชาย": "#57A8F5", "หญิง": "#E83C91"}

        options = {
            "backgroundColor": "transparent",
            "animation": True,
            "animationDuration": 250,
            "tooltip": {
                "trigger": "item",
                "formatter": "{b}: {d}% ({c} พันคน)",
            },
            "legend": {
                "show": True, "data": ["ชาย", "หญิง"],
                "top": 4, "left": "center", "selectedMode": False,
                "itemWidth": 13, "itemHeight": 13, "itemGap": 26,
                "textStyle": {"color": "#43334C", "fontSize": 13,
                              "fontFamily": "IBM Plex Sans Thai, sans-serif"},
            },
            "title": {
                "text": f"{center_k / 1000:,.2f}",
                "subtext": "ล้านคน" if selected_sex == ALL else f"ล้านคน · {selected_sex} 100%",
                "left": "center", "top": "46%",
                "textStyle": {"fontFamily": "IBM Plex Sans Thai, sans-serif",
                              "color": "#43334C", "fontSize": 24, "fontWeight": "bold"},
                "subtextStyle": {"fontFamily": "IBM Plex Sans Thai, sans-serif",
                                 "color": "#43334C", "fontSize": 14},
            },
            "series": [{
                "type": "pie", "radius": ["51%", "78%"],
                "center": ["50%", "55%"], "selectedMode": False,
                "label": {"show": True, "position": "inside", "formatter": "{d}%",
                          "color": "#FFFFFF", "fontWeight": "bold"},
                "labelLine": {"show": False},
                "itemStyle": {"borderColor": "#FFFFFF", "borderWidth": 3},
                "data": [
                    {"name": sex, "value": round(value, 4),
                     "itemStyle": {"color": color_by_sex[sex]}}
                    for sex, value in zip(names, display_values)
                ],
            }],
        }

        try:
            from streamlit_echarts import st_echarts
        except ImportError:
            st.error("ต้องติดตั้ง streamlit-echarts ก่อน: pip install streamlit-echarts==0.4.0")
            # Keep the chart visible even if dependency is not installed.
            backup = go.Figure(go.Pie(
                labels=names, values=display_values, hole=0.66,
                marker=dict(colors=[color_by_sex[s] for s in names]),
            ))
            st.plotly_chart(backup, use_container_width=True, config=PLOT_CONFIG)
            return

        # Use Canvas: SVG charts sometimes fail to paint when opened from a hidden Streamlit tab.
        # Keep the ECharts component mounted across year/region/sidebar changes.
        # Re-keying on every filter change can produce a temporarily blank iframe
        # (especially when Tab 3 was hidden) and lose the chart's update cycle.
        # Events have unique click IDs; old events are acknowledged below.
        events = {
            "click": "function(p) { if (p.componentType !== 'series' || "
                     "(p.name !== 'ชาย' && p.name !== 'หญิง')) return null; "
                     "return {sex: p.name, click_id: Date.now() + '_' + Math.random()}; }"
        }
        try:
            event = st_echarts(
                options=options, events=events, height="390px",
                key="gender_donut_echarts_stable_v3_canvas",
                renderer="canvas",
            )
        except Exception as exc:
            st.error(f"กราฟโดนัท ECharts มีข้อผิดพลาด: {exc}")
            return

        if not isinstance(event, dict):
            return
        sex = event.get("sex")
        click_id = event.get("click_id")
        if sex not in ("ชาย", "หญิง") or click_id is None:
            return
        if st.session_state.get("_gender_last_click_id") == click_id:
            return
        st.session_state["_gender_last_click_id"] = click_id
        st.session_state["_pending_chart_filter"] = {
            "dimension": "sex",
            "value": ALL if selected_sex == sex else sex,
            "drill_down": False,
        }
        st.rerun()


# ============================================================
# TAB 2 - REGIONAL COMPARISON
# ============================================================

with tab2:

    st.markdown(
        "### 🗺️ เปรียบเทียบภูมิภาค"
    )

    st.caption(
        "เลือกภาคจากกราฟใดก็ได้ "
        "แล้ว KPI แผนที่ และแท็บอื่นจะเปลี่ยนตาม"
    )

    comparison_metric = st.radio(
        "เลือกตัวชี้วัด",
        options=[
            "emp_rate",
            "unemp_rate",
            "avg_wage",
        ],
        format_func=lambda value: LABELS[value],
        horizontal=True,
        key="comparison_metric",
    )

    # All regions remain available,
    # even when a specific region is selected.
    comparison_frame = filter_frame(
        all_region_data,
        comparison_metric,
    )

    region_values = (
        comparison_frame["region"].astype(str).tolist()
        if not comparison_frame.empty
        else []
    )

    render_interactive_chart(
        create_regional_ranking_chart(
            comparison_frame,
            metric=comparison_metric,
            selected_region=(
                selected_region
                if region_selected
                else None
            ),
        ),
        "🏆 จัดอันดับภูมิภาค",
        "คลิกแท่งเพื่อกรองข้อมูลทั้ง Dashboard",
        "regional_ranking",
        dimension="region",
        valid_values=region_values,
    )

    left, right = st.columns(2)

    with left:

        scatter_frame = (
            all_region_data.dropna(
                subset=["avg_wage", "emp_rate"]
            ).copy()
        )

        scatter_regions = (
            scatter_frame["region"].astype(str).tolist()
            if not scatter_frame.empty
            else []
        )

        # Always display all regions. Highlight the selected one, without
        # hiding other regions or replacing the chart with KPI cards.
        scatter_fig = create_wage_vs_employment_scatter(
            scatter_frame,
            selected_region=selected_region if region_selected else None,
        )
        if scatter_fig is not None and region_selected:
            for trace in scatter_fig.data:
                focused = str(trace.name) == str(selected_region)
                trace.marker.opacity = 1.0 if focused else 0.24
                trace.marker.size = max(24, float(trace.marker.size) * 1.35) if focused else max(12, float(trace.marker.size) * 0.84)
                trace.marker.line.color = "#43334C" if focused else "#FFFFFF"
                trace.marker.line.width = 4 if focused else 1
                if focused:
                    trace.mode = "markers+text"
                    trace.text = [str(selected_region)]
                    trace.textposition = "top center"
                    trace.textfont = dict(color="#43334C", size=14, family="IBM Plex Sans Thai, sans-serif")

        render_interactive_chart(
            scatter_fig,
            "⚖️ ค่าจ้างเฉลี่ย vs อัตราการมีงานทำ",
            "คลิกจุดภูมิภาคเพื่อเลือกหรือเปลี่ยนภาค · ภาคที่เลือกจะเด่น และยังเห็นภาคอื่นครบ",
            "regional_scatter",
            dimension="region",
            valid_values=scatter_regions,
        )

    with right:

        area_data = get_area_wage_comparison_data(
            df, comparison_filters
        )

        area_regions = (
            area_data["region"].astype(str).tolist()
            if not area_data.empty
            else []
        )

        if region_selected:
            render_interactive_chart(
                _regional_municipal_yearly_figure(df, filters, selected_region, selected_year),
                f"🏙️ ค่าจ้างใน/นอกเขตเทศบาล: {selected_region}",
                "เปรียบเทียบค่าจ้างย้อนหลังตามปี · คลิกจุดปีเพื่อกรองทุกแท็บ · ปี 2567–2568 เป็นข้อมูลไม่ระบุไตรมาส",
                "regional_area_yearly",
                dimension="year",
                valid_values=list(range(START_YEAR, END_YEAR + 1)),
                drill_down=True,
            )
        else:
            render_interactive_chart(
                create_dumbbell_wage_chart(area_data),
                "🏙️ ค่าจ้างในเขต vs นอกเขตเทศบาล",
                "คลิกแท่งภูมิภาคเพื่อเปลี่ยนตัวกรองทุกแท็บ",
                "regional_area_wage",
                dimension="region",
                valid_values=area_regions,
            )


# ============================================================
# TAB 3 - DEMOGRAPHICS
# ============================================================

with tab3:

    st.markdown(
        "### 👥 วิเคราะห์กลุ่มแรงงาน"
    )

    st.caption(
        "ข้อมูลนี้เชื่อมกับปี ไตรมาส "
        "ภูมิภาค เพศ และกลุ่มอายุที่เลือก"
    )

    age_data = get_demographics_age_data(
        df, filters
    )

    left, right = st.columns(2)

    with left:
        _render_clickable_gender_donut(df, filters)

    with right:
        render_interactive_chart(
            create_all_years_heatmap(df, filters),
            "📊 โครงสร้างผู้มีงานทำตามเพศและอายุ",
            "จำนวนผู้มีงานทำ หน่วยล้านคน",
            "demographic_heatmap",
        )

    left, right = st.columns(2)

    with left:

        render_interactive_chart(
            create_age_wage_chart(
                age_data,
                selected_age=(
                    filters["age_group"]
                    if filters["age_group"] != ALL
                    else None
                ),
            ),
            "💵 ค่าจ้างเฉลี่ยตามช่วงอายุ",
            "คลิกช่วงอายุเพื่อเปลี่ยนตัวกรองทุกแท็บ",
            "age_wage",
            dimension="age_group",
            valid_values=[a for a in AGE_ORDER if a != "รวม"],
        )

    with right:

        with st.container(border=False, key="labor_card_age_unemployment"):
            st.markdown(
                "**🚨 อัตราการว่างงานตามช่วงอายุ**"
            )

            st.caption(
                "จัดอันดับจากมากไปน้อย "
                "คลิกแท่งเพื่อเลือกช่วงอายุ"
            )

            age_figure, summary = prepare_age_chart(
                age_data,
                selected_age=(
                    filters["age_group"]
                    if filters["age_group"] != ALL
                    else None
                ),
            )

            if summary is not None:
                top_age, top_rate = summary

                st.markdown(
                    f"""
                    <div class="age-insight">
                        <div class="label">
                            🏆 กลุ่มที่มีอัตราว่างงานสูงสุด
                        </div>
                        <div class="value">
                            {html.escape(top_age)}
                            · {top_rate:.2f}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if age_figure is None:
                st.info(
                    "ไม่มีข้อมูลตามช่วงอายุ"
                )
            else:

                age_key = (
                    "global_age_unemployment_"
                    f"{chart_version()}"
                )

                plot_chart(
                    age_figure,
                    key=age_key,
                    on_select=(
                        lambda k=age_key:
                        queue_chart_filter(
                            k,
                            "age_group",
                            [a for a in AGE_ORDER if a != "รวม"],
                        )
                    ),
                    selection_mode="points",
                )

            st.caption(
                "อัตราการว่างงานใช้กำลังแรงงาน"
                "เป็นฐาน ไม่ใช่ประชากรทั้งหมด"
            )


# ============================================================
# DATA NOTES
# ============================================================

st.markdown("""
<details class="labor-notes">
  <summary><span class="labor-notes-icon">ⓘ</span><span>แหล่งข้อมูลและข้อจำกัด</span><span class="labor-notes-chev">⌄</span></summary>
  <div class="labor-notes-body">
    <p><strong>แหล่งข้อมูล:</strong> สำนักงานสถิติแห่งชาติ (NSO)</p>
    <ul>
      <li>ใช้ข้อมูลเฉพาะปี พ.ศ. 2561–2568</li>
      <li>ไม่แก้ไขไฟล์ CSV ต้นฉบับ</li>
      <li>การคลิกปีบนกราฟแนวโน้มอัปเดต Global Filter</li>
      <li>ค่าจ้างปี 2567–2568 อยู่ใน quarter = 0 (ไม่แยกไตรมาส) และมีหลายค่าต่อกลุ่ม ระบบแสดงค่าเฉลี่ยของค่าที่รายงาน พร้อมเครื่องหมายสีส้ม</li>
      <li>จำนวนผู้มีงานทำหน่วยพันคน แสดงเป็นล้านคน และไม่มีข้อมูลแยกเขตเทศบาล</li>
      <li>การเลือกภูมิภาคและช่วงอายุใช้ตัวกรองร่วมกัน</li>
      <li>กราฟเปรียบเทียบภูมิภาคแสดงทุกภาค เพื่อให้คลิกสลับภาคได้</li>
      <li>ค่าอัตราร้อยละไม่ถูกบวกหรือเฉลี่ยโดยพลการ</li>
      <li>ข้อมูลบางชุดไม่มีครบทุกตัวกรอง</li>
      <li>แผนที่แสดงระดับภูมิภาค ไม่ใช่ระดับจังหวัด</li>
      <li>นิยามภูมิภาคก่อนและหลังปี 2568 อาจแตกต่างกัน</li>
    </ul>
  </div>
</details>
""", unsafe_allow_html=True)
