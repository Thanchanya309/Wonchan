"""
Plotly Chart Generators for Thailand Labor Market Dashboard
Modern Admin Bento Grid Theme with Pink-Purple Palette and Kanit Font
"""
import json
import os
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Palette Constants
COLOR_PINK = '#E83C91'
COLOR_PURPLE = '#843A7D'
COLOR_DARK_PURPLE = '#43334C'
COLOR_SKY_BLUE = '#57C7FF'
COLOR_ORANGE = '#F7A531'
COLOR_SOFT_PINK = '#FBEAF3'
COLOR_CARD_BG = '#FFFFFF'
COLOR_MUTED = '#8C7B94'
COLOR_GRID = '#F0E8EE'
FONT_FAMILY = 'Kanit, sans-serif'


def apply_chart_theme(fig, height=380, margin=None):
    """Apply consistent styling across all Plotly figures."""
    if margin is None:
        margin = dict(l=40, r=30, t=50, b=40)

    fig.update_layout(
        font=dict(family=FONT_FAMILY, color=COLOR_DARK_PURPLE, size=12),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=margin,
        hoverlabel=dict(
            bgcolor=COLOR_DARK_PURPLE,
            font_size=12,
            font_family=FONT_FAMILY,
            font_color='#FFFFFF'
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor=COLOR_GRID,
            linecolor=COLOR_GRID,
            tickfont=dict(family=FONT_FAMILY, color=COLOR_MUTED),
            title_font=dict(family=FONT_FAMILY, color=COLOR_DARK_PURPLE, size=13)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=COLOR_GRID,
            linecolor=COLOR_GRID,
            tickfont=dict(family=FONT_FAMILY, color=COLOR_MUTED),
            title_font=dict(family=FONT_FAMILY, color=COLOR_DARK_PURPLE, size=13)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(family=FONT_FAMILY, size=11)
        )
    )
    return fig


def create_time_series_chart(ts_data):
    """Dual-axis line chart for employment and unemployment rates."""
    fig = go.Figure()

    if ts_data.empty:
        fig.add_annotation(text="ไม่มีข้อมูลสำหรับตัวกรองที่เลือก", showarrow=False, font=dict(size=14, color=COLOR_MUTED))
        return apply_chart_theme(fig)

    # Filter out empty rates
    valid_ts = ts_data[ts_data['emp_rate'].notnull()].copy()

    # Employment Rate (Left Axis)
    fig.add_trace(go.Scatter(
        x=valid_ts['time_label'],
        y=valid_ts['emp_rate'],
        name='อัตราการมีงานทำ (%)',
        mode='lines+markers',
        line=dict(color=COLOR_PINK, width=3),
        marker=dict(size=6, color=COLOR_PINK),
        customdata=valid_ts['year'],
        hovertemplate="<b>%{x}</b><br>อัตราการมีงานทำ: %{y:.2f}%<extra></extra>",
        yaxis='y1'
    ))

    # Unemployment Rate (Right Axis)
    unemp_ts = ts_data[ts_data['unemp_rate'].notnull()].copy()
    fig.add_trace(go.Scatter(
        x=unemp_ts['time_label'],
        y=unemp_ts['unemp_rate'],
        name='อัตราการว่างงาน (%)',
        mode='lines+markers',
        line=dict(color=COLOR_PURPLE, width=2.5, dash='dot'),
        marker=dict(size=5, color=COLOR_PURPLE),
        customdata=unemp_ts['year'],
        hovertemplate="<b>%{x}</b><br>อัตราการว่างงาน: %{y:.2f}%<extra></extra>",
        yaxis='y2'
    ))

    fig = apply_chart_theme(fig, height=360)
    fig.update_layout(
        yaxis=dict(
            title='อัตราการมีงานทำ (%)',
            title_font=dict(color=COLOR_PINK),
            tickfont=dict(color=COLOR_PINK),
            side='left',
            showgrid=True
        ),
        yaxis2=dict(
            title='อัตราการว่างงาน (%)',
            title_font=dict(color=COLOR_PURPLE),
            tickfont=dict(color=COLOR_PURPLE),
            side='right',
            overlaying='y',
            showgrid=False
        ),
        clickmode='event+select'
    )
    return fig


