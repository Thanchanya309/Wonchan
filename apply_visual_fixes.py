
"""
One-time visual fixes for Thailand Labor Dashboard.
Run from the project root.

Updates:
- Year-only headcount chart
- Year-only employment/unemployment trend
- Real employed-population gender donut
- Clearer scatter labels/legend
- Municipal wage chart explanation
- More distinctive regional details card

Makes backup copies before changing existing files.
"""

from pathlib import Path
import ast
import shutil
import textwrap


ROOT = Path(__file__).resolve().parent
CHARTS = ROOT / "src" / "charts.py"
APP = ROOT / "app.py"

for path in (CHARTS, APP):
    if not path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์ {path}")


REPLACEMENTS = {
"create_headcount_trend_chart": '''
def create_headcount_trend_chart(ts_data):
    """One bar per year using its latest available quarter."""
    frame = _clean(
        ts_data,
        ["year", "quarter", "emp_headcount_m"],
    )
    if frame.empty:
        return None

    frame = frame.sort_values(["year", "quarter"])
    frame = frame.drop_duplicates("year", keep="last")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=frame["year"].astype(int).astype(str),
        y=frame["emp_headcount_m"],
        customdata=frame["year"].astype(int).tolist(),
        marker=dict(
            color="#E83C91",
            line=dict(color="#843A7D", width=0.8),
        ),
        hovertemplate=(
            "<b>ปี พ.ศ. %{x}</b>"
            "<br>ผู้มีงานทำ: %{y:,.2f} ล้านคน"
            "<extra></extra>"
        ),
    ))
    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(
        bargap=0.22,
        xaxis=dict(
            title="ปี พ.ศ.",
            type="category",
            tickangle=0,
            showgrid=False,
        ),
        yaxis=dict(title="ล้านคน"),
    )
    return fig
''',

"create_time_series_chart": '''
def create_time_series_chart(ts_data):
    """Yearly rates; latest available quarter in each year."""
    if not isinstance(ts_data, pd.DataFrame) or ts_data.empty:
        return None

    fig = go.Figure()

    for metric, name, color, axis in [
        ("emp_rate", "อัตราการมีงานทำ", "#E83C91", "y"),
        ("unemp_rate", "อัตราการว่างงาน", "#843A7D", "y2"),
    ]:
        frame = _clean(ts_data, ["year", "quarter", metric])
        if frame.empty:
            continue

        frame = frame.sort_values(["year", "quarter"])
        frame = frame.drop_duplicates("year", keep="last")

        fig.add_trace(go.Scatter(
            x=frame["year"].astype(int).astype(str),
            y=frame[metric],
            customdata=frame["year"].astype(int).tolist(),
            name=name,
            mode="lines+markers",
            line=dict(
                color=color,
                width=3,
                dash="dot" if metric == "unemp_rate" else "solid",
            ),
            marker=dict(size=8, color=color),
            yaxis=axis,
            hovertemplate=(
                "<b>ปี พ.ศ. %{x}</b>"
                "<br>" + name + ": %{y:.2f}%"
                "<extra></extra>"
            ),
        ))

    if not fig.data:
        return None

    fig = apply_chart_theme(fig, height=360)
    fig.update_layout(
        xaxis=dict(
            title="ปี พ.ศ.",
            type="category",
            tickangle=0,
            showgrid=True,
        ),
        yaxis=dict(
            title="อัตราการมีงานทำ (%)",
            tickfont=dict(color="#E83C91"),
        ),
        yaxis2=dict(
            title="อัตราการว่างงาน (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color="#843A7D"),
        ),
        hovermode="x unified",
    )
    return fig
''',

"create_wage_vs_employment_scatter": '''
def create_wage_vs_employment_scatter(
    reg_data,
    selected_region=None,
):
    """
    Keep the actual values, move region names into the legend
    to prevent overlapping labels on nearby points.
    """
    frame = _clean(
        reg_data, ["region", "avg_wage", "emp_rate"]
    )
    if frame.empty:
        return None

    fig = go.Figure()
    palette = [
        "#9540A5", "#D94691", "#713574",
        "#B54A9C", "#F062A6", "#AE3D74",
        "#783A91",
    ]

    for i, (_, row) in enumerate(frame.iterrows()):
        region = str(row["region"])
        hc = row.get("headcount_m")
        try:
            size = (
                float(np.clip(float(hc) * 8, 14, 46))
                if pd.notna(hc)
                else 19
            )
        except (TypeError, ValueError):
            size = 19

        selected = region == selected_region
        fig.add_trace(go.Scatter(
            x=[row["avg_wage"]],
            y=[row["emp_rate"]],
            mode="markers",
            name=region,
            customdata=[region],
            marker=dict(
                size=size,
                color="#E83C91" if selected else palette[i % len(palette)],
                opacity=0.95,
                line=dict(
                    color="#55206C" if selected else "#FFFFFF",
                    width=3 if selected else 1.5,
                ),
            ),
            hovertemplate=(
                "<b>" + region + "</b>"
                "<br>ค่าจ้างเฉลี่ย: %{x:,.2f} บาท/เดือน"
                "<br>อัตรามีงานทำ: %{y:.2f}%"
                "<extra></extra>"
            ),
        ))

    fig = apply_chart_theme(
        fig, height=410,
        margin=dict(l=60, r=25, t=80, b=65)
    )
    fig.update_layout(
        legend=dict(
            title="ภูมิภาค (สีของจุด)",
            orientation="h",
            x=0,
            xanchor="left",
            y=1.03,
            yanchor="bottom",
            font=dict(size=11),
        ),
        xaxis=dict(
            title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
            tickformat=",",
        ),
        yaxis=dict(
            title="อัตราการมีงานทำ (%)",
        ),
    )
    return fig
''',

"create_dumbbell_wage_chart": '''
def create_dumbbell_wage_chart(
    area_data,
    selected_region=None,
):
    """Paired regional wage observations with readable labels."""
    frame = _clean(
        area_data, ["region", "wage_in", "wage_out"]
    )
    if frame.empty:
        return None

    fig = go.Figure()
    for _, row in frame.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["wage_out"], row["wage_in"]],
            y=[row["region"], row["region"]],
            mode="lines",
            line=dict(color="#D4B9CF", width=4),
            hoverinfo="skip",
            showlegend=False,
        ))

    for col, title, color, symbol in [
        ("wage_out", "นอกเขตเทศบาล", "#843A7D", "circle"),
        ("wage_in", "ในเขตเทศบาล", "#E83C91", "diamond"),
    ]:
        fig.add_trace(go.Scatter(
            x=frame[col],
            y=frame["region"],
            mode="markers",
            name=title,
            customdata=frame["region"].tolist(),
            marker=dict(
                size=13,
                color=color,
                symbol=symbol,
                line=dict(color="white", width=1.5),
            ),
            hovertemplate=(
                "<b>%{y}</b><br>"
                + title +
                ": %{x:,.2f} บาท/เดือน"
                "<extra></extra>"
            ),
        ))

    fig = apply_chart_theme(
        fig, height=390,
        margin=dict(l=170, r=45, t=55, b=55),
    )
    fig.update_layout(
        xaxis=dict(
            title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
            tickformat=",",
        ),
        yaxis=dict(showgrid=False),
        legend=dict(
            orientation="h",
            y=1.10,
            x=0,
        ),
    )
    return fig
''',

"create_gender_headcount_donut": '''
def create_gender_headcount_donut(df, filters):
    """Donut of actual employed population by sex, not wage averages."""
    year = int(filters.get("year", 2568))
    quarter = filters.get("quarter", "ทั้งหมด")
    region = filters.get("region", "ทั้งหมด")
    age = filters.get("age_group", "ทั้งหมด")

    frame = df[
        (df["year"] == year)
        & (df["quarter"] > 0)
        & df["emp_headcount"].notna()
        & df["clean_sex"].isin(["ชาย", "หญิง"])
    ].copy()

    if region != "ทั้งหมด":
        frame = frame[frame["clean_region"] == region]
    else:
        if year < 2568:
            regions = [
                "กรุงเทพมหานคร", "ภาคกลาง", "ภาคเหนือ",
                "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้",
            ]
        else:
            regions = [
                "กรุงเทพมหานคร", "ภาคกลาง", "ภาคเหนือ",
                "ภาคตะวันออกเฉียงเหนือ", "ภาคใต้",
                "ภาคตะวันออก", "ภาคใต้ชายแดน",
            ]
        frame = frame[frame["clean_region"].isin(regions)]

    if age != "ทั้งหมด":
        frame = frame[frame["clean_age"] == age]
    else:
        frame = frame[frame["clean_age"].isin([
            "15-19 ปี", "20-24 ปี", "25-29 ปี",
            "30-34 ปี", "35-39 ปี", "40-49 ปี",
            "50-59 ปี", "60 ปีขึ้นไป",
        ])]

    selected_sex = filters.get("sex", "ทั้งหมด")
    if selected_sex != "ทั้งหมด":
        frame = frame[frame["clean_sex"] == selected_sex]

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
    counts = frame.groupby("clean_sex")["emp_headcount"].sum()

    counts = counts.reindex(["ชาย", "หญิง"]).dropna()
    counts = counts[counts > 0]

    if counts.empty:
        return None

    fig = go.Figure(go.Pie(
        labels=counts.index.tolist(),
        values=counts.values.tolist(),
        hole=0.67,
        marker=dict(
            colors=[
                "#57A8F5" if s == "ชาย" else "#E83C91"
                for s in counts.index
            ],
            line=dict(color="#FFFFFF", width=2),
        ),
        textinfo="percent",
        textposition="inside",
        customdata=counts.index.tolist(),
        hovertemplate=(
            "<b>%{label}</b>"
            "<br>ผู้มีงานทำ: %{value:,.1f} พันคน"
            "<br>สัดส่วน: %{percent}"
            "<extra></extra>"
        ),
        sort=False,
    ))

    total_m = counts.sum() / 1000.0
    fig.add_annotation(
        text=f"<b>{total_m:,.2f}</b><br>ล้านคน",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(
            family="Kanit, sans-serif",
            color="#43334C",
            size=19,
        ),
    )
    fig = apply_chart_theme(
        fig, height=340,
        margin=dict(l=10, r=10, t=15, b=15),
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            xanchor="center",
            y=-0.02,
        ),
    )
    return fig
''',
}


