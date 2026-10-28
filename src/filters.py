"""
Global Filter State and Cross-Filtering Management for Thailand Labor Market Dashboard

หลักการ
- st.session_state['filters'] คือตัวกรองกลางตัวเดียว (single source of truth)
- widget ใน Sidebar เป็นเพียง "กระจกเงา" (mirror) เก็บใน key sb_* และถูกซิงค์จาก filters
- ทุกการเปลี่ยนตัวกรอง (Sidebar / คลิกแผนที่ / คลิกกราฟ / ปุ่มกลับ) เกิดใน callback
  ซึ่ง Streamlit รันก่อนสคริปต์หลัก จึงแก้ค่า widget ได้อย่างปลอดภัยและไม่ต้องเรียก st.rerun()
- ทุกครั้งที่ตัวกรองเปลี่ยน จะเพิ่ม chart_nonce เพื่อรีเซ็ตสถานะการเลือกค้างของกราฟทุกตัว
  (กันการคลิกเก่าถูกประมวลผลซ้ำ จึงไม่เกิด Rerun วนซ้ำ)
"""
from functools import partial

import numpy as np
import pandas as pd
import streamlit as st

from src.data_loader import REGION_ORDER

ALL = 'ทั้งหมด'

DEFAULT_FILTERS = {
    'year': ALL,
    'quarter': ALL,
    'region': ALL,
    'area': ALL,
    'sex': ALL,
    'age_group': ALL
}

# key ของ widget ใน Sidebar ที่ซิงค์กับแต่ละตัวกรอง
SIDEBAR_KEYS = {
    'year': 'sb_year',
    'quarter': 'sb_quarter',
    'region': 'sb_region',
    'area': 'sb_area',
    'sex': 'sb_sex',
    'age_group': 'sb_age',
}

VALID_AREAS = [ALL, 'ในเขตเทศบาล', 'นอกเขตเทศบาล']
VALID_SEX = [ALL, 'ชาย', 'หญิง']
VALID_AGES = [
    ALL, '15-19 ปี', '20-24 ปี', '25-29 ปี', '30-34 ปี',
    '35-39 ปี', '40-49 ปี', '50-59 ปี', '60 ปีขึ้นไป'
]

_METRIC_COLUMNS = ['avg_wage', 'emp_rate', 'unemp_rate', 'emp_headcount']


# -------------------------------------------------------------
# State initialisation
# -------------------------------------------------------------
def _sync_widgets():
    """คัดลอกค่าจาก filters ไปยัง widget key (เรียกได้ใน callback หรือก่อนสร้าง widget เท่านั้น)."""
    current = st.session_state.filters
    for dimension, widget_key in SIDEBAR_KEYS.items():
        st.session_state[widget_key] = current[dimension]


def _bump_nonce():
    st.session_state['chart_nonce'] = st.session_state.get('chart_nonce', 0) + 1


def init_filter_state():
    """Initialize filters (and sidebar mirrors) in st.session_state if not already present."""
    if 'filters' not in st.session_state:
        st.session_state.filters = DEFAULT_FILTERS.copy()
    else:
        for dimension, default in DEFAULT_FILTERS.items():
            st.session_state.filters.setdefault(dimension, default)

    if 'chart_nonce' not in st.session_state:
        st.session_state['chart_nonce'] = 0
    if 'last_clicked_event' not in st.session_state:
        st.session_state.last_clicked_event = None

    for dimension, widget_key in SIDEBAR_KEYS.items():
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state.filters[dimension]


def get_current_filters():
    """Retrieve current active filters dictionary."""
    init_filter_state()
    return st.session_state.filters


# -------------------------------------------------------------
# Filter mutations (ใช้ใน callback)
# -------------------------------------------------------------
def apply_filter(dimension, value):
    """
    ตั้งค่าตัวกรองหนึ่งมิติ พร้อมซิงค์ widget ใน Sidebar และรีเซ็ตสถานะเลือกของกราฟ
    คืนค่า True ถ้าค่าเปลี่ยนจริง
    """
    init_filter_state()
    if dimension not in DEFAULT_FILTERS:
        return False
    if str(st.session_state.filters.get(dimension)) == str(value):
        return False
    st.session_state.filters[dimension] = value
    # ปีเปลี่ยนแล้วภาค/ไตรมาสอาจใช้ไม่ได้ จะถูกตรวจใน sanitize_filters ตอน rerun
    _sync_widgets()
    _bump_nonce()
    return True