def create_wage_trend_chart(ts_data, wage_data):
    """Area/Line chart showing average wage evolution over time."""
    fig = go.Figure()

    if wage_data is not None and not wage_data.empty:
        fig.add_trace(go.Scatter(
            x=[f"พ.ศ. {int(y)}" for y in wage_data['year']],
            y=wage_data['annual_avg_wage'],
            name='ค่าจ้างเฉลี่ยรายปี (บาท/เดือน)',
            mode='lines+markers',
            line=dict(color=COLOR_PURPLE, width=3),
            fill='tozeroy',
            fillcolor='rgba(232, 60, 145, 0.12)',
            marker=dict(size=7, color=COLOR_PINK),
            customdata=wage_data['year'],
            hovertemplate="<b>%{x}</b><br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน<extra></extra>"
        ))

    fig = apply_chart_theme(fig, height=360)
    fig.update_layout(
        yaxis=dict(title='ค่าจ้างเฉลี่ย (บาท/เดือน)', tickformat=","),
        clickmode='event+select'
    )
    return fig


def create_headcount_trend_chart(ts_data):
    """Bar chart of employed population headcount over time in millions of persons."""
    fig = go.Figure()

    sub = ts_data[ts_data['emp_headcount_m'].notnull()].copy()
    if not sub.empty:
        fig.add_trace(go.Bar(
            x=sub['time_label'],
            y=sub['emp_headcount_m'],
            name='ผู้มีงานทำ (ล้านคน)',
            marker=dict(
                color=COLOR_SKY_BLUE,
                line=dict(color=COLOR_PURPLE, width=1)
            ),
            customdata=sub['year'],
            hovertemplate="<b>%{x}</b><br>จำนวนผู้มีงานทำ: %{y:.2f} ล้านคน<extra></extra>"
        ))

    fig = apply_chart_theme(fig, height=340)
    fig.update_layout(
        yaxis=dict(title='ผู้มีงานทำ (ล้านคน)'),
        clickmode='event+select'
    )
    return fig


def create_seasonality_chart(df, filters):
    """Bar chart comparing unemployment rates across quarters (Q1-Q4) to show seasonal shifts."""
    region = filters.get('region', 'ทั้งหมด')
    target_region = 'รวม' if region == 'ทั้งหมด' else region

    mask = (
        (df['clean_region'] == target_region) &
        (df['clean_area'] == 'รวม') &
        (df['clean_sex'] == 'รวม') &
        (df['clean_age'] == 'รวม') &
        (df['quarter'].isin([1, 2, 3, 4])) &
        (df['unemp_rate'].notnull())
    )
    if target_region == 'กรุงเทพมหานคร':
        mask = (
            (df['clean_region'] == target_region) &
            (df['clean_area'] == 'ในเขตเทศบาล') &
            (df['clean_sex'] == 'รวม') &
            (df['clean_age'] == 'รวม') &
            (df['quarter'].isin([1, 2, 3, 4])) &
            (df['unemp_rate'].notnull())
        )

    sub = df[mask]
    q_avg = sub.groupby('quarter')['unemp_rate'].mean().reset_index()

    q_labels = {
        1: 'Q1 (ม.ค.-มี.ค. / ฤดูแล้ง)',
        2: 'Q2 (เม.ย.-มิ.ย.)',
        3: 'Q3 (ก.ค.-ก.ย. / ฤดูเพาะปลูก)',
        4: 'Q4 (ต.ค.-ธ.ค. / ฤดูเก็บเกี่ยว)'
    }
    q_avg['q_label'] = q_avg['quarter'].map(q_labels)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=q_avg['q_label'],
        y=q_avg['unemp_rate'],
        marker=dict(
            color=[COLOR_ORANGE, COLOR_PURPLE, COLOR_SKY_BLUE, COLOR_PINK],
            line=dict(color=COLOR_DARK_PURPLE, width=1)
        ),
        customdata=q_avg['quarter'],
        hovertemplate="<b>%{x}</b><br>อัตราว่างงานเฉลี่ย: %{y:.2f}%<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=340)
    fig.update_layout(
        yaxis=dict(title='อัตราการว่างงานเฉลี่ย (%)'),
        clickmode='event+select'
    )
    return fig