def replace_functions(source, replacements):
    """Replace whole top-level functions using Python AST boundaries."""
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    edits = []
    found = set()

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name not in replacements:
            continue
        replacement = textwrap.dedent(replacements[node.name]).strip() + "\n\n"
        # Decorators, if present, belong to the function definition.
        start = min(
            [node.lineno] + [d.lineno for d in node.decorator_list]
        ) - 1
        end = node.end_lineno
        edits.append((start, end, replacement))
        found.add(node.name)

    for start, end, replacement in reversed(edits):
        lines[start:end] = [replacement]

    return "".join(lines), found


charts_source = CHARTS.read_text(encoding="utf-8")

# Replace the four existing chart functions. The donut is added later.
chart_updates = {
    k: v for k, v in REPLACEMENTS.items()
    if k != "create_gender_headcount_donut"
}
updated_charts, found = replace_functions(charts_source, chart_updates)

missing = set(chart_updates) - found
if missing:
    raise RuntimeError(
        "ไม่พบฟังก์ชันใน charts.py: " + ", ".join(sorted(missing))
    )

if "def create_gender_headcount_donut(" in updated_charts:
    updated_charts, _ = replace_functions(
        updated_charts,
        {"create_gender_headcount_donut":
         REPLACEMENTS["create_gender_headcount_donut"]}
    )
