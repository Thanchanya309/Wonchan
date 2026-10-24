"""
Thailand Labor Market Interactive Analytics Dashboard
Built with Streamlit, Pandas, and Plotly
Features: Bi-directional Cross-filtering, Modern Admin Bento Grid, Official NSO Statistical Rules
"""
import streamlit as st
import pandas as pd
import numpy as np

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

# Top KPI Bento Grid
col1, col2, col3, col4 = st.columns(4)

with col1:
    wage_disp = f"{kpis['avg_wage']:,.0f}" if kpis['avg_wage'] is not None else "ไม่มีข้อมูล"
    st.markdown(f"""
    <div class="kpi-card kpi-card-1">
        <div class="kpi-title">💵 ค่าจ้างเฉลี่ย</div>
        <div class="kpi-value">{wage_disp}<span class="kpi-unit">บาท/เดือน</span></div>
        <div class="kpi-subtext">ประชากรมีงานทำที่เป็นลูกจ้าง</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    emp_disp = f"{kpis['emp_rate']:.2f}" if kpis['emp_rate'] is not None else "ไม่มีข้อมูล"
    st.markdown(f"""
    <div class="kpi-card kpi-card-2">
        <div class="kpi-title">📈 อัตราการมีงานทำ</div>
        <div class="kpi-value">{emp_disp}<span class="kpi-unit">%</span></div>
        <div class="kpi-subtext">สัดส่วนต่อกำลังแรงงานรวม</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    unemp_disp = f"{kpis['unemp_rate']:.2f}" if kpis['unemp_rate'] is not None else "ไม่มีข้อมูล"
    st.markdown(f"""
    <div class="kpi-card kpi-card-3">
        <div class="kpi-title">⚠️ อัตราการว่างงาน</div>
        <div class="kpi-value">{unemp_disp}<span class="kpi-unit">%</span></div>
        <div class="kpi-subtext">สัดส่วนผู้ว่างงานต่อกำลังแรงงาน</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    if kpis['emp_headcount_m'] is not None:
        hc_disp = f"{kpis['emp_headcount_m']:.2f}"
        hc_unit = "ล้านคน"
        hc_sub = f"({kpis['emp_headcount_k']:,.1f} พันคน)"
    else:
        hc_disp = "ไม่มีข้อมูล"
        hc_unit = ""
        hc_sub = ""
    st.markdown(f"""
    <div class="kpi-card kpi-card-4">
        <div class="kpi-title">👥 ประชากรผู้มีงานทำ</div>
        <div class="kpi-value">{hc_disp}<span class="kpi-unit">{hc_unit}</span></div>
        <div class="kpi-subtext">{hc_sub}</div>
    </div>
    """, unsafe_allow_html=True)

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
    ts_data, wage_data = get_time_series_data(df, filters)

    st.markdown("""
    <div class="bento-card">
        <div class="bento-card-title">📈 แนวโน้มอัตราการมีงานทำและอัตราการว่างงานตามเวลา</div>
        <div class="bento-card-subtitle">แสดงการเคลื่อนไหวของตลาดแรงงานรายปีและรายไตรมาส (คลิกเลือกจุดบนกราฟเพื่อกรองปี/ไตรมาส)</div>
    </div>
    """, unsafe_allow_html=True)

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
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">💵 ทิศทางการเติบโตของค่าจ้างเฉลี่ย (บาท/เดือน)</div>
            <div class="bento-card-subtitle">ค่าจ้างเฉลี่ยรายปีตามตัวกรองที่เลือก (คลิกจุดปีบนกราฟเพื่อเจาะจงปี)</div>
        </div>
        """, unsafe_allow_html=True)
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
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">🌾 การเปลี่ยนแปลงตามฤดูกาลในแต่ละไตรมาส (Seasonality)</div>
            <div class="bento-card-subtitle">เปรียบเทียบอัตราว่างงานเฉลี่ย Q1 (แล้ง) ถึง Q4 (เก็บเกี่ยว) ชี้ชัดผลกระทบภาคเกษตรกรรม</div>
        </div>
        """, unsafe_allow_html=True)
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

    st.markdown("""
    <div class="bento-card">
        <div class="bento-card-title">👥 จำนวนผู้มีงานทำรวมของประเทศตามช่วงเวลา (ล้านคน)</div>
        <div class="bento-card-subtitle">สะท้อนขนาดกำลังแรงงานที่แท้จริงจากประมาณการประชากร (2555 - 2569)</div>
    </div>
    """, unsafe_allow_html=True)
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

    m_col1, m_col2 = st.columns([1, 3])
    with m_col1:
        map_metric = st.selectbox(
            "เลือกตัวชี้วัดสำหรับแผนที่และการจัดอันดับ:",
            options=['avg_wage', 'unemp_rate', 'emp_rate'],
            format_func=lambda x: '💵 ค่าจ้างเฉลี่ย (บาท/เดือน)' if x == 'avg_wage' else ('⚠️ อัตราการว่างงาน (%)' if x == 'unemp_rate' else '📈 อัตราการมีงานทำ (%)'),
            key="sb_map_metric"
        )

    col_map, col_rank = st.columns([1.1, 1])

    with col_map:
        st.markdown(f"""
        <div class="bento-card">
            <div class="bento-card-title">🗺️ แผนที่ภูมิภาคประเทศไทย (Choropleth Map)</div>
            <div class="bento-card-subtitle">แสดงความเข้มของตัวชี้วัดตามภูมิภาคประจำปี พ.ศ. {filters.get('year', 2568)}</div>
        </div>
        """, unsafe_allow_html=True)
        fig_map = create_thailand_map(reg_data, metric=map_metric, year=filters.get('year', 2568))
        st.plotly_chart(fig_map, use_container_width=True, key="chart_regional_map")

    with col_rank:
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">🏆 การจัดอันดับภูมิภาค (Regional Ranking)</div>
            <div class="bento-card-subtitle">เปรียบเทียบค่าชี้วัดรายภาค (คลิกที่แท่งภูมิภาคเพื่อกรองข้อมูลเฉพาะภาคนั้น)</div>
        </div>
        """, unsafe_allow_html=True)
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
            st.rerun()

    c_scat, c_dumb = st.columns(2)

    with c_scat:
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">⚖️ ค่าจ้างเฉลี่ย vs อัตราการมีงานทำ (Scatter Bubble)</div>
            <div class="bento-card-subtitle">ความสัมพันธ์ระหว่างระดับค่าจ้างและอัตรามีงานทำ (ขนาดฟอง = ประชากรทำงาน)</div>
        </div>
        """, unsafe_allow_html=True)
        fig_scatter = create_wage_vs_employment_scatter(reg_data)
        event_scat = st.plotly_chart(
            fig_scatter,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="chart_wage_scatter"
        )
        if handle_chart_selection(event_scat, 'region', value_key='customdata'):
            st.rerun()

    with c_dumb:
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">🏙️ ช่องว่างค่าจ้างเมือง vs ชนบท (Dumbbell Chart)</div>
            <div class="bento-card-subtitle">เปรียบเทียบค่าจ้างในเขตเทศบาลเทียบกับนอกเขตเทศบาลในแต่ละภาค</div>
        </div>
        """, unsafe_allow_html=True)
        fig_dumb = create_dumbbell_wage_chart(area_data)
        event_dumb = st.plotly_chart(
            fig_dumb,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="chart_area_dumbbell"
        )
        if handle_chart_selection(event_dumb, 'region', value_key='customdata'):
            st.rerun()