def create_regional_ranking_chart(reg_data, metric='avg_wage', selected_region=None):
    """Horizontal sorted bar chart ranking regions by wage or unemployment."""
    fig = go.Figure()

    if reg_data.empty:
        return apply_chart_theme(fig)

    metric_col = metric
    if metric == 'avg_wage':
        title = 'ค่าจ้างเฉลี่ยรายภูมิภาค (บาท/เดือน)'
        x_label = 'ค่าจ้างเฉลี่ย (บาท/เดือน)'
        hover_unit = 'บาท/เดือน'
        format_str = ":,.2f"
        sorted_df = reg_data.sort_values(by=metric_col, ascending=True)
    elif metric == 'unemp_rate':
        title = 'อัตราการว่างงานรายภูมิภาค (%)'
        x_label = 'อัตราการว่างงาน (%)'
        hover_unit = '%'
        format_str = ":.2f"
        sorted_df = reg_data.sort_values(by=metric_col, ascending=True)
    else:
        title = 'อัตราการมีงานทำรายภูมิภาค (%)'
        x_label = 'อัตราการมีงานทำ (%)'
        hover_unit = '%'
        format_str = ":.2f"
        sorted_df = reg_data.sort_values(by=metric_col, ascending=True)

    colors = []
    for r in sorted_df['region']:
        if selected_region and r == selected_region:
            colors.append(COLOR_PINK)
        else:
            colors.append(COLOR_PURPLE)

    fig.add_trace(go.Bar(
        y=sorted_df['region'],
        x=sorted_df[metric_col],
        orientation='h',
        marker=dict(color=colors, line=dict(color=COLOR_DARK_PURPLE, width=0.5)),
        customdata=sorted_df['region'],
        hovertemplate=f"<b>%{{y}}</b><br>{x_label}: %{{x{format_str}}} {hover_unit}<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=380, margin=dict(l=140, r=30, t=30, b=40))
    fig.update_layout(
        xaxis=dict(title=x_label),
        clickmode='event+select'
    )
    return fig


def create_wage_vs_employment_scatter(reg_data):
    """Bubble scatter plot showing relation between wage and employment rate."""
    fig = go.Figure()

    if reg_data.empty or reg_data['avg_wage'].dropna().empty:
        return apply_chart_theme(fig)

    clean_df = reg_data.dropna(subset=['avg_wage', 'emp_rate']).copy()
    if clean_df.empty:
        return apply_chart_theme(fig)

    sizes = clean_df['headcount_m'].fillna(1.0) * 8
    sizes = np.clip(sizes, 12, 45)

    fig.add_trace(go.Scatter(
        x=clean_df['avg_wage'],
        y=clean_df['emp_rate'],
        mode='markers+text',
        text=clean_df['region'],
        textposition='top center',
        textfont=dict(family=FONT_FAMILY, size=11, color=COLOR_DARK_PURPLE),
        marker=dict(
            size=sizes,
            color=clean_df['avg_wage'],
            colorscale=[[0, COLOR_PURPLE], [0.5, COLOR_PINK], [1, COLOR_ORANGE]],
            showscale=False,
            line=dict(color=COLOR_DARK_PURPLE, width=1.5)
        ),
        customdata=clean_df['region'],
        hovertemplate=(
            "<b>%{customdata}</b><br>" +
            "ค่าจ้างเฉลี่ย: %{x:,.2f} บาท/เดือน<br>" +
            "อัตรามีงานทำ: %{y:.2f}%<br>" +
            "<extra></extra>"
        )
    ))

    fig = apply_chart_theme(fig, height=380)
    fig.update_layout(
        xaxis=dict(title='ค่าจ้างเฉลี่ย (บาท/เดือน)', tickformat=","),
        yaxis=dict(title='อัตราการมีงานทำ (%)'),
        clickmode='event+select'
    )
    return fig


def create_dumbbell_wage_chart(area_data):
    """Dumbbell / paired comparison of municipal vs non-municipal wages."""
    fig = go.Figure()

    if area_data.empty or area_data['wage_in'].dropna().empty:
        return apply_chart_theme(fig)

    valid_df = area_data.dropna(subset=['wage_in', 'wage_out']).copy()

    # Lines connecting the points
    for _, row in valid_df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['wage_out'], row['wage_in']],
            y=[row['region'], row['region']],
            mode='lines',
            line=dict(color=COLOR_MUTED, width=3),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Points for Non-municipal
    fig.add_trace(go.Scatter(
        x=valid_df['wage_out'],
        y=valid_df['region'],
        mode='markers',
        name='นอกเขตเทศบาล (ชนบท)',
        marker=dict(color=COLOR_PURPLE, size=11, symbol='circle'),
        customdata=valid_df['region'],
        hovertemplate="<b>%{y}</b> (นอกเขต): %{x:,.2f} บาท/เดือน<extra></extra>"
    ))

    # Points for Municipal
    fig.add_trace(go.Scatter(
        x=valid_df['wage_in'],
        y=valid_df['region'],
        mode='markers',
        name='ในเขตเทศบาล (เมือง)',
        marker=dict(color=COLOR_PINK, size=11, symbol='diamond'),
        customdata=valid_df['region'],
        hovertemplate="<b>%{y}</b> (ในเขต): %{x:,.2f} บาท/เดือน<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=340, margin=dict(l=140, r=30, t=40, b=40))
    fig.update_layout(
        xaxis=dict(title='ค่าจ้างเฉลี่ย (บาท/เดือน)', tickformat=","),
        clickmode='event+select'
    )
    return fig


def create_gender_gap_chart(gender_data):
    """Grouped bar chart for Male vs Female wages and gap percentage."""
    fig = go.Figure()

    if gender_data.empty or gender_data['avg_wage'].dropna().empty:
        return apply_chart_theme(fig)

    colors = {'ชาย': COLOR_SKY_BLUE, 'หญิง': COLOR_PINK}

    fig.add_trace(go.Bar(
        x=gender_data['sex'],
        y=gender_data['avg_wage'],
        marker=dict(
            color=[colors.get(s, COLOR_PURPLE) for s in gender_data['sex']],
            line=dict(color=COLOR_DARK_PURPLE, width=1)
        ),
        text=[f"{w:,.0f} ฿" if pd.notnull(w) else "" for w in gender_data['avg_wage']],
        textposition='outside',
        textfont=dict(family=FONT_FAMILY, size=12, color=COLOR_DARK_PURPLE),
        customdata=gender_data['sex'],
        hovertemplate="<b>เพศ%{x}</b><br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=340)
    fig.update_layout(
        yaxis=dict(title='ค่าจ้างเฉลี่ย (บาท/เดือน)', tickformat=","),
        clickmode='event+select'
    )
    return fig


def create_age_wage_chart(age_data):
    """Age-Wage profile curve showing peak wage earning years."""
    fig = go.Figure()

    if age_data.empty:
        return apply_chart_theme(fig)

    fig.add_trace(go.Scatter(
        x=age_data['age_group'],
        y=age_data['avg_wage'],
        mode='lines+markers',
        line=dict(color=COLOR_PURPLE, width=3.5, shape='spline'),
        marker=dict(size=9, color=COLOR_PINK),
        fill='tozeroy',
        fillcolor='rgba(232, 60, 145, 0.1)',
        customdata=age_data['age_group'],
        hovertemplate="<b>กลุ่มอายุ %{x}</b><br>ค่าจ้างเฉลี่ย: %{y:,.2f} บาท/เดือน<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(
        yaxis=dict(title='ค่าจ้างเฉลี่ย (บาท/เดือน)', tickformat=","),
        xaxis=dict(tickangle=-30),
        clickmode='event+select'
    )
    return fig


def create_youth_unemployment_chart(age_data):
    """Bar chart of unemployment rates by age group highlighting youth (15-24)."""
    fig = go.Figure()

    if age_data.empty:
        return apply_chart_theme(fig)

    colors = []
    for ag in age_data['age_group']:
        if ag in ['15-19 ปี', '20-24 ปี']:
            colors.append(COLOR_PINK)  # Highlight youth unemployment
        else:
            colors.append(COLOR_MUTED)

    fig.add_trace(go.Bar(
        x=age_data['age_group'],
        y=age_data['unemp_rate'],
        marker=dict(color=colors, line=dict(color=COLOR_DARK_PURPLE, width=0.5)),
        text=[f"{r:.1f}%" if pd.notnull(r) else "" for r in age_data['unemp_rate']],
        textposition='outside',
        textfont=dict(family=FONT_FAMILY, size=11, color=COLOR_DARK_PURPLE),
        customdata=age_data['age_group'],
        hovertemplate="<b>กลุ่มอายุ %{x}</b><br>อัตราการว่างงาน: %{y:.2f}%<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=350)
    fig.update_layout(
        yaxis=dict(title='อัตราการว่างงาน (%)'),
        xaxis=dict(tickangle=-30),
        clickmode='event+select'
    )
    return fig


def create_demographic_matrix_heatmap(df, filters):
    """Matrix heatmap of employed population across Sex and Age Groups."""
    year = filters.get('year', 'ทั้งหมด')
    quarter = filters.get('quarter', 'ทั้งหมด')
    region = filters.get('region', 'ทั้งหมด')

    cur_year = int(year) if year != 'ทั้งหมด' else 2568
    cur_q = int(quarter) if (quarter != 'ทั้งหมด' and int(quarter) > 0) else None

    target_region = 'รวม' if region == 'ทั้งหมด' else region

    age_brackets = [
        '15-19 ปี', '20-24 ปี', '25-29 ปี', '30-34 ปี',
        '35-39 ปี', '40-49 ปี', '50-59 ปี', '60 ปีขึ้นไป'
    ]

    matrix_data = []
    for s in ['ชาย', 'หญิง']:
        row_vals = []
        for ag in age_brackets:
            mask = (
                (df['clean_sex'] == s) &
                (df['clean_age'] == ag) &
                (df['year'] == cur_year) &
                (df['emp_headcount'].notnull())
            )
            if target_region != 'รวม':
                mask = mask & (df['clean_region'] == target_region)
            if cur_q:
                mask = mask & (df['quarter'] == cur_q)
            else:
                sub = df[mask]
                if not sub.empty:
                    mask = mask & (df['quarter'] == sub['quarter'].max())

            hc_dedup = df[mask].drop_duplicates(subset=['year', 'quarter', 'clean_region', 'clean_sex', 'clean_age'])
            val_k = hc_dedup['emp_headcount'].sum() if not hc_dedup.empty else 0
            row_vals.append(round(val_k / 1000.0, 2))  # In millions
        matrix_data.append(row_vals)

    fig = go.Figure(data=go.Heatmap(
        z=matrix_data,
        x=age_brackets,
        y=['ชาย', 'หญิง'],
        colorscale=[[0, '#FFFFFF'], [0.2, COLOR_SOFT_PINK], [0.6, COLOR_PINK], [1, COLOR_PURPLE]],
        text=matrix_data,
        texttemplate="%{text:.2f}M",
        textfont=dict(family=FONT_FAMILY, size=11),
        hovertemplate="<b>เพศ%{y} | อายุ %{x}</b><br>ผู้มีงานทำ: %{z:.2f} ล้านคน<extra></extra>"
    ))

    fig = apply_chart_theme(fig, height=280)
    fig.update_layout(
        xaxis=dict(tickangle=-25),
        clickmode='event+select'
    )
    return fig


def create_thailand_map(reg_data, metric='avg_wage', year=2568, selected_region='ทั้งหมด'):
    """Regional polygons from the project's province GeoJSON; one shape per region.

    This uses true region-level features and stable feature ordering for click events.
    """
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    geojson_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'assets', 'thailand_regions.geojson'
    )
    if not os.path.isfile(geojson_path):
        return create_regional_ranking_chart(reg_data, metric=metric)

    with open(geojson_path, encoding='utf-8') as file:
        source = json.load(file)

    region_property = 'region_7' if int(year) >= 2568 else 'region_5'
    groups = {}
    for feature in source.get('features', []):
        name = feature.get('properties', {}).get(region_property)
        geom = feature.get('geometry')
        if name and geom:
            groups.setdefault(name, []).append(shape(geom))

    if not groups or reg_data.empty or metric not in reg_data.columns:
        return create_regional_ranking_chart(reg_data, metric=metric)

    merged_shapes = {name: unary_union(items) for name, items in groups.items()}
    geojson = {
        'type': 'FeatureCollection',
        'features': [
            {'type': 'Feature', 'properties': {'region': name},
             'geometry': mapping(geometry)}
            for name, geometry in merged_shapes.items()
        ]
    }
    frame = reg_data[['region', metric]].copy()
    frame[metric] = pd.to_numeric(frame[metric], errors='coerce')
    frame = frame.dropna(subset=[metric])
    frame = frame[frame['region'].isin(merged_shapes)].drop_duplicates('region')
    if frame.empty:
        return go.Figure()

    titles = {
        'avg_wage': 'ค่าจ้างเฉลี่ย (บาท/เดือน)',
        'unemp_rate': 'อัตราการว่างงาน (%)',
        'emp_rate': 'อัตราการมีงานทำ (%)',
    }
    metric_title = titles.get(metric, metric)
    # Order and trace locations are aligned. Click handler can use pointNumber or location.
    fig = go.Figure(go.Choropleth(
        geojson=geojson,
        locations=frame['region'].tolist(),
        z=frame[metric].tolist(),
        featureidkey='properties.region',
        customdata=[[str(region)] for region in frame['region']],
        colorscale=[[0, '#FDE6F1'], [.45, '#EB5DA7'], [1, '#683074']],
        colorbar=dict(title=metric_title, thickness=13, len=.65,
                      x=1.01, xpad=4, tickfont=dict(size=11)),
        marker_line_color='#FFFFFF', marker_line_width=1.8,
        hovertemplate='<b>%{location}</b><br>' + metric_title + ': %{z:,.2f}<extra></extra>',
        showscale=True,
    ))
    # Projections/extent in degrees. Explicit geographic extents avoid postage-stamp maps.
    if selected_region in merged_shapes:
        minx, miny, maxx, maxy = merged_shapes[selected_region].bounds
        padding = 0.12
    else:
        joined = unary_union(list(merged_shapes.values()))
        minx, miny, maxx, maxy = joined.bounds
        padding = 0.045
    dx, dy = max(0.8, maxx-minx), max(0.8, maxy-miny)
    fig.update_geos(
        projection_type='mercator',
        lonaxis_range=[minx-dx*padding, maxx+dx*padding],
        lataxis_range=[miny-dy*padding, maxy+dy*padding],
        bgcolor='rgba(0,0,0,0)', visible=False,
        showcoastlines=False, showland=False,
        domain=dict(x=[0, .91], y=[0, 1]),
    )
    fig.update_layout(
        height=650, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT_FAMILY, color=COLOR_DARK_PURPLE),
        clickmode='event+select', dragmode=False,
        uirevision=f'map_{year}_{selected_region}_{metric}',
    )
    return fig
