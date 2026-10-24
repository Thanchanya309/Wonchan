
"""
Thailand Labor Market Dashboard - Plotly Charts

Compatible with latest app.py:
- Fixed-height interactive regional map
- Regional ranking and cross-filtering
- Yearly trend (click year for quarterly drill-down in app.py)
- Ranked age unemployment spotlight
- Gender donut, scatter, grouped wage bars and heatmap

Uses real data passed from the project's data and metrics modules.
"""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go


# ============================================================
# THEME AND CONSTANTS
# ============================================================

COLOR_PINK = "#E83C91"
COLOR_PURPLE = "#843A7D"
COLOR_DARK = "#43334C"
COLOR_BLUE = "#57A8F5"
COLOR_ORANGE = "#F7A531"
COLOR_MUTED = "#8C7B94"
COLOR_GRID = "#F0E8EE"
FONT = "Kanit, sans-serif"

MAP_COLORS = [
    [0.00, "#D95A9A"],
    [0.25, "#C54C9D"],
    [0.50, "#AA429B"],
    [0.75, "#873D92"],
    [1.00, "#633078"],
]

REGION_COLORS = {
    "กรุงเทพมหานคร": "#7541D9",
    "ภาคกลาง": "#F03284",
    "ภาคเหนือ": "#1595D2",
    "ภาคตะวันออกเฉียงเหนือ": "#E49A18",
    "ภาคใต้": "#159B84",
    "ภาคตะวันออก": "#D85342",
    "ภาคใต้ชายแดน": "#9250AB",
}

REGIONS_5 = [
    "กรุงเทพมหานคร",
    "ภาคกลาง",
    "ภาคเหนือ",
    "ภาคตะวันออกเฉียงเหนือ",
    "ภาคใต้",
]

REGIONS_7 = REGIONS_5 + [
    "ภาคตะวันออก",
    "ภาคใต้ชายแดน",
]

AGES = [
    "15-19 ปี",
    "20-24 ปี",
    "25-29 ปี",
    "30-34 ปี",
    "35-39 ปี",
    "40-49 ปี",
    "50-59 ปี",
    "60 ปีขึ้นไป",
]

METRIC_LABELS = {
    "avg_wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)",
    "emp_rate": "อัตราการมีงานทำ (%)",
    "unemp_rate": "อัตราการว่างงาน (%)",
}


# ============================================================
# COMMON HELPERS
# ============================================================

def _clean(frame, columns):
    if not isinstance(frame, pd.DataFrame):
        return pd.DataFrame(columns=columns)

    if frame.empty or not set(columns).issubset(frame.columns):
        return pd.DataFrame(columns=columns)

    return frame.dropna(subset=columns).copy()


def apply_chart_theme(fig, height=380, margin=None):
    if margin is None:
        margin = dict(l=45, r=30, t=55, b=45)

    fig.update_layout(
        height=height,
        margin=margin,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family=FONT,
            color=COLOR_DARK,
            size=12,
        ),
        hoverlabel=dict(
            bgcolor=COLOR_DARK,
            font=dict(
                family=FONT,
                size=12,
                color="white",
            ),
        ),
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.08,
            yanchor="bottom",
        ),
        clickmode="event+select",
        dragmode=False,
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor=COLOR_GRID,
        zeroline=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLOR_GRID,
        zeroline=False,
    )
    return fig


def _latest_per_year(frame, metric):
    """Latest valid quarterly observation in each year."""
    result = _clean(frame, ["year", "quarter", metric])

    if result.empty:
        return result

    result = result.sort_values(["year", "quarter"])
    return result.drop_duplicates("year", keep="last")


# ============================================================
# 1. ANNUAL EMPLOYMENT AND UNEMPLOYMENT
# ============================================================

