"""
Thailand Labor Market Interactive Analytics Dashboard
Built with Streamlit, Pandas, and Plotly
Features: Bi-directional Cross-filtering, Modern Admin Bento Grid, Official NSO Statistical Rules
"""
import streamlit as st
import pandas as pd
import numpy as np

# This component returns Plotly click events (native Streamlit selection is not a click).
try:
    from streamlit_plotly_events import plotly_events
except ImportError:
    plotly_events = None

# Page configuration
st.set_page_config(
    page_title="Thailand Labor Market Analytics | แดชบอร์ดตลาดแรงงานไทย",
    page_icon="🇹🇭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import internal modules
from src.styles import get_custom_css
from src.data_loader import (
    get_cached_labor_data,
    AGE_ORDER,
    REGION_ORDER,
    AREA_ORDER,
    SEX_ORDER
)
from src.filters import (
    init_filter_state,
    get_current_filters,
    set_filter,
    reset_all_filters,
    clear_filter,
    handle_chart_selection
)
from src.metrics import (
    get_kpis,
    get_time_series_data,
    get_regional_comparison_data,
    get_demographics_gender_data,
    get_demographics_age_data,
    get_area_wage_comparison_data
)
from src.charts import (
    create_time_series_chart,
    create_wage_trend_chart,
    create_headcount_trend_chart,
    create_seasonality_chart,
    create_regional_ranking_chart,
    create_wage_vs_employment_scatter,
    create_dumbbell_wage_chart,
    create_gender_gap_chart,
    create_age_wage_chart,
    create_youth_unemployment_chart,
    create_demographic_matrix_heatmap,
    create_thailand_map
)

# Apply UI styling
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Initialize filter state
init_filter_state()
filters = get_current_filters()

# A selected map region is applied before the sidebar widget is created.
# Streamlit does not allow writing to an existing widget key after its creation.
if st.session_state.pop('_pending_map_sidebar_sync', False):
    st.session_state['sb_region'] = filters.get('region', 'ทั้งหมด')
if st.session_state.pop('_pending_reset_sidebar_sync', False):
    sidebar_widget_keys = {
        'year': 'sb_year', 'quarter': 'sb_quarter', 'region': 'sb_region',
        'area': 'sb_area', 'sex': 'sb_sex', 'age_group': 'sb_age',
    }
    for dimension, widget_key in sidebar_widget_keys.items():
        st.session_state[widget_key] = filters.get(dimension, 'ทั้งหมด')

# Load dataset
try:
    df = get_cached_labor_data()
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
    st.stop()


# -------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand-card">
        <h2>🇹🇭 Labor Analytics</h2>
        <p>สถิติตลาดแรงงานไทย (NSO Thailand)</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 ตัวกรองข้อมูลหลัก (Global Filters)")

    # 1. Year Filter
    avail_years = sorted(df['year'].unique(), reverse=True)
    cur_year = filters.get('year', 2568)
    year_idx = avail_years.index(cur_year) if cur_year in avail_years else 0
    selected_year = st.selectbox(
        "📅 ปี พ.ศ.",
        options=avail_years,
        index=year_idx,
        key="sb_year"
    )
    if selected_year != filters.get('year'):
        set_filter('year', selected_year)
        st.rerun()

    # 2. Quarter Filter
    q_opts = ['ทั้งหมด', 1, 2, 3, 4]
    cur_q = filters.get('quarter', 'ทั้งหมด')
    q_idx = q_opts.index(cur_q) if cur_q in q_opts else 0
    selected_quarter = st.selectbox(
        "⏱️ ไตรมาส",
        options=q_opts,
        index=q_idx,
        format_func=lambda x: f"ไตรมาส {x}" if isinstance(x, int) else "ทั้งหมด (ภาพรวม)",
        key="sb_quarter"
    )
    if selected_quarter != filters.get('quarter'):
        set_filter('quarter', selected_quarter)
        st.rerun()

    # 3. Region Filter
    avail_regions = ['ทั้งหมด'] + [r for r in REGION_ORDER if r in df['clean_region'].unique() and r != 'รวม']
    cur_region = filters.get('region', 'ทั้งหมด')
    reg_idx = avail_regions.index(cur_region) if cur_region in avail_regions else 0
    selected_region = st.selectbox(
        "📍 ภูมิภาค",
        options=avail_regions,
        index=reg_idx,
        key="sb_region"
    )
    if selected_region != filters.get('region'):
        set_filter('region', selected_region)
        st.rerun()

    # 4. Area Filter
    avail_areas = ['ทั้งหมด', 'ในเขตเทศบาล', 'นอกเขตเทศบาล']
    cur_area = filters.get('area', 'ทั้งหมด')
    area_idx = avail_areas.index(cur_area) if cur_area in avail_areas else 0
    selected_area = st.selectbox(
        "🏙️ เขตการปกครอง",
        options=avail_areas,
        index=area_idx,
        key="sb_area"
    )
    if selected_area != filters.get('area'):
        set_filter('area', selected_area)
        st.rerun()

    # 5. Sex Filter
    avail_sex = ['ทั้งหมด', 'ชาย', 'หญิง']
    cur_sex = filters.get('sex', 'ทั้งหมด')
    sex_idx = avail_sex.index(cur_sex) if cur_sex in avail_sex else 0
    selected_sex = st.selectbox(
        "👤 เพศ",
        options=avail_sex,
        index=sex_idx,
        key="sb_sex"
    )
    if selected_sex != filters.get('sex'):
        set_filter('sex', selected_sex)
        st.rerun()

    # 6. Age Group Filter
    avail_ages = ['ทั้งหมด'] + [a for a in AGE_ORDER if a != 'รวม']
    cur_age = filters.get('age_group', 'ทั้งหมด')
    age_idx = avail_ages.index(cur_age) if cur_age in avail_ages else 0
    selected_age = st.selectbox(
        "🎂 กลุ่มอายุ",
        options=avail_ages,
        index=age_idx,
        key="sb_age"
    )
    if selected_age != filters.get('age_group'):
        set_filter('age_group', selected_age)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 รีเซ็ตตัวกรองทั้งหมด", type="primary", use_container_width=True):
        reset_all_filters()
        st.session_state['_pending_reset_sidebar_sync'] = True
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.8rem; color: #7A6882; line-height: 1.4;">
        <b>แหล่งข้อมูล:</b> การสำรวจภาวะการทำงานของประชากร สำนักงานสถิติแห่งชาติ (NSO)<br>
        <b>เทคโนโลยี:</b> Python, Streamlit, Pandas, Plotly<br>
        <b>เวอร์ชัน:</b> 1.0.0
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------------
# MAIN DASHBOARD AREA
# -------------------------------------------------------------

# Main Header Banner
st.markdown("""
<div class="main-header-banner">
    <div>
        <h1 class="main-header-title">🇹🇭 แดชบอร์ดวิเคราะห์สถิติตลาดแรงงานไทย</h1>
        <p class="main-header-subtitle">ระบบติดตามภาวะการทำงาน ค่าจ้าง อัตราการว่างงาน และโครงสร้างประชากรแบบโต้ตอบ (Cross-filtering Enabled)</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Active Filters Tag Bar
active_tags_html = ['<div class="active-filters-container"><span style="font-size:0.85rem; font-weight:600; color:#43334C;">ตัวกรองที่ใช้งาน:</span>']
has_custom_filters = False

for dim, val in filters.items():
    if dim == 'year':
        active_tags_html.append(f'<span class="filter-pill"><span class="filter-pill-label">ปี:</span> <span class="filter-pill-val">{val}</span></span>')
    elif val != 'ทั้งหมด':
        has_custom_filters = True
        label_map = {'quarter': 'ไตรมาส', 'region': 'ภาค', 'area': 'พื้นที่', 'sex': 'เพศ', 'age_group': 'อายุ'}
        d_lbl = label_map.get(dim, dim)
        active_tags_html.append(f'<span class="filter-pill"><span class="filter-pill-label">{d_lbl}:</span> <span class="filter-pill-val">{val}</span></span>')

active_tags_html.append('</div>')
st.markdown("".join(active_tags_html), unsafe_allow_html=True)

# Calculate KPIs
kpis = get_kpis(df, filters)

# Display caveats if applicable
caveats = []
if kpis['wage_caveat']:
    caveats.append(kpis['wage_caveat'])
if kpis['headcount_caveat']:
    caveats.append(kpis['headcount_caveat'])

if caveats:
    caveat_text = "<br>• ".join(["• " + c for c in caveats])
    st.markdown(f"""
    <div class="caveat-banner">
        <div class="caveat-title">ℹ️ ข้อควรทราบทางสถิติสำหรับตัวกรองปัจจุบัน:</div>
        {caveat_text}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Show only KPI cards backed by actual values for the active filters.
# Create columns dynamically, so absent indicators leave no blank placeholders.
def valid_metric(value):
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False

kpi_items = [
    ('avg_wage', '💵 ค่าจ้างเฉลี่ย', 'บาท/เดือน', 'ประชากรมีงานทำที่เป็นลูกจ้าง', 'kpi-card-1', ',.0f'),
    ('emp_rate', '📈 อัตราการมีงานทำ', '%', 'สัดส่วนต่อกำลังแรงงานรวม', 'kpi-card-2', '.2f'),
    ('unemp_rate', '⚠️ อัตราการว่างงาน', '%', 'สัดส่วนผู้ว่างงานต่อกำลังแรงงาน', 'kpi-card-3', '.2f'),
    ('emp_headcount_m', '👥 ประชากรผู้มีงานทำ', 'ล้านคน', '', 'kpi-card-4', '.2f'),
]
available_kpis = [item for item in kpi_items if valid_metric(kpis.get(item[0]))]
if available_kpis:
    for col, (metric, title, unit, note, color_class, num_format) in zip(
        st.columns(len(available_kpis)), available_kpis
    ):
        with col:
            value_text = format(float(kpis[metric]), num_format)
            if metric == 'emp_headcount_m' and valid_metric(kpis.get('emp_headcount_k')):
                note = f"({float(kpis['emp_headcount_k']):,.1f} พันคน)"
            st.markdown(f"""
            <div class="kpi-card {color_class}">
                <div class="kpi-title">{title}</div>
                <div class="kpi-value">{value_text}<span class="kpi-unit">{unit}</span></div>
                <div class="kpi-subtext">{note}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.caption('ไม่มีตัวชี้วัด KPI ที่รองรับตัวกรองนี้')

st.markdown("<br>", unsafe_allow_html=True)


# -------------------------------------------------------------
# TAB NAVIGATION
# -------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 ภาพรวมตลาดแรงงานไทย",
    "🗺️ วิเคราะห์ตลาดแรงงานรายภูมิภาค",
    "👥 วิเคราะห์กลุ่มประชากรและความแตกต่าง",
    "📋 ตารางข้อมูลและคำอธิบายสถิติ"
])


# -------------------------------------------------------------
# TAB 1: ภาพรวมตลาดแรงงานไทย (MACRO OVERVIEW)
# -------------------------------------------------------------
with tab1:
    # Map is the main interaction point of the overview.
    st.markdown("### 🗺️ สำรวจตลาดแรงงานรายภูมิภาค")
    full_region_data = get_regional_comparison_data(df, filters)
    map_metric = st.selectbox(
        'เลือกตัวชี้วัดบนแผนที่',
        ['emp_rate', 'unemp_rate', 'avg_wage'],
        format_func=lambda x: {
            'emp_rate': 'อัตราการมีงานทำ (%)',
            'unemp_rate': 'อัตราการว่างงาน (%)',
            'avg_wage': 'ค่าจ้างเฉลี่ย (บาท/เดือน)',
        }[x],
        key='overview_map_metric',
    )
    valid_regions = full_region_data.dropna(subset=[map_metric]).copy()
    if not valid_regions.empty:
        main_map, map_detail = st.columns([2.4, 1], gap='medium')
        with main_map:
            with st.container(border=True):
                selected_region = filters.get('region', 'ทั้งหมด')
                if selected_region != 'ทั้งหมด':
                    st.caption(f'📍 เลือกอยู่: {selected_region} — แผนที่ขยายเพื่อแสดงภูมิภาคนี้')
                map_fig = create_thailand_map(
                    valid_regions, metric=map_metric, year=filters['year'],
                    selected_region=selected_region,
                )
                if plotly_events is not None:
                    # IMPORTANT: exactly one map trace; pointNumber indexes trace.locations.
                    clicked = plotly_events(
                        map_fig, click_event=True, select_event=False,
                        hover_event=False, override_height=650,
                        key=f"regional_map_click_{filters['year']}_{selected_region}_{map_metric}",
                    )
                    if clicked:
                        point = clicked[0]
                        names = list(map_fig.data[0].locations) if map_fig.data else []
                        position = point.get('pointNumber', point.get('pointIndex'))
                        candidate = names[position] if isinstance(position, int) and 0 <= position < len(names) else None
                        if candidate and candidate != selected_region:
                            set_filter('region', candidate)
                            st.session_state['_pending_map_sidebar_sync'] = True
                            st.rerun()
                else:
                    st.plotly_chart(map_fig, use_container_width=True,
                                    config={'displayModeBar': False})
                    st.info('ติดตั้ง streamlit-plotly-events เพื่อเปิดการคลิกแผนที่: python -m pip install -r requirements.txt')
        with map_detail:
            with st.container(border=True):
                st.markdown('**📌 รายละเอียดภูมิภาค**')
                if filters['region'] != 'ทั้งหมด':
                    st.markdown(f"### {filters['region']}")
                    if st.button('↩️ กลับไปดูทั้งประเทศ', key='overview_map_reset',
                                 use_container_width=True):
                        clear_filter('region')
                        st.session_state['_pending_map_sidebar_sync'] = True
                        st.rerun()
                    regional_kpis = get_kpis(df, filters)
                    for field, label, unit in [
                        ('emp_rate', 'อัตราการมีงานทำ', '%'),
                        ('unemp_rate', 'อัตราการว่างงาน', '%'),
                        ('avg_wage', 'ค่าจ้างเฉลี่ย', 'บาท/เดือน'),
                    ]:
                        value = regional_kpis.get(field)
                        if valid_metric(value):
                            st.metric(label, f'{float(value):,.2f} {unit}')
                else:
                    st.markdown('**ประเทศไทย**')
                    st.caption('คลิกภูมิภาคบนแผนที่ หรือกดชื่อภาคด้านล่าง เพื่อซูมและกรองทั้ง Dashboard')
                # Dependable alternative to map clicks for all browsers and devices.
                st.markdown('**เลือกภาค:**')
                for region in valid_regions['region'].astype(str).tolist():
                    if st.button('📍 ' + region, key='map_region_btn_' + region,
                                 use_container_width=True):
                        set_filter('region', region)
                        st.session_state['_pending_map_sidebar_sync'] = True
                        st.rerun()
    else:
        st.caption('ไม่มีข้อมูลรายภาคที่รองรับตัวชี้วัดและช่วงเวลาที่เลือก')

    ts_data, wage_data = get_time_series_data(df, filters)

    if valid_metric(kpis.get('emp_rate')) or valid_metric(kpis.get('unemp_rate')):
        with st.container(border=True):
            st.markdown("**📈 แนวโน้มอัตราการมีงานทำและอัตราการว่างงานตามเวลา**")
            st.caption("แสดงการเคลื่อนไหวของตลาดแรงงานรายปีและรายไตรมาส (คลิกเลือกจุดบนกราฟเพื่อกรองปี/ไตรมาส)")

            fig_rates_ts = create_time_series_chart(ts_data)
            event_rates = st.plotly_chart(
                fig_rates_ts,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key="chart_rates_ts"
            )
            if handle_chart_selection(event_rates, 'year', value_key='customdata'):
                st.rerun()

    c1, c2 = st.columns(2)

    with c1:
        if valid_metric(kpis.get('avg_wage')):
            with st.container(border=True):
                st.markdown("**💵 ทิศทางการเติบโตของค่าจ้างเฉลี่ย (บาท/เดือน)**")
                st.caption("ค่าจ้างเฉลี่ยรายปีตามตัวกรองที่เลือก (คลิกจุดปีบนกราฟเพื่อเจาะจงปี)")
                fig_wage_trend = create_wage_trend_chart(ts_data, wage_data)
                event_wage = st.plotly_chart(
                    fig_wage_trend,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_wage_trend"
                )
                if handle_chart_selection(event_wage, 'year', value_key='customdata'):
                    st.rerun()

    with c2:
        if valid_metric(kpis.get('unemp_rate')) and filters.get('quarter', 'ทั้งหมด') == 'ทั้งหมด':
            with st.container(border=True):
                st.markdown("**🌾 การเปลี่ยนแปลงตามฤดูกาลในแต่ละไตรมาส (Seasonality)**")
                st.caption("เปรียบเทียบอัตราว่างงานเฉลี่ย Q1 (แล้ง) ถึง Q4 (เก็บเกี่ยว) ชี้ชัดผลกระทบภาคเกษตรกรรม")
                fig_season = create_seasonality_chart(df, filters)
                event_season = st.plotly_chart(
                    fig_season,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_seasonality"
                )
                if handle_chart_selection(event_season, 'quarter', value_key='customdata'):
                    st.rerun()

    if valid_metric(kpis.get('emp_headcount_m')):
        with st.container(border=True):
            st.markdown("**👥 จำนวนผู้มีงานทำรวมของประเทศตามช่วงเวลา (ล้านคน)**")
            st.caption("สะท้อนขนาดกำลังแรงงานที่แท้จริงจากประมาณการประชากร (2555 - 2569)")
            fig_hc_trend = create_headcount_trend_chart(ts_data)
            event_hc = st.plotly_chart(
                fig_hc_trend,
                use_container_width=True,
                on_select="rerun",
                selection_mode="points",
                key="chart_hc_trend"
            )
            if handle_chart_selection(event_hc, 'year', value_key='customdata'):
                st.rerun()


# -------------------------------------------------------------
# TAB 2: วิเคราะห์ตลาดแรงงานรายภูมิภาค (REGIONAL DEEP-DIVE)
# -------------------------------------------------------------
with tab2:
    reg_data = get_regional_comparison_data(df, filters)
    area_data = get_area_wage_comparison_data(df, filters)

    # Map lives in Tab 1. Tab 2 keeps regional comparisons.
    map_metric = st.session_state.get('overview_map_metric', 'emp_rate')
    col_rank = st.container()

    with col_rank:
        if valid_metric(kpis.get(map_metric)) and not reg_data.empty:
            with st.container(border=True):
                st.markdown("**🏆 การจัดอันดับภูมิภาค (Regional Ranking)**")
                st.caption("เปรียบเทียบค่าชี้วัดรายภาค (คลิกที่แท่งภูมิภาคเพื่อกรองข้อมูลเฉพาะภาคนั้น)")
                fig_reg_rank = create_regional_ranking_chart(
                    reg_data,
                    metric=map_metric,
                    selected_region=filters.get('region') if filters.get('region') != 'ทั้งหมด' else None
                )
                event_rank = st.plotly_chart(
                    fig_reg_rank,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_regional_rank"
                )
                if handle_chart_selection(event_rank, 'region', value_key='customdata'):
                    st.session_state['_pending_map_sidebar_sync'] = True
                    st.rerun()

    c_scat, c_dumb = st.columns(2)

    with c_scat:
        if valid_metric(kpis.get('avg_wage')) and valid_metric(kpis.get('emp_rate')) and not reg_data.empty:
            with st.container(border=True):
                st.markdown("**⚖️ ค่าจ้างเฉลี่ย vs อัตราการมีงานทำ (Scatter Bubble)**")
                st.caption("ความสัมพันธ์ระหว่างระดับค่าจ้างและอัตรามีงานทำ (ขนาดฟอง = ประชากรทำงาน)")
                fig_scatter = create_wage_vs_employment_scatter(reg_data)
                event_scat = st.plotly_chart(
                    fig_scatter,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_wage_scatter"
                )
                if handle_chart_selection(event_scat, 'region', value_key='customdata'):
                    st.session_state['_pending_map_sidebar_sync'] = True
                    st.rerun()

    with c_dumb:
        if valid_metric(kpis.get('avg_wage')) and not area_data.empty:
            with st.container(border=True):
                st.markdown("**🏙️ ช่องว่างค่าจ้างเมือง vs ชนบท (Dumbbell Chart)**")
                st.caption("เปรียบเทียบค่าจ้างในเขตเทศบาลเทียบกับนอกเขตเทศบาลในแต่ละภาค")
                fig_dumb = create_dumbbell_wage_chart(area_data)
                event_dumb = st.plotly_chart(
                    fig_dumb,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_area_dumbbell"
                )
                if handle_chart_selection(event_dumb, 'region', value_key='customdata'):
                    st.session_state['_pending_map_sidebar_sync'] = True
                    st.rerun()


# -------------------------------------------------------------
# TAB 3: วิเคราะห์กลุ่มประชากรและความแตกต่าง (DEMOGRAPHICS)
# -------------------------------------------------------------
with tab3:
    gender_data = get_demographics_gender_data(df, filters)
    age_data = get_demographics_age_data(df, filters)

    g_col1, g_col2 = st.columns(2)

    with g_col1:
        if valid_metric(kpis.get('avg_wage')) and not gender_data.empty:
            with st.container(border=True):
                st.markdown("**👫 ช่องว่างค่าจ้างระหว่างเพศ (Gender Wage Gap)**")
                st.caption("เปรียบเทียบค่าจ้างเฉลี่ยชาย vs หญิง (คลิกแท่งเพื่อกรองเฉพาะเพศนั้น)")
                fig_gender = create_gender_gap_chart(gender_data)
                event_gender = st.plotly_chart(
                    fig_gender,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_gender_gap"
                )
                if handle_chart_selection(event_gender, 'sex', value_key='customdata'):
                    st.rerun()

    with g_col2:
        if valid_metric(kpis.get('emp_headcount_m')):
            with st.container(border=True):
                st.markdown("**📊 โครงสร้างความหนาแน่นแรงงาน (Matrix Heatmap)**")
                st.caption("การกระจายตัวของจำนวนผู้มีงานทำ (ล้านคน) ตามเพศและช่วงอายุ")
                fig_heat = create_demographic_matrix_heatmap(df, filters)
                st.plotly_chart(fig_heat, use_container_width=True, key="chart_demo_heatmap")

    a_col1, a_col2 = st.columns(2)

    with a_col1:
        if valid_metric(kpis.get('avg_wage')) and not age_data.empty:
            with st.container(border=True):
                st.markdown("**📈 โครงสร้างค่าจ้างตามวัย (Age-Wage Curve)**")
                st.caption("ค่าจ้างเฉลี่ยไต่ระดับตามอายุ และสูงสุดที่วัย 40-59 ปี (คลิกเพื่อกรองช่วงอายุ)")
                fig_age_wage = create_age_wage_chart(age_data)
                event_age_wage = st.plotly_chart(
                    fig_age_wage,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_age_wage"
                )
                if handle_chart_selection(event_age_wage, 'age_group', value_key='customdata'):
                    st.rerun()

    with a_col2:
        if valid_metric(kpis.get('unemp_rate')) and not age_data.empty:
            with st.container(border=True):
                st.markdown("**🚨 การว่างงานในกลุ่มเยาวชน (Youth Unemployment)**")
                st.caption("อัตราว่างงานช่วง 15-24 ปี สูงกว่าวัยผู้ใหญ่อย่างมีนัยสำคัญ (คลิกเพื่อกรอง)")
                fig_youth = create_youth_unemployment_chart(age_data)
                event_youth = st.plotly_chart(
                    fig_youth,
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="points",
                    key="chart_youth_unemp"
                )
                if handle_chart_selection(event_youth, 'age_group', value_key='customdata'):
                    st.rerun()


# -------------------------------------------------------------
# TAB 4: ตารางข้อมูลและคำอธิบายสถิติ (DATA & NOTES)
# -------------------------------------------------------------
with tab4:
    st.markdown("""
    <div class="bento-card">
        <div class="bento-card-title">📋 ตารางสำรวจข้อมูลตลาดแรงงาน (Data Explorer)</div>
        <div class="bento-card-subtitle">แสดงข้อมูลที่สอดคล้องกับตัวกรองที่กำลังใช้งาน พร้อมตัวเลือกค้นหาและส่งออกเป็น CSV</div>
    </div>
    """, unsafe_allow_html=True)

    # Filter df for table view
    tbl_mask = pd.Series(True, index=df.index)
    if filters.get('year') != 'ทั้งหมด':
        tbl_mask = tbl_mask & (df['year'] == int(filters['year']))
    if filters.get('quarter') != 'ทั้งหมด' and int(filters['quarter']) > 0:
        tbl_mask = tbl_mask & (df['quarter'] == int(filters['quarter']))
    if filters.get('region') != 'ทั้งหมด':
        tbl_mask = tbl_mask & (df['clean_region'] == filters['region'])
    if filters.get('area') != 'ทั้งหมด':
        tbl_mask = tbl_mask & (df['clean_area'] == filters['area'])
    if filters.get('sex') != 'ทั้งหมด':
        tbl_mask = tbl_mask & (df['clean_sex'] == filters['sex'])
    if filters.get('age_group') != 'ทั้งหมด':
        tbl_mask = tbl_mask & (df['clean_age'] == filters['age_group'])

    tbl_display = df[tbl_mask][[
        'year', 'quarter', 'clean_region', 'clean_area', 'clean_sex', 'clean_age',
        'avg_wage', 'emp_rate', 'unemp_rate', 'emp_headcount'
    ]].copy()

    tbl_display.rename(columns={
        'year': 'ปี พ.ศ.',
        'quarter': 'ไตรมาส',
        'clean_region': 'ภูมิภาค',
        'clean_area': 'เขตการปกครอง',
        'clean_sex': 'เพศ',
        'clean_age': 'กลุ่มอายุ',
        'avg_wage': 'ค่าจ้างเฉลี่ย (บาท)',
        'emp_rate': 'อัตราการมีงานทำ (%)',
        'unemp_rate': 'อัตราการว่างงาน (%)',
        'emp_headcount': 'ผู้มีงานทำ (พันคน)'
    }, inplace=True)

    st.write(f"พบข้อมูลทั้งหมด: **{len(tbl_display):,} แถว**")
    st.dataframe(tbl_display.head(500), use_container_width=True)

    csv_data = tbl_display.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลดข้อมูลชุดนี้เป็น CSV",
        data=csv_data,
        file_name=f"labor_data_{filters.get('year')}.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.markdown("""
    ### 📖 คำนิยามและข้อจำกัดสำคัญของสถิติแรงงาน (Statistical Notes)
    
    1. **การถ่วงน้ำหนักสถิติ (Weighted Aggregates):**
       - ตัวเลขสถิติในระดับภาพรวม (เช่น ระดับประเทศ ระดับภาค ผลรวมเพศ) ได้รับการคำนวณและถ่วงน้ำหนักโดยสำนักงานสถิติแห่งชาติไว้แล้วในแถว `รวม`
       - ระบบดึงค่าจากแถวผลรวมทางการโดยตรง โดยไม่มีการนำอัตราเปอร์เซ็นต์มาหาค่าเฉลี่ยทางคณิตศาสตร์แบบไม่ถ่วงน้ำหนัก เพื่อรักษาความถูกต้องตามหลักสถิติสูงสุด
    
    2. **หน่วยวัดจำนวนผู้มีงานทำ (`emp_headcount`):**
       - มีหน่วยเป็น **พันคน (Thousand Persons)** หากต้องการแปลงเป็นคนให้คูณด้วย 1,000 หรือแปลงเป็นล้านคนโดยหารด้วย 1,000
    
    3. **ความไม่ต่อเนื่องของสถิติค่าจ้างปี 2567-2568:**
       - ค่าจ้างเฉลี่ยในปี พ.ศ. 2567 และ 2568 จัดเก็บในระดับภาพรวมรายปี (`quarter = 0`) จึงไม่มีข้อมูลแยกรายไตรมาส 1 ถึง 4
    
    4. **การปรับเปลี่ยนการแบ่งภูมิภาคในปี 2568:**
       - สำนักงานสถิติแห่งชาติได้แยก `ภาคตะวันออก` (เดิมอยู่ในภาคกลาง) และ `ภาคใต้ชายแดน` (เดิมอยู่ในภาคใต้) เพิ่มขึ้นเป็น 7 ภูมิภาคตั้งแต่ปี 2568 เป็นต้นมา
    
    5. **ตัวแปรที่ไม่มีในชุดข้อมูล:**
       - ชุดข้อมูลนี้ไม่มีข้อมูลประเภทอุตสาหกรรม/สาขาอาชีพ (`industry`), ระดับการศึกษา (`education`) และจำนวนคนว่างงานเป็นตัวเลขคน ระบบจึงไม่มีการแสดงผลการจัดอันดับอุตสาหกรรมเพื่อความซื่อสัตย์ต่อข้อมูลจริง
    """)