else:
    updated_charts += (
        "\n\n" +
        textwrap.dedent(
            REPLACEMENTS["create_gender_headcount_donut"]
        ).strip() +
        "\n"
    )

ast.parse(updated_charts)

app_source = APP.read_text(encoding="utf-8")

# Modify the app's existing import safely.
old_import = "    create_gender_gap_chart,"
new_import = (
    "    create_gender_gap_chart,\n"
    "    create_gender_headcount_donut,"
)

if "create_gender_headcount_donut" not in app_source:
    if old_import not in app_source:
        raise RuntimeError(
            "หา import create_gender_gap_chart ใน app.py ไม่พบ"
        )
    app_source = app_source.replace(old_import, new_import, 1)

old_chart = "create_gender_gap_chart(gender_data, selected_sex=sex_sel)"
new_chart = "create_gender_headcount_donut(df, filters)"

if old_chart not in app_source and new_chart not in app_source:
    raise RuntimeError("หาโค้ดกราฟเพศใน app.py ไม่พบ")

app_source = app_source.replace(old_chart, new_chart, 1)

app_source = app_source.replace(
    "👫 ช่องว่างค่าจ้างระหว่างเพศ (Gender Wage Gap)",
    "👫 สัดส่วนผู้มีงานทำแยกตามเพศ",
    1,
)
app_source = app_source.replace(
    "ค่าจ้างเฉลี่ยชายเทียบหญิง (คลิกแท่งเพื่อกรองเฉพาะเพศนั้น)",
    "จำนวนผู้มีงานทำชายและหญิงจากข้อมูลจริง "
    "(หน่วยต้นทางเป็นพันคน)",
    1,
)