def set_filter(dimension, value):
    """Update a single filter in session state (เข้ากันได้กับโค้ดเดิม)."""
    return apply_filter(dimension, value)


def clear_filter(dimension):
    """Reset a single filter to its default ('ทั้งหมด' หรือปีเริ่มต้น)."""
    init_filter_state()
    if dimension == 'year':
        apply_filter('year', DEFAULT_FILTERS['year'])
    else:
        apply_filter(dimension, ALL)


def reset_all_filters():
    """Reset all filters back to default values."""
    init_filter_state()
    st.session_state.filters = DEFAULT_FILTERS.copy()
    st.session_state.last_clicked_event = None
    _sync_widgets()
    _bump_nonce()


def on_sidebar_change(dimension):
    """on_change callback ของ selectbox ใน Sidebar: คัดลอกค่าจาก widget เข้า filters."""
    init_filter_state()
    widget_key = SIDEBAR_KEYS[dimension]
    if widget_key not in st.session_state:
        return
    value = st.session_state[widget_key]
    if isinstance(value, (np.integer,)):
        value = int(value)
    if str(st.session_state.filters.get(dimension)) != str(value):
        st.session_state.filters[dimension] = value
        _bump_nonce()


# -------------------------------------------------------------
# Data-driven options (รองรับการแบ่ง 5 / 7 ภาคตามปีจริง)
# -------------------------------------------------------------
def get_regions_for_year(df, year):
    """ภูมิภาคที่มีข้อมูลจริงในปีนั้น (5 ภาคถึงปี 2567, 7 ภาคตั้งแต่ปี 2568) เรียงตาม REGION_ORDER."""
    sub = df if year == ALL else df[df['year'] == int(year)]
    sub = sub[~sub['clean_region'].isin(['รวม', 'ไม่ระบุ'])]
    sub = sub[sub[_METRIC_COLUMNS].notna().any(axis=1)]
    found = set(sub['clean_region'].unique().tolist())
    ordered = [r for r in REGION_ORDER if r in found]
    ordered += sorted(r for r in found if r not in REGION_ORDER)
    return ordered


def get_quarters_for_year(df, year):
    """ไตรมาส 1-4 ที่มีข้อมูลจริงในปีนั้น (เช่น ปี 2569 มีเฉพาะไตรมาส 1)."""
    sub = df[df['quarter'] > 0] if year == ALL else df[(df['year'] == int(year)) & (df['quarter'] > 0)]
    sub = sub[sub[_METRIC_COLUMNS].notna().any(axis=1)]
    return sorted(int(q) for q in sub['quarter'].unique())


def sanitize_filters(df):
    """
    ตรวจให้ตัวกรองทุกตัวใช้ได้กับข้อมูลจริง แล้วซิงค์ widget
    ต้องเรียกก่อนสร้าง widget ใน Sidebar (ในรอบสคริปต์เดียวกัน)
    """
    init_filter_state()
    current = st.session_state.filters
    changed = False

    years = sorted(int(y) for y in df['year'].dropna().unique())
    raw_year = current.get('year', ALL)
    if raw_year == ALL:
        year = ALL
    else:
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            year = ALL
        if year not in years:
            year = ALL
    if current.get('year') != year:
        current['year'] = year
        changed = True

    quarters = get_quarters_for_year(df, year)
    quarter = current.get('quarter', ALL)
    if quarter != ALL:
        try:
            quarter = int(quarter)
        except (TypeError, ValueError):
            quarter = ALL
        if quarter not in quarters:
            quarter = ALL
    if current.get('quarter') != quarter:
        current['quarter'] = quarter
        changed = True

    regions = get_regions_for_year(df, year)
    if current.get('region', ALL) != ALL and current.get('region') not in regions:
        current['region'] = ALL
        changed = True

    for dimension, valid in (('area', VALID_AREAS), ('sex', VALID_SEX), ('age_group', VALID_AGES)):
        if current.get(dimension, ALL) not in valid:
            current[dimension] = ALL
            changed = True

    _sync_widgets()
    if changed:
        _bump_nonce()
    return changed


