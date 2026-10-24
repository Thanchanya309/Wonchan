"""
Data Loader and Normalization Module for Thailand Labor Market Dashboard
"""
import os
import re
import pandas as pd
import numpy as np

# Standard categories order
AGE_ORDER = [
    '15-19 ปี',
    '20-24 ปี',
    '25-29 ปี',
    '30-34 ปี',
    '35-39 ปี',
    '40-49 ปี',
    '50-59 ปี',
    '60 ปีขึ้นไป',
    'รวม'
]

REGION_ORDER = [
    'กรุงเทพมหานคร',
    'ภาคกลาง',
    'ภาคเหนือ',
    'ภาคตะวันออกเฉียงเหนือ',
    'ภาคใต้',
    'ภาคตะวันออก',
    'ภาคใต้ชายแดน',
    'รวม'
]

AREA_ORDER = ['ในเขตเทศบาล', 'นอกเขตเทศบาล', 'รวม']
SEX_ORDER = ['ชาย', 'หญิง', 'รวม']


def clean_string_category(val):
    """Strip whitespace and leading digits/punctuation like '1) ', '1. '"""
    if pd.isna(val):
        return val
    s = str(val).strip()
    s = re.sub(r'^\d+[\.\)]\s*', '', s)
    return s.strip()


def normalize_sex(val):
    if pd.isna(val):
        return 'ไม่ระบุ'
    s = clean_string_category(val)
    if s in ['ชาย', '1. ชาย']:
        return 'ชาย'
    if s in ['หญิง', '2. หญิง']:
        return 'หญิง'
    if s in ['รวม', 'Total']:
        return 'รวม'
    return s


def normalize_age_group(val):
    if pd.isna(val):
        return 'ไม่ระบุ'
    s = clean_string_category(val)
    if s in ['Total', 'รวม']:
        return 'รวม'
    if s in ['60 ขึ้นไป', '60 ปีขึ้นไป', '8. 60 ปีขึ้นไป']:
        return '60 ปีขึ้นไป'
    return s


def normalize_area(val):
    if pd.isna(val):
        return 'ไม่ระบุ'
    s = clean_string_category(val)
    if s in ['เขตเทศบาล', 'ในเขตเทศบาล', '1) เขตเทศบาล', '1) ในเขตเทศบาล']:
        return 'ในเขตเทศบาล'
    if s in ['นอกเขตเทศบาล', '2) นอกเขตเทศบาล']:
        return 'นอกเขตเทศบาล'
    if s in ['รวม', 'Total']:
        return 'รวม'
    return s


def normalize_region(val):
    if pd.isna(val):
        return 'ไม่ระบุ'
    s = clean_string_category(val)
    if s in ['Total', 'รวม']:
        return 'รวม'
    if s in ['กลาง', 'ภาคกลาง', '2) กลาง', '2) ภาคกลาง']:
        return 'ภาคกลาง'
    if s in ['ใต้', 'ภาคใต้', '3) ใต้', '5) ภาคใต้']:
        return 'ภาคใต้'
    if s in ['ใต้ชายแดน', 'ภาคใต้ชายแดน', '4) ใต้ชายแดน']:
        return 'ภาคใต้ชายแดน'
    if s in ['ตะวันออก', 'ภาคตะวันออก', '5) ตะวันออก']:
        return 'ภาคตะวันออก'
    if s in ['ตะวันออกเฉียงเหนือ', 'ภาคตะวันออกเฉียงเหนือ', '6) ตะวันออกเฉียงเหนือ', '4) ภาคตะวันออกเฉียงเหนือ']:
        return 'ภาคตะวันออกเฉียงเหนือ'
    if s in ['เหนือ', 'ภาคเหนือ', '7) เหนือ', '3) ภาคเหนือ']:
        return 'ภาคเหนือ'
    if s in ['กรุงเทพมหานคร', '1) กรุงเทพมหานคร']:
        return 'กรุงเทพมหานคร'
    return s


def format_time_label(row):
    year = int(row['year'])
    quarter = int(row['quarter'])
    if quarter == 0:
        return f"{year} (ทั้งปี)"
    return f"{year} Q{quarter}"


def locate_dataset_file(custom_path=None):
    """Find dataset in standard locations"""
    candidates = [
        custom_path,
        os.path.join("data", "raw", "final_labor_master_data.csv"),
        "final_labor_master_data.csv",
        "final_labor_master_data(1).csv",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw", "final_labor_master_data.csv"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "final_labor_master_data(1).csv"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def load_labor_data(filepath=None):
    """
    Load raw CSV dataset and apply data normalization.
    Returns cleaned pandas DataFrame with normalized category columns.
    """
    path = locate_dataset_file(filepath)
    if not path:
        raise FileNotFoundError(
            "ไม่พบไฟล์ข้อมูลชุดสถิติตลาดแรงงาน! กรุณาวางไฟล์ final_labor_master_data.csv ในโฟลเดอร์ data/raw/"
        )

    df = pd.read_csv(path)

    # Validate essential columns
    required_cols = ['year', 'quarter', 'region', 'area', 'sex', 'age_group',
                     'avg_wage', 'emp_rate', 'emp_headcount', 'unemp_rate']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"ชุดข้อมูลขาดคอลัมน์ที่จำเป็น: {missing_cols}")

    # Ensure types
    df['year'] = df['year'].astype(int)
    df['quarter'] = df['quarter'].astype(int)

    # Normalized dimension columns
    df['clean_sex'] = df['sex'].apply(normalize_sex)
    df['clean_age'] = df['age_group'].apply(normalize_age_group)
    df['clean_area'] = df['area'].apply(normalize_area)
    df['clean_region'] = df['region'].apply(normalize_region)
    df['time_label'] = df.apply(format_time_label, axis=1)

    # Sort helper for chronological plots
    df['time_sort_key'] = df['year'] * 10 + df['quarter']

    return df


# Try to export a cached version for Streamlit
try:
    import streamlit as st
    @st.cache_data(show_spinner="กำลังโหลดและประมวลผลข้อมูลตลาดแรงงาน...")
    def get_cached_labor_data(filepath=None):
        return load_labor_data(filepath)
except ImportError:
    get_cached_labor_data = load_labor_data