def create_time_series_chart(ts_data):
    fig = go.Figure()

    for metric, label, color, axis in [
        ("emp_rate", "อัตราการมีงานทำ", COLOR_PINK, "y"),
        ("unemp_rate", "อัตราการว่างงาน", COLOR_PURPLE, "y2"),
    ]:
        frame = _latest_per_year(ts_data, metric)

        if frame.empty:
            continue

        fig.add_trace(go.Scatter(
            x=frame["year"].astype(int).astype(str),
            y=frame[metric],
            customdata=frame["year"].astype(int).tolist(),
            mode="lines+markers",
            name=label,
            yaxis=axis,
            line=dict(
                color=color,
                width=3,
                dash="dot" if metric == "unemp_rate" else "solid",
            ),
            marker=dict(size=8, color=color),
            hovertemplate=(
                "<b>ปี พ.ศ. %{x}</b>"
                "<br>" + label + ": %{y:.2f}%"
                "<extra></extra>"
            ),
        ))

    if not fig.data:
        return None

    fig = apply_chart_theme(
        fig,
        height=370,
        margin=dict(l=60, r=60, t=75, b=55),
    )

    fig.update_layout(
        hovermode="x unified",
        xaxis=dict(
            type="category",
            categoryorder="category ascending",
            title="ปี พ.ศ.",
            tickangle=0,
        ),
        yaxis=dict(
            title="อัตราการมีงานทำ (%)",
            tickfont=dict(color=COLOR_PINK),
        ),
        yaxis2=dict(
            title="อัตราการว่างงาน (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=COLOR_PURPLE),
        ),
    )
    return fig


# ============================================================
# 2. ANNUAL WAGE TREND
# ============================================================