# -------------------------------------------------------------
# Chart interaction (คลิกแผนที่ / คลิกกราฟ)
# -------------------------------------------------------------
def chart_key(name):
    """key ของกราฟที่ผูกกับ chart_nonce เพื่อให้สถานะการเลือกถูกรีเซ็ตทุกครั้งที่ตัวกรองเปลี่ยน."""
    return f"{name}_{st.session_state.get('chart_nonce', 0)}"


def _get(obj, name, default=None):
    """อ่านค่าจาก dict หรือ object (Streamlit คืน selection เป็น dict ที่เข้าถึงแบบ attribute ได้)."""
    if obj is None:
        return default
    try:
        return obj[name]
    except (KeyError, TypeError, IndexError):
        return getattr(obj, name, default)


def _first(value):
    """customdata อาจเป็นค่าเดี่ยวหรือ list/tuple -> ใช้ค่าแรก."""
    while isinstance(value, (list, tuple, np.ndarray)):
        if len(value) == 0:
            return None
        value = value[0]
    return value


def extract_clicked_value(state):
    """
    ดึงค่าที่ผู้ใช้คลิกจากสถานะของ st.plotly_chart(on_select=...)
    ลำดับความสำคัญ: customdata -> location (Choropleth) -> text
    คืน None ถ้าไม่มีการเลือก
    """
    selection = _get(state, 'selection')
    points = _get(selection, 'points') or []
    if len(points) == 0:
        return None
    point = points[0]
    for field in ('customdata', 'location', 'text'):
        candidate = _first(_get(point, field))
        if candidate is not None and not (isinstance(candidate, float) and np.isnan(candidate)):
            return candidate
    return None


def _coerce(dimension, value):
    if dimension == 'year':
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
    if dimension == 'quarter':
        try:
            q = int(float(value))
        except (TypeError, ValueError):
            return None
        return q if 1 <= q <= 4 else None
    return str(value)


def _on_chart_select(key, dimension, valid_values):
    """Callback ของ st.plotly_chart(on_select=callable): อัปเดตตัวกรองกลางจากจุดที่คลิก."""
    state = st.session_state.get(key)
    clicked = extract_clicked_value(state)
    if clicked is None:
        return
    value = _coerce(dimension, clicked)
    if value is None:
        return
    if valid_values is not None and str(value) not in {str(v) for v in valid_values}:
        return
    st.session_state.last_clicked_event = {'dimension': dimension, 'value': value}
    apply_filter(dimension, value)


def make_select_callback(key, dimension, valid_values=None):
    """
    สร้าง callback สำหรับ on_select ของกราฟ/แผนที่
    key           : key ของ st.plotly_chart (ใช้อ่านสถานะการเลือก)
    dimension     : ตัวกรองที่จะถูกอัปเดต (year, quarter, region, sex, age_group)
    valid_values  : ค่าที่ยอมรับ (เช่น รายชื่อภาคของปีนั้น) ถ้า None = ไม่ตรวจ
    """
    values = tuple(valid_values) if valid_values is not None else None
    return partial(_on_chart_select, key, dimension, values)


def handle_chart_selection(event, dimension, value_key='x'):
    """
    (คงไว้เพื่อความเข้ากันได้กับโค้ดเดิม) ประมวลผล event ที่ได้จาก st.plotly_chart โดยตรง
    คืน True ถ้าตัวกรองเปลี่ยน
    """
    clicked = extract_clicked_value(event)
    if clicked is None:
        points = _get(_get(event, 'selection'), 'points') or []
        if points:
            clicked = _first(_get(points[0], value_key))
    if clicked is None:
        return False
    value = _coerce(dimension, clicked)
    if value is None:
        return False
    return apply_filter(dimension, value)