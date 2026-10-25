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


# Apply any incoming chart click first.
apply_pending_chart_filter()


# ============================================================
# GENERAL UTILITIES
# ============================================================

def plot_chart(fig, **kwargs):
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
    with st.container(border=True):
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
            <h3>📍 {html.escape(str(region))}</h3>
            <div>
                ข้อมูลตลาดแรงงาน ·
                {html.escape(str(period_label))}
            </div>
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
                <div class="detail-value">
                    {format_number(value, suffix)}
                </div>
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
            family="Kanit, sans-serif",
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

if current_year not in valid_years:
    current_filter_state["year"] = valid_years[0]

    st.session_state["filters"] = (
        current_filter_state
    )

    sidebar_year_key = SIDEBAR_KEYS.get("year")

    if sidebar_year_key is not None:
        st.session_state[
            sidebar_year_key
        ] = valid_years[0]

sanitize_filters(df)

filters = dict(get_current_filters())

selected_year = int(filters["year"])
selected_region = filters["region"]

# While the trend is in quarterly mode it always shows the GLOBAL
# year, so changing the year from the sidebar, a chip or a chart
# keeps every drill-down chart consistent.
if st.session_state.get("trend_drill_year") is not None:
    st.session_state["trend_drill_year"] = selected_year

region_selected = selected_region not in (
    ALL, None
)

available_regions = get_regions_for_year(
    df,
    selected_year,
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
        options=valid_years,
        key=SIDEBAR_KEYS["year"],
        on_change=on_sidebar_change,
        args=("year",),
    )

    st.selectbox(
        "⏱️ ไตรมาส",
        options=[
            ALL,
            *get_quarters_for_year(
                df, selected_year
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
    <div class="main-header-banner">
        <h1 class="main-header-title">
            🇹🇭 แดชบอร์ดวิเคราะห์ตลาดแรงงานไทย
        </h1>
        <p class="main-header-subtitle">
            วิเคราะห์ตลาดแรงงานไทย ปี พ.ศ. 2561–2568
        </p>
    </div>
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
    kpis.get("period_label")
    or f"ปี พ.ศ. {selected_year}"
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

render_active_filters(filters)


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

    map_metric = st.radio(
        "ตัวชี้วัดบนแผนที่",
        options=[
            "emp_rate",
            "unemp_rate",
            "avg_wage",
        ],
        format_func=lambda value: LABELS[value],
        horizontal=True,
        key="overview_map_metric",
    )

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
    map_box = st.container(border=True)

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
    if selected_year >= 2567:
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

    with st.container(border=True):

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

        if not drilled_now:
            wage_title = "💵 ค่าจ้างเฉลี่ยรายปี"
            wage_caption = (
                "ปี 2561–2566 ใช้ค่าจ้างของไตรมาสล่าสุดของปี · "
                "คลิกปีเพื่อดู Q1–Q4"
            )
        elif chart_year <= 2566:
            wage_title = f"💵 ค่าจ้างเฉลี่ยรายไตรมาส ปี {chart_year}"
            wage_caption = "คลิกแท่งเพื่อเปลี่ยนตัวกรองไตรมาส"
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

        render_interactive_chart(
            create_wage_vs_employment_scatter(
                scatter_frame,
                selected_region=(
                    selected_region
                    if region_selected
                    else None
                ),
            ),
            "⚖️ ค่าจ้างเฉลี่ย vs อัตราการมีงานทำ",
            "คลิกจุดของภูมิภาคเพื่อเปลี่ยนตัวกรอง",
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

        render_interactive_chart(
            create_dumbbell_wage_chart(
                area_data,
                selected_region=(
                    selected_region
                    if region_selected
                    else None
                ),
            ),
            "🏙️ ค่าจ้างในเขต vs นอกเขตเทศบาล",
            "คลิกแท่งของภูมิภาคเพื่อเปลี่ยนตัวกรอง",
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
        render_interactive_chart(
            create_gender_headcount_donut(
                df, filters
            ),
            "👫 สัดส่วนผู้มีงานทำแยกตามเพศ",
            "สัดส่วนจำนวนผู้มีงานทำชายและหญิง "
            "ภายใต้ตัวกรองปัจจุบัน",
            "gender_donut",
        )

    with right:
        render_interactive_chart(
            create_demographic_matrix_heatmap(
                df, filters
            ),
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

        with st.container(border=True):
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

st.markdown("---")

with st.expander(
    "📖 แหล่งข้อมูลและข้อจำกัด"
):
    st.markdown(
        """
        **แหล่งข้อมูล:** สำนักงานสถิติแห่งชาติ (NSO)

        - ใช้ข้อมูลเฉพาะปี พ.ศ. 2561–2568
        - ไม่แก้ไขไฟล์ CSV ต้นฉบับ
        - การคลิกปีบนกราฟแนวโน้มอัปเดต Global Filter
        - ค่าจ้างปี 2567–2568 อยู่ใน quarter = 0 (ไม่แยกไตรมาส)
          และมีหลายค่าต่อกลุ่ม ระบบแสดงค่าเฉลี่ยของค่าที่รายงาน
          พร้อมเครื่องหมายสีส้ม
        - จำนวนผู้มีงานทำหน่วยพันคน แสดงเป็นล้านคน
          และไม่มีข้อมูลแยกเขตเทศบาล
        - การเลือกภูมิภาคและช่วงอายุใช้ตัวกรองร่วมกัน
        - กราฟเปรียบเทียบภูมิภาคแสดงทุกภาค
          เพื่อให้คลิกสลับภาคได้
        - ค่าอัตราร้อยละไม่ถูกบวกหรือเฉลี่ยโดยพลการ
        - ข้อมูลบางชุดไม่มีครบทุกตัวกรอง
        - แผนที่แสดงระดับภูมิภาค ไม่ใช่ระดับจังหวัด
        - นิยามภูมิภาคก่อนและหลังปี 2568
          อาจแตกต่างกัน
        """
    )