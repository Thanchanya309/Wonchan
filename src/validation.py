"""
Data Validation and Quality Assurance Module for Thailand Labor Market Dashboard
"""
import pandas as pd
import numpy as np


def validate_dataset_schema(df):
    """
    Validate that the DataFrame contains expected columns and valid data types.
    Returns a dict with status and list of warnings/errors.
    """
    results = {'is_valid': True, 'errors': [], 'warnings': []}

    expected_cols = [
        'year', 'quarter', 'region', 'area', 'sex', 'age_group',
        'avg_wage', 'emp_rate', 'emp_headcount', 'unemp_rate',
        'clean_sex', 'clean_age', 'clean_area', 'clean_region'
    ]

    for col in expected_cols:
        if col not in df.columns:
            results['errors'].append(f"คอลัมน์ขาดหาย: '{col}'")
            results['is_valid'] = False

    if not results['is_valid']:
        return results

    # Value ranges
    # Rates should be between 0 and 100
    if (df['emp_rate'].dropna() < 0).any() or (df['emp_rate'].dropna() > 100).any():
        results['warnings'].append("พบค่าวัด emp_rate นอกช่วง 0 - 100%")

    if (df['unemp_rate'].dropna() < 0).any() or (df['unemp_rate'].dropna() > 100).any():
        results['warnings'].append("พบค่าวัด unemp_rate นอกช่วง 0 - 100%")

    # Wages should be positive
    if (df['avg_wage'].dropna() <= 0).any():
        results['warnings'].append("พบค่าวัด avg_wage ที่น้อยกว่าหรือเท่ากับ 0")

    # Headcount should be positive
    if (df['emp_headcount'].dropna() <= 0).any():
        results['warnings'].append("พบค่าวัด emp_headcount ที่น้อยกว่าหรือเท่ากับ 0")

    # Quarter values must be in [0, 1, 2, 3, 4]
    invalid_quarters = set(df['quarter'].unique()) - {0, 1, 2, 3, 4}
    if invalid_quarters:
        results['errors'].append(f"พบค่าไตรมาสที่ไม่ถูกต้อง: {invalid_quarters}")
        results['is_valid'] = False

    return results


def check_metric_filter_compatibility(metric_name, filters):
    """
    Check if a specific metric is compatible with the selected filters.
    Returns (is_compatible, thai_caveat_message)
    """
    selected_year = filters.get('year')
    selected_quarter = filters.get('quarter')
    selected_area = filters.get('area')
    selected_region = filters.get('region')

    # Headcount vs Area
    if metric_name == 'emp_headcount' and selected_area and selected_area != 'ทั้งหมด':
        return False, "จำนวนผู้มีงานทำ (Headcount) ในชุดข้อมูลดั้งเดิมไม่สามารถแยกตามในเขต/นอกเขตเทศบาลได้ ข้อมูลที่แสดงจึงเป็นภาพรวมทั้งพื้นที่"

    # Wage vs Quarter in 2567-2568
    if metric_name == 'avg_wage' and selected_year in [2567, 2568] and selected_quarter not in ['ทั้งหมด', 0, None]:
        return False, f"สถิติค่าจ้างเฉลี่ยปี พ.ศ. {selected_year} มีเฉพาะข้อมูลสรุปภาพรวมรายปี (ไตรมาส 0) ไม่สามารถแยกรายไตรมาส 1-4 ได้"

    # Region 7 vs 5 in 2568
    if selected_region in ['ภาคตะวันออก', 'ภาคใต้ชายแดน'] and selected_year and selected_year < 2568:
        return False, f"ภูมิภาค '{selected_region}' เริ่มมีการจำแนกแยกเฉพาะในปี พ.ศ. 2568 เป็นต้นไป ในปีก่อนหน้าจะรวมอยู่ในภาคกลางและภาคใต้"

    return True, ""