def create_wage_trend_chart(ts_data, wage_data):
    frame = _clean(
        wage_data,
        ["year", "annual_avg_wage"],
    )

    if frame.empty:
        return None

    frame = frame.sort_values("year")

    fig = go.Figure(go.Scatter(
        x=frame["year"].astype(int).astype(str),
        y=frame["annual_avg_wage"],
        customdata=frame["year"].astype(int).tolist(),
        mode="lines+markers",
        name="ค่าจ้างเฉลี่ย",
        line=dict(color=COLOR_PURPLE, width=3),
        marker=dict(
            color=COLOR_PINK,
            size=9,
            line=dict(color="white", width=1.5),
        ),
        fill="tozeroy",
        fillcolor="rgba(232,60,145,0.10)",
        hovertemplate=(
            "<b>ปี พ.ศ. %{x}</b>"
            "<br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(
        xaxis=dict(type="category", title="ปี พ.ศ."),
        yaxis=dict(
            title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
            tickformat=",",
        ),
    )
    return fig


# ============================================================
# 3. ANNUAL EMPLOYED HEADCOUNT
# ============================================================

def create_headcount_trend_chart(ts_data):
    frame = _latest_per_year(ts_data, "emp_headcount_m")

    if frame.empty:
        return None

    fig = go.Figure(go.Bar(
        x=frame["year"].astype(int).astype(str),
        y=frame["emp_headcount_m"],
        customdata=frame["year"].astype(int).tolist(),
        marker=dict(
            color=COLOR_PINK,
            line=dict(color=COLOR_PURPLE, width=0.7),
        ),
        hovertemplate=(
            "<b>ปี พ.ศ. %{x}</b>"
            "<br>ผู้มีงานทำ: %{y:,.2f} ล้านคน"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(
        bargap=0.25,
        xaxis=dict(
            type="category",
            title="ปี พ.ศ.",
            showgrid=False,
        ),
        yaxis=dict(title="ผู้มีงานทำ (ล้านคน)"),
    )
    return fig


# ============================================================
# 4. QUARTERLY UNEMPLOYMENT
# ============================================================

def create_seasonality_chart(df, filters):
    year = int(filters.get("year", 2568))

    region = filters.get("region", "ทั้งหมด")
    area = filters.get("area", "ทั้งหมด")
    sex = filters.get("sex", "ทั้งหมด")
    age = filters.get("age_group", "ทั้งหมด")

    target_region = "รวม" if region == "ทั้งหมด" else region
    target_area = "รวม" if area == "ทั้งหมด" else area
    target_sex = "รวม" if sex == "ทั้งหมด" else sex
    target_age = "รวม" if age == "ทั้งหมด" else age

    if target_region == "กรุงเทพมหานคร" and target_area == "รวม":
        target_area = "ในเขตเทศบาล"

    frame = df[
        (df["year"] == year)
        & (df["clean_region"] == target_region)
        & (df["clean_area"] == target_area)
        & (df["clean_sex"] == target_sex)
        & (df["clean_age"] == target_age)
        & df["quarter"].isin([1, 2, 3, 4])
        & df["unemp_rate"].notna()
    ]

    if frame.empty:
        return None

    rows = []
    for quarter, group in frame.groupby("quarter"):
        values = pd.to_numeric(
            group["unemp_rate"], errors="coerce"
        ).dropna().unique()

        if len(values) == 1:
            rows.append({
                "quarter": int(quarter),
                "unemp_rate": float(values[0]),
            })

    if not rows:
        return None

    result = pd.DataFrame(rows).sort_values("quarter")

    colors = {
        1: "#F062A6",
        2: "#D94691",
        3: "#B54A9C",
        4: "#783A91",
    }

    fig = go.Figure(go.Bar(
        x=[f"Q{int(q)}" for q in result["quarter"]],
        y=result["unemp_rate"],
        customdata=result["quarter"].astype(int).tolist(),
        marker_color=[colors[q] for q in result["quarter"]],
        hovertemplate=(
            "<b>%{x}</b>"
            "<br>อัตราว่างงาน: %{y:.2f}%"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=340)
    fig.update_layout(
        xaxis=dict(title="ไตรมาส"),
        yaxis=dict(title="อัตราการว่างงาน (%)"),
    )
    return fig


# ============================================================
# 5. REGIONAL RANKING
# ============================================================

def create_regional_ranking_chart(
    reg_data,
    metric="avg_wage",
    selected_region=None,
):
    frame = _clean(reg_data, ["region", metric])

    if frame.empty:
        return None

    frame = frame.sort_values(metric, ascending=True)

    colors = [
        COLOR_PINK if r == selected_region else COLOR_PURPLE
        for r in frame["region"]
    ]

    fig = go.Figure(go.Bar(
        x=frame[metric],
        y=frame["region"],
        orientation="h",
        customdata=frame["region"].astype(str).tolist(),
        marker=dict(
            color=colors,
            line=dict(color="white", width=0.8),
        ),
        text=[f"{v:,.2f}" for v in frame[metric]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{y}</b>"
            "<br>" + METRIC_LABELS.get(metric, metric)
            + ": %{x:,.2f}"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(
        fig,
        height=390,
        margin=dict(l=155, r=65, t=40, b=55),
    )
    fig.update_layout(
        xaxis=dict(
            title=METRIC_LABELS.get(metric, metric),
            tickformat=",",
            rangemode="tozero",
        ),
        yaxis=dict(showgrid=False),
    )
    return fig


# ============================================================
# 6. WAGE VS EMPLOYMENT SCATTER
# ============================================================

def create_wage_vs_employment_scatter(
    reg_data,
    selected_region=None,
):
    frame = _clean(
        reg_data,
        ["region", "avg_wage", "emp_rate"],
    )

    if frame.empty:
        return None

    fig = go.Figure()

    for _, row in frame.iterrows():
        region = str(row["region"])
        headcount = row.get("headcount_m")

        try:
            size = (
                float(np.clip(float(headcount) * 8, 13, 46))
                if pd.notna(headcount)
                else 18
            )
        except (ValueError, TypeError):
            size = 18

        selected = region == selected_region

        fig.add_trace(go.Scatter(
            x=[float(row["avg_wage"])],
            y=[float(row["emp_rate"])],
            mode="markers",
            name=region,
            customdata=[region],
            marker=dict(
                color=REGION_COLORS.get(region, COLOR_PURPLE),
                size=size,
                opacity=0.95,
                line=dict(
                    color="#442050" if selected else "white",
                    width=3.5 if selected else 1.5,
                ),
            ),
            hovertemplate=(
                "<b>" + region + "</b>"
                "<br>ค่าจ้างเฉลี่ย: %{x:,.2f} บาท/เดือน"
                "<br>อัตราการมีงานทำ: %{y:.2f}%"
                "<extra></extra>"
            ),
        ))

    fig = apply_chart_theme(
        fig,
        height=440,
        margin=dict(l=65, r=30, t=110, b=60),
    )
    fig.update_layout(
        legend=dict(
            title="ภูมิภาค",
            orientation="h",
            x=0,
            xanchor="left",
            y=1.04,
            yanchor="bottom",
            font=dict(size=11),
        ),
        xaxis=dict(
            title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
            tickformat=",",
        ),
        yaxis=dict(title="อัตราการมีงานทำ (%)"),
    )
    return fig


# ============================================================
# 7. MUNICIPAL WAGES - GROUPED HORIZONTAL BARS
# ============================================================

def create_dumbbell_wage_chart(
    area_data,
    selected_region=None,
):
    """
    Kept original function name for app.py compatibility.
    Visualization is grouped bars, not a dumbbell.
    """
    frame = _clean(
        area_data,
        ["region", "wage_in", "wage_out"],
    )

    if frame.empty:
        return None

    frame = frame.sort_values("wage_in", ascending=True)
    regions = frame["region"].astype(str).tolist()

    fig = go.Figure()

    for column, label, color in [
        ("wage_out", "นอกเขตเทศบาล", "#713574"),
        ("wage_in", "ในเขตเทศบาล", "#E83C91"),
    ]:
        fig.add_trace(go.Bar(
            y=regions,
            x=frame[column],
            orientation="h",
            name=label,
            customdata=regions,
            marker=dict(
                color=color,
                line=dict(color="white", width=0.8),
            ),
            hovertemplate=(
                "<b>%{y}</b>"
                "<br>" + label + ": %{x:,.2f} บาท/เดือน"
                "<extra></extra>"
            ),
        ))

    fig = apply_chart_theme(
        fig,
        height=435,
        margin=dict(l=170, r=25, t=80, b=55),
    )
    fig.update_layout(
        barmode="group",
        bargap=0.28,
        bargroupgap=0.08,
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.07,
            yanchor="bottom",
        ),
        xaxis=dict(
            title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
            tickformat=",",
            rangemode="tozero",
        ),
        yaxis=dict(showgrid=False),
    )
    return fig


# ============================================================
# 8. LEGACY GENDER WAGE CHART
# ============================================================

def create_gender_gap_chart(
    gender_data,
    selected_sex=None,
):
    frame = _clean(gender_data, ["sex", "avg_wage"])

    if frame.empty:
        return None

    fig = go.Figure(go.Bar(
        x=frame["sex"],
        y=frame["avg_wage"],
        customdata=frame["sex"].astype(str).tolist(),
        marker_color=[
            COLOR_BLUE if s == "ชาย" else COLOR_PINK
            for s in frame["sex"]
        ],
        hovertemplate=(
            "<b>เพศ%{x}</b>"
            "<br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=340)
    fig.update_yaxes(
        title_text="ค่าจ้างเฉลี่ย (บาท/เดือน)",
        tickformat=",",
    )
    return fig


# ============================================================
# 9. GENDER HEADCOUNT DONUT
# ============================================================

def create_gender_headcount_donut(df, filters):
    year = int(filters.get("year", 2568))
    quarter = filters.get("quarter", "ทั้งหมด")
    region = filters.get("region", "ทั้งหมด")
    age = filters.get("age_group", "ทั้งหมด")
    sex = filters.get("sex", "ทั้งหมด")

    frame = df[
        (df["year"] == year)
        & (df["quarter"] > 0)
        & df["emp_headcount"].notna()
        & df["clean_sex"].isin(["ชาย", "หญิง"])
    ].copy()

    if region == "ทั้งหมด":
        regions = REGIONS_7 if year >= 2568 else REGIONS_5
        frame = frame[frame["clean_region"].isin(regions)]
    else:
        frame = frame[frame["clean_region"] == region]

    if age == "ทั้งหมด":
        frame = frame[frame["clean_age"].isin(AGES)]
    else:
        frame = frame[frame["clean_age"] == age]

    if sex != "ทั้งหมด":
        frame = frame[frame["clean_sex"] == sex]

    if quarter != "ทั้งหมด":
        frame = frame[frame["quarter"] == int(quarter)]
    elif not frame.empty:
        frame = frame[
            frame["quarter"] == frame["quarter"].max()
        ]

    if frame.empty:
        return None

    keys = [
        "year", "quarter", "clean_region",
        "clean_sex", "clean_age",
    ]

    conflicts = frame.groupby(
        keys, dropna=False
    )["emp_headcount"].nunique()

    if (conflicts > 1).any():
        return None

    frame = frame.drop_duplicates(subset=keys)

    counts = (
        frame.groupby("clean_sex")["emp_headcount"]
        .sum()
        .reindex(["ชาย", "หญิง"])
        .dropna()
    )

    counts = counts[counts > 0]

    if counts.empty:
        return None

    total_million = counts.sum() / 1000.0

    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.68,
        sort=False,
        marker=dict(
            colors=[
                COLOR_BLUE if s == "ชาย" else COLOR_PINK
                for s in counts.index
            ],
            line=dict(color="white", width=2),
        ),
        textinfo="percent",
        textposition="inside",
        hovertemplate=(
            "<b>%{label}</b>"
            "<br>จำนวนผู้มีงานทำ: %{value:,.1f} พันคน"
            "<br>สัดส่วน: %{percent}"
            "<extra></extra>"
        ),
    ))

    fig.add_annotation(
        x=0.5,
        y=0.46,
        xref="paper",
        yref="paper",
        showarrow=False,
        text=f"<b>{total_million:,.2f}</b><br>ล้านคน",
        font=dict(
            family=FONT,
            color=COLOR_DARK,
            size=20,
        ),
    )

    fig = apply_chart_theme(
        fig,
        height=410,
        margin=dict(l=20, r=20, t=80, b=10),
    )
    fig.update_layout(
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=1.06,
            yanchor="bottom",
            title=None,
        ),
    )
    fig.update_traces(
        domain=dict(x=[0.08, 0.92], y=[0.03, 0.92]),
        selector=dict(type="pie"),
    )
    return fig


# ============================================================
# 10. WAGE BY AGE
# ============================================================

def create_age_wage_chart(
    age_data,
    selected_age=None,
):
    frame = _clean(
        age_data,
        ["age_group", "avg_wage"],
    )

    if frame.empty:
        return None

    fig = go.Figure(go.Scatter(
        x=frame["age_group"],
        y=frame["avg_wage"],
        customdata=frame["age_group"].astype(str).tolist(),
        mode="lines+markers",
        line=dict(color=COLOR_PURPLE, width=3),
        marker=dict(
            size=10,
            color=[
                COLOR_PURPLE if a == selected_age else COLOR_PINK
                for a in frame["age_group"]
            ],
            line=dict(color="white", width=1.5),
        ),
        fill="tozeroy",
        fillcolor="rgba(232,60,145,0.08)",
        hovertemplate=(
            "<b>กลุ่มอายุ %{x}</b>"
            "<br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=350)
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(
        title_text="ค่าจ้างเฉลี่ย (บาท/เดือน)",
        tickformat=",",
    )
    return fig


# ============================================================
# 11. AGE UNEMPLOYMENT INSIGHT + RANKED BARS
# ============================================================

def create_youth_unemployment_chart(
    age_data,
    selected_age=None,
):
    """
    Ranked unemployment rates by age.

    - Strong headline identifying the highest reported rate.
    - Horizontal bars sorted high to low.
    - Pink highlights youth (15-19 and 20-24).
    - Plotly customdata retains age-group cross-filtering.

    IMPORTANT:
    These are unemployment rates, not counts of unemployed people.
    """
    frame = _clean(
        age_data,
        ["age_group", "unemp_rate"],
    )

    if frame.empty:
        return None

    frame["unemp_rate"] = pd.to_numeric(
        frame["unemp_rate"], errors="coerce"
    )
    frame = frame.dropna(subset=["unemp_rate"])

    if frame.empty:
        return None

    # Each age group should have one reported rate.
    # Conflicting values are excluded, rather than averaged.
    rows = []
    for age, group in frame.groupby("age_group", sort=False):
        values = group["unemp_rate"].dropna().unique()

        if len(values) == 1:
            rows.append({
                "age_group": str(age),
                "unemp_rate": float(values[0]),
            })

    if not rows:
        return None

    ranked = pd.DataFrame(rows).sort_values(
        "unemp_rate",
        ascending=False,
    ).reset_index(drop=True)

    top = ranked.iloc[0]
    top_age = str(top["age_group"])
    top_rate = float(top["unemp_rate"])

    max_rate = max(float(ranked["unemp_rate"].max()), 0.1)

    colors = []
    borders = []
    widths = []

    for age in ranked["age_group"]:
        if age == selected_age:
            colors.append("#713574")
            borders.append("#48234D")
            widths.append(2)
        elif age == "15-19 ปี":
            colors.append("#E83C91")
            borders.append("#E83C91")
            widths.append(0)
        elif age == "20-24 ปี":
            colors.append("#F062A6")
            borders.append("#F062A6")
            widths.append(0)
        else:
            colors.append("#BA9ACB")
            borders.append("#BA9ACB")
            widths.append(0)

    fig = go.Figure(go.Bar(
        x=ranked["unemp_rate"],
        y=ranked["age_group"],
        orientation="h",
        customdata=ranked["age_group"].tolist(),
        marker=dict(
            color=colors,
            line=dict(
                color=borders,
                width=widths,
            ),
        ),
        text=[
            f"{value:.2f}%"
            for value in ranked["unemp_rate"]
        ],
        textposition="outside",
        textfont=dict(
            family=FONT,
            color=COLOR_DARK,
            size=12,
        ),
        cliponaxis=False,
        hovertemplate=(
            "<b>อายุ %{y}</b>"
            "<br>อัตราการว่างงาน: %{x:.2f}%"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(
        fig,
        height=515,
        margin=dict(
            l=110,
            r=65,
            t=125,
            b=55,
        ),
    )

    fig.update_layout(
        bargap=0.42,
        showlegend=False,
        xaxis=dict(
            title="อัตราการว่างงาน (%)",
            range=[0, max_rate * 1.22],
            tickformat=".1f",
            ticksuffix="%",
            gridcolor="#F0E8EE",
            zeroline=False,
        ),
        yaxis=dict(
            title=None,
            autorange="reversed",
            showgrid=False,
            categoryorder="array",
            categoryarray=ranked["age_group"].tolist(),
        ),
    )

    # Insight heading is a visualization annotation, not a statistic
    # computed from a different dataset.
    fig.add_annotation(
        x=0,
        y=1.29,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        text=(
            "<b>กลุ่มที่มีอัตราว่างงานสูงสุด</b>"
            f"<br><span style='font-size:22px;color:#D52D86'>"
            f"{top_age} · {top_rate:.2f}%</span>"
        ),
        showarrow=False,
        align="left",
        font=dict(
            family=FONT,
            size=13,
            color=COLOR_DARK,
        ),
    )

    fig.add_annotation(
        x=0,
        y=-0.24,
        xref="paper",
        yref="paper",
        xanchor="left",
        text=(
            "สีชมพูเน้นกลุ่มอายุ 15–24 ปี · "
            "คลิกแท่งเพื่อกรองอายุทั้ง Dashboard"
        ),
        showarrow=False,
        align="left",
        font=dict(
            family=FONT,
            size=11,
            color=COLOR_MUTED,
        ),
    )

    return fig


# ============================================================
# 12. EMPLOYED HEADCOUNT BY SEX AND AGE
# ============================================================

def create_demographic_matrix_heatmap(df, filters):
    year = int(filters.get("year", 2568))
    quarter = filters.get("quarter", "ทั้งหมด")
    region = filters.get("region", "ทั้งหมด")
    sex = filters.get("sex", "ทั้งหมด")
    age = filters.get("age_group", "ทั้งหมด")

    sexes = ["ชาย", "หญิง"] if sex == "ทั้งหมด" else [sex]
    ages = AGES if age == "ทั้งหมด" else [age]

    frame = df[
        (df["year"] == year)
        & (df["quarter"] > 0)
        & df["emp_headcount"].notna()
        & df["clean_sex"].isin(sexes)
        & df["clean_age"].isin(ages)
    ].copy()

    if region == "ทั้งหมด":
        regions = REGIONS_7 if year >= 2568 else REGIONS_5
        frame = frame[frame["clean_region"].isin(regions)]
    else:
        frame = frame[frame["clean_region"] == region]

    if quarter != "ทั้งหมด":
        frame = frame[frame["quarter"] == int(quarter)]
    elif not frame.empty:
        frame = frame[
            frame["quarter"] == frame["quarter"].max()
        ]

    if frame.empty:
        return None

    keys = [
        "year", "quarter", "clean_region",
        "clean_sex", "clean_age",
    ]

    conflicts = frame.groupby(
        keys, dropna=False
    )["emp_headcount"].nunique()

    if (conflicts > 1).any():
        return None

    frame = frame.drop_duplicates(subset=keys)

    grouped = (
        frame.groupby(["clean_sex", "clean_age"])["emp_headcount"]
        .sum()
        .reset_index()
    )

    pivot = grouped.pivot(
        index="clean_sex",
        columns="clean_age",
        values="emp_headcount",
    ).reindex(index=sexes, columns=ages)

    if pivot.notna().sum().sum() == 0:
        return None

    pivot = pivot / 1000.0

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=ages,
        y=sexes,
        colorscale=[
            [0.00, "#FFF0F7"],
            [0.25, "#F49AC2"],
            [0.55, "#D94691"],
            [1.00, "#713574"],
        ],
        hoverongaps=False,
        colorbar=dict(title="ล้านคน"),
        hovertemplate=(
            "<b>เพศ%{y} · อายุ %{x}</b>"
            "<br>ผู้มีงานทำ: %{z:.2f} ล้านคน"
            "<extra></extra>"
        ),
    ))

    fig = apply_chart_theme(fig, height=300)
    fig.update_xaxes(tickangle=-25)
    fig.update_yaxes(showgrid=False)
    return fig


# ============================================================
# 13. THAILAND REGIONAL MAP
# ============================================================

@lru_cache(maxsize=2)
def _load_regional_geojson(year_group):
    """Merge provincial polygons into actual regions."""
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
    except ImportError:
        return None

    path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "thailand_regions.geojson"
    )

    if not path.is_file():
        return None

    try:
        with path.open("r", encoding="utf-8") as file:
            source = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    field = "region_7" if year_group == 7 else "region_5"
    groups = {}

    for feature in source.get("features", []):
        region = feature.get("properties", {}).get(field)
        geometry = feature.get("geometry")

        if not region or not geometry:
            continue

        try:
            polygon = shape(geometry)
        except (ValueError, TypeError):
            continue

        if polygon.is_empty:
            continue

        groups.setdefault(region, []).append(polygon)

    if not groups:
        return None

    polygons = {
        name: unary_union(geometries)
        for name, geometries in groups.items()
    }

    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"region": name},
                "geometry": mapping(geometry),
            }
            for name, geometry in polygons.items()
        ],
    }

    return geojson, polygons


def create_thailand_map(
    reg_data,
    metric="avg_wage",
    year=2568,
    selected_region="ทั้งหมด",
    height=550,
):
    """
    Fixed-height map. Only geographic extent changes
    when a region is selected.

    Note: Browser support for Plotly Choropleth point
    selection must be tested in the actual Streamlit app.
    """
    from shapely.ops import unary_union

    year = int(year)
    group = 7 if year >= 2568 else 5

    loaded = _load_regional_geojson(group)

    if loaded is None:
        return None

    geojson, polygons = loaded

    frame = _clean(reg_data, ["region", metric])

    if frame.empty:
        return None

    frame[metric] = pd.to_numeric(
        frame[metric], errors="coerce"
    )
    frame = frame.dropna(subset=[metric])
    frame = frame[
        frame["region"].isin(polygons)
    ].drop_duplicates("region")

    if frame.empty:
        return None

    label = METRIC_LABELS.get(metric, metric)
    values = frame[metric].astype(float)

    low = float(values.min())
    high = float(values.max())

    if low == high:
        high = low + 1

    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=frame["region"].tolist(),
        z=values.tolist(),
        customdata=[
            [str(region)] for region in frame["region"]
        ],
        featureidkey="properties.region",
        colorscale=MAP_COLORS,
        zmin=low,
        zmax=high,
        marker=dict(
            line=dict(color="white", width=2)
        ),
        colorbar=dict(
            title=dict(text=label),
            thickness=12,
            len=0.65,
            x=1.01,
            xpad=4,
        ),
        hovertemplate=(
            "<b>%{location}</b>"
            "<br>" + label + ": %{z:,.2f}"
            "<extra></extra>"
        ),
    ))

    if selected_region in polygons:
        target = polygons[selected_region]

        if target.geom_type == "Polygon":
            pieces = [target]
        elif target.geom_type == "MultiPolygon":
            pieces = list(target.geoms)
        else:
            pieces = []

        for piece in pieces:
            xs, ys = piece.exterior.xy

            fig.add_trace(go.Scattergeo(
                lon=list(xs),
                lat=list(ys),
                mode="lines",
                line=dict(
                    color="#55206C",
                    width=3.5,
                ),
                hoverinfo="skip",
                showlegend=False,
            ))

        bounds = target.bounds
        padding = 0.13

    else:
        bounds = unary_union(list(polygons.values())).bounds
        padding = 0.045

    min_lon, min_lat, max_lon, max_lat = bounds
    lon_span = max(max_lon - min_lon, 0.7)
    lat_span = max(max_lat - min_lat, 0.7)

    fig.update_geos(
        projection_type="mercator",
        lonaxis_range=[
            min_lon - lon_span * padding,
            max_lon + lon_span * padding,
        ],
        lataxis_range=[
            min_lat - lat_span * padding,
            max_lat + lat_span * padding,
        ],
        domain=dict(x=[0, 0.88], y=[0, 1]),
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        showcoastlines=False,
        showland=False,
        showcountries=False,
    )

    fig.update_layout(
        height=int(height),
        autosize=False,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family=FONT, color=COLOR_DARK),
        paper_bgcolor="rgba(0,0,0,0)",
        clickmode="event+select",
        dragmode=False,
        uirevision=f"map_{year}_{selected_region}_{metric}",
    )

    return fig