# The donut is a composition chart, not a wage bar.
app_source = app_source.replace(
    '"chart_gender_gap", dimension=\'sex\', valid_values=[\'ชาย\', \'หญิง\']',
    '"chart_gender_gap"',
    1,
)

app_source = app_source.replace(
    "ขนาดจุดแทนจำนวนผู้มีงานทำ (คลิกจุดเพื่อเลือกภาค)",
    "ดูชื่อภาคจากสีในคำอธิบายกราฟ หรือชี้เมาส์บนจุด"
    " (คลิกจุดเพื่อเลือกภาค)",
    1,
)

app_source = app_source.replace(
    "ค่าจ้างในเขตเทศบาลเทียบนอกเขตเทศบาลของแต่ละภาค (คลิกเพื่อเลือกภาค)",
    "จุดวงกลมสีม่วง = ค่าจ้างนอกเขตเทศบาล, "
    "จุดเพชรสีชมพู = ค่าจ้างในเขตเทศบาล, "
    "เส้นเชื่อม = ส่วนต่างค่าจ้าง (คลิกจุดเพื่อเลือกภาค)",
    1,
)

# Style the existing regional-details card, without adding region buttons.
original_detail = (
    "with detail_col:\n"
    "        with st.container(border=True):"
)
new_detail = (
    "with detail_col:\n"
    "        with st.container(border=True, key='region_details'):"
)

if original_detail in app_source:
    app_source = app_source.replace(
        original_detail, new_detail, 1
    )

css = '''
<style>
/* Highlight only the regional details card */
.st-key-region_details {
    background: linear-gradient(
        150deg, #FFF9FD 0%, #FCE4F1 60%, #F3D6F1 100%
    ) !important;
    border: 2px solid #E83C91 !important;
    border-radius: 20px !important;
    padding: 18px !important;
    box-shadow: 0 12px 32px rgba(132,58,125,.16) !important;
}
.st-key-region_details [data-testid="stMetric"] {
    background: rgba(255,255,255,.78);
    border: 1px solid #F0C7E0;
    border-radius: 14px;
    padding: 12px;
}
.st-key-region_details [data-testid="stMetricValue"] {
    color: #702667;
}
.st-key-region_details h3 {
    color: #702667 !important;
}
</style>
'''

if "/* Highlight only the regional details card */" not in app_source:
    needle = "st.markdown(get_custom_css(), unsafe_allow_html=True)"
    if needle not in app_source:
        raise RuntimeError("หาจุดโหลด CSS ใน app.py ไม่พบ")
    app_source = app_source.replace(
        needle,
        needle + "\n\nst.markdown(" + repr(css) +
        ", unsafe_allow_html=True)",
        1,
    )

ast.parse(app_source)

# Backup first; edit only after both outputs pass syntax checks.
for file in (CHARTS, APP):
    backup = file.with_suffix(file.suffix + ".before_visual_fixes.bak")
    if not backup.exists():
        shutil.copy2(file, backup)

CHARTS.write_text(updated_charts, encoding="utf-8")
APP.write_text(app_source, encoding="utf-8")

print("แก้ไขโค้ดเรียบร้อย:")
print(" - src/charts.py")
print(" - app.py")
print("สร้างไฟล์สำรอง .before_visual_fixes.bak แล้ว")
print("ยังไม่ได้ทดสอบการรัน Dashboard กับข้อมูลจริง")