# -------------------------------------------------------------
# TAB 3: วิเคราะห์กลุ่มประชากรและความแตกต่าง (DEMOGRAPHICS)
# -------------------------------------------------------------
with tab3:
    gender_data = get_demographics_gender_data(df, filters)
    age_data = get_demographics_age_data(df, filters)

    g_col1, g_col2 = st.columns(2)

    with g_col1:
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">👫 ช่องว่างค่าจ้างระหว่างเพศ (Gender Wage Gap)</div>
            <div class="bento-card-subtitle">เปรียบเทียบค่าจ้างเฉลี่ยชาย vs หญิง (คลิกแท่งเพื่อกรองเฉพาะเพศนั้น)</div>
        </div>
        """, unsafe_allow_html=True)
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
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">📊 โครงสร้างความหนาแน่นแรงงาน (Matrix Heatmap)</div>
            <div class="bento-card-subtitle">การกระจายตัวของจำนวนผู้มีงานทำ (ล้านคน) ตามเพศและช่วงอายุ</div>
        </div>
        """, unsafe_allow_html=True)
        fig_heat = create_demographic_matrix_heatmap(df, filters)
        st.plotly_chart(fig_heat, use_container_width=True, key="chart_demo_heatmap")

    a_col1, a_col2 = st.columns(2)

    with a_col1:
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">📈 โครงสร้างค่าจ้างตามวัย (Age-Wage Curve)</div>
            <div class="bento-card-subtitle">ค่าจ้างเฉลี่ยไต่ระดับตามอายุ และสูงสุดที่วัย 40-59 ปี (คลิกเพื่อกรองช่วงอายุ)</div>
        </div>
        """, unsafe_allow_html=True)
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
        st.markdown("""
        <div class="bento-card">
            <div class="bento-card-title">🚨 การว่างงานในกลุ่มเยาวชน (Youth Unemployment)</div>
            <div class="bento-card-subtitle">อัตราว่างงานช่วง 15-24 ปี สูงกว่าวัยผู้ใหญ่อย่างมีนัยสำคัญ (คลิกเพื่อกรอง)</div>
        </div>
        """, unsafe_allow_html=True)
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
