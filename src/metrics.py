"""
Statistical Calculation and Metric Engine for Thailand Labor Market Dashboard
Complies with official NSO statistical guidelines (no rate summing, explicit weighted totals).
"""
import pandas as pd
import numpy as np


def get_kpis(df, filters):
    """
    Compute key labor market metrics based on active filters.
    Returns:
        dict: {
            'avg_wage': float or None,
            'emp_rate': float or None,
            'unemp_rate': float or None,
            'emp_headcount_k': float or None,
            'emp_headcount_m': float or None,
            'wage_caveat': str,
            'headcount_caveat': str
        }
    """
    year = filters.get('year', 'ทั้งหมด')
    quarter = filters.get('quarter', 'ทั้งหมด')
    region = filters.get('region', 'ทั้งหมด')
    area = filters.get('area', 'ทั้งหมด')
    sex = filters.get('sex', 'ทั้งหมด')
    age_group = filters.get('age_group', 'ทั้งหมด')

    # Target values in dimension columns for rate/wage extraction:
    # If filter is 'ทั้งหมด', look for official weighted total row 'รวม'
    target_region = 'รวม' if region == 'ทั้งหมด' else region
    target_area = 'รวม' if area == 'ทั้งหมด' else area
    target_sex = 'รวม' if sex == 'ทั้งหมด' else sex
    target_age = 'รวม' if age_group == 'ทั้งหมด' else age_group

    wage_val = None
    emp_rate_val = None
    unemp_rate_val = None
    wage_caveat = ""
    headcount_caveat = ""

    # Build base mask for rates and wage
    mask = (
        (df['clean_region'] == target_region) &
        (df['clean_sex'] == target_sex) &
        (df['clean_age'] == target_age)
    )

    # For Bangkok, area is only 'ในเขตเทศบาล'
    if target_region == 'กรุงเทพมหานคร' and target_area == 'รวม':
        mask_area = mask & (df['clean_area'] == 'ในเขตเทศบาล')
    else:
        mask_area = mask & (df['clean_area'] == target_area)

    # Filter by Year if specified
    if year != 'ทั้งหมด':
        mask_year = mask_area & (df['year'] == int(year))
    else:
        # Default to latest available year with data (e.g. 2568 or 2567)
        latest_year = 2568
        mask_year = mask_area & (df['year'] == latest_year)

    # 1. Calculate / Extract emp_rate and unemp_rate
    sub_rates = df[mask_year]
    if quarter != 'ทั้งหมด' and int(quarter) > 0:
        sub_rates_q = sub_rates[sub_rates['quarter'] == int(quarter)]
    else:
        # If quarter is 'ทั้งหมด', take the latest quarter available in that year
        valid_qs = sub_rates[sub_rates['emp_rate'].notnull()]['quarter']
        latest_q = valid_qs.max() if len(valid_qs) > 0 else 4
        sub_rates_q = sub_rates[sub_rates['quarter'] == latest_q]

    if not sub_rates_q.empty:
        emp_rate_row = sub_rates_q['emp_rate'].dropna()
        if not emp_rate_row.empty:
            emp_rate_val = float(emp_rate_row.iloc[0])

        unemp_rate_row = sub_rates_q['unemp_rate'].dropna()
        if not unemp_rate_row.empty:
            unemp_rate_val = float(unemp_rate_row.iloc[0])

    # 2. Calculate / Extract avg_wage
    # Handle Q0 wage for 2567-2568
    cur_year = int(year) if year != 'ทั้งหมด' else 2568
    if cur_year in [2567, 2568]:
        # Wage is stored in quarter 0
        q0_sub = df[mask_area & (df['year'] == cur_year) & (df['quarter'] == 0)]
        if not q0_sub.empty and q0_sub['avg_wage'].notnull().any():
            wage_val = float(q0_sub['avg_wage'].dropna().mean())
            if quarter != 'ทั้งหมด' and int(quarter) > 0:
                wage_caveat = f"ค่าจ้างปี {cur_year} เผยแพร่เฉพาะภาพรวมทั้งปี (ไตรมาส 0)"
    else:
        # Normal quarter wage for 2561-2566
        if quarter != 'ทั้งหมด' and int(quarter) > 0:
            wage_sub = sub_rates[sub_rates['quarter'] == int(quarter)]
        else:
            wage_sub = sub_rates[sub_rates['avg_wage'].notnull()]
        if not wage_sub.empty and wage_sub['avg_wage'].notnull().any():
            wage_val = float(wage_sub['avg_wage'].dropna().iloc[-1])

    # 3. Calculate Headcount
    # Headcount is summed across non-duplicate sub-slices
    hc_mask = df['emp_headcount'].notnull()
    if year != 'ทั้งหมด':
        hc_mask = hc_mask & (df['year'] == int(year))
    else:
        hc_mask = hc_mask & (df['year'] == 2568)

    if quarter != 'ทั้งหมด' and int(quarter) > 0:
        hc_mask = hc_mask & (df['quarter'] == int(quarter))
    else:
        # Take latest quarter in that year
        sub_hc = df[hc_mask]
        if not sub_hc.empty:
            latest_q = sub_hc['quarter'].max()
            hc_mask = hc_mask & (df['quarter'] == latest_q)

    if region != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_region'] == region)
    if sex != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_sex'] == sex)
    if age_group != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_age'] == age_group)

    # Deduplicate to prevent area-broadcast triple counting in 2561-2566
    hc_df = df[hc_mask].drop_duplicates(subset=['year', 'quarter', 'clean_region', 'clean_sex', 'clean_age'])
    if not hc_df.empty:
        hc_sum_k = float(hc_df['emp_headcount'].sum())
        hc_sum_m = round(hc_sum_k / 1000.0, 2)
    else:
        hc_sum_k = None
        hc_sum_m = None

    if area != 'ทั้งหมด':
        headcount_caveat = "จำนวนผู้มีงานทำ (Headcount) ในชุดข้อมูลเดิมไม่มีการจำแนกตามเขตเทศบาล ตัวเลขจึงเป็นภาพรวมพื้นที่"

    return {
        'avg_wage': round(wage_val, 2) if wage_val is not None else None,
        'emp_rate': round(emp_rate_val, 2) if emp_rate_val is not None else None,
        'unemp_rate': round(unemp_rate_val, 2) if unemp_rate_val is not None else None,
        'emp_headcount_k': round(hc_sum_k, 1) if hc_sum_k is not None else None,
        'emp_headcount_m': hc_sum_m,
        'wage_caveat': wage_caveat,
        'headcount_caveat': headcount_caveat
    }


def get_time_series_data(df, filters):
    """
    Extract time series for labor rates and wages over years and quarters.
    """
    region = filters.get('region', 'ทั้งหมด')
    area = filters.get('area', 'ทั้งหมด')
    sex = filters.get('sex', 'ทั้งหมด')
    age_group = filters.get('age_group', 'ทั้งหมด')

    target_region = 'รวม' if region == 'ทั้งหมด' else region
    target_area = 'รวม' if area == 'ทั้งหมด' else area
    target_sex = 'รวม' if sex == 'ทั้งหมด' else sex
    target_age = 'รวม' if age_group == 'ทั้งหมด' else age_group

    mask = (
        (df['clean_region'] == target_region) &
        (df['clean_sex'] == target_sex) &
        (df['clean_age'] == target_age)
    )
    if target_region == 'กรุงเทพมหานคร' and target_area == 'รวม':
        mask = mask & (df['clean_area'] == 'ในเขตเทศบาล')
    else:
        mask = mask & (df['clean_area'] == target_area)

    # Exclude Q0 for quarterly trends
    sub_q = df[mask & (df['quarter'] > 0)].sort_values(by=['year', 'quarter'])

    ts_data = sub_q[['year', 'quarter', 'time_label', 'emp_rate', 'unemp_rate', 'avg_wage']].copy()

    # Also extract annual wage points (including Q0 for 2567-2568)
    wage_mask = mask & (df['avg_wage'].notnull())
    wage_data = df[wage_mask].groupby('year')['avg_wage'].mean().reset_index()
    wage_data.rename(columns={'avg_wage': 'annual_avg_wage'}, inplace=True)

    # Headcount time series
    hc_mask = df['emp_headcount'].notnull() & (df['quarter'] > 0)
    if region != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_region'] == region)
    if sex != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_sex'] == sex)
    if age_group != 'ทั้งหมด':
        hc_mask = hc_mask & (df['clean_age'] == age_group)

    hc_sub = df[hc_mask].drop_duplicates(subset=['year', 'quarter', 'clean_region', 'clean_sex', 'clean_age'])
    hc_ts = hc_sub.groupby(['year', 'quarter'])['emp_headcount'].sum().reset_index()
    hc_ts['emp_headcount_m'] = hc_ts['emp_headcount'] / 1000.0

    merged_ts = pd.merge(ts_data, hc_ts[['year', 'quarter', 'emp_headcount_m']], on=['year', 'quarter'], how='left')

    return merged_ts, wage_data


def get_regional_comparison_data(df, filters):
    """
    Get regional comparison data for the selected year and quarter.
    """
    year = filters.get('year', 'ทั้งหมด')
    quarter = filters.get('quarter', 'ทั้งหมด')
    area = filters.get('area', 'ทั้งหมด')
    sex = filters.get('sex', 'ทั้งหมด')
    age_group = filters.get('age_group', 'ทั้งหมด')

    cur_year = int(year) if year != 'ทั้งหมด' else 2568
    cur_q = int(quarter) if (quarter != 'ทั้งหมด' and int(quarter) > 0) else None

    target_area = 'รวม' if area == 'ทั้งหมด' else area
    target_sex = 'รวม' if sex == 'ทั้งหมด' else sex
    target_age = 'รวม' if age_group == 'ทั้งหมด' else age_group

    # Select all distinct regions except 'รวม'
    regions = [r for r in df['clean_region'].unique() if r not in ['รวม', 'ไม่ระบุ']]
    if cur_year < 2568:
        # In pre-2568, filter to 5 main regions
        regions = ['กรุงเทพมหานคร', 'ภาคกลาง', 'ภาคเหนือ', 'ภาคตะวันออกเฉียงเหนือ', 'ภาคใต้']

    rows = []
    for r in regions:
        r_area = 'ในเขตเทศบาล' if (r == 'กรุงเทพมหานคร' and target_area == 'รวม') else target_area
        mask = (
            (df['clean_region'] == r) &
            (df['clean_area'] == r_area) &
            (df['clean_sex'] == target_sex) &
            (df['clean_age'] == target_age) &
            (df['year'] == cur_year)
        )
        sub = df[mask]
        if cur_q:
            sub_q = sub[sub['quarter'] == cur_q]
        else:
            sub_q = sub[sub['quarter'] > 0]
            if not sub_q.empty:
                max_q = sub_q['quarter'].max()
                sub_q = sub_q[sub_q['quarter'] == max_q]

        emp_rate = sub_q['emp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['emp_rate'].notnull().any() else None
        unemp_rate = sub_q['unemp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['unemp_rate'].notnull().any() else None

        # Wage
        if cur_year in [2567, 2568]:
            q0_sub = df[mask & (df['quarter'] == 0)]
            avg_wage = q0_sub['avg_wage'].dropna().mean() if not q0_sub.empty and q0_sub['avg_wage'].notnull().any() else None
        else:
            avg_wage = sub_q['avg_wage'].dropna().iloc[0] if not sub_q.empty and sub_q['avg_wage'].notnull().any() else None

        # Headcount for region
        hc_mask = (
            (df['clean_region'] == r) &
            (df['year'] == cur_year) &
            (df['emp_headcount'].notnull())
        )
        if cur_q:
            hc_mask = hc_mask & (df['quarter'] == cur_q)
        else:
            hc_sub = df[hc_mask]
            if not hc_sub.empty:
                hc_mask = hc_mask & (df['quarter'] == hc_sub['quarter'].max())

        if target_sex != 'รวม':
            hc_mask = hc_mask & (df['clean_sex'] == target_sex)
        if target_age != 'รวม':
            hc_mask = hc_mask & (df['clean_age'] == target_age)

        hc_dedup = df[hc_mask].drop_duplicates(subset=['year', 'quarter', 'clean_region', 'clean_sex', 'clean_age'])
        headcount_m = round(hc_dedup['emp_headcount'].sum() / 1000.0, 2) if not hc_dedup.empty else None

        rows.append({
            'region': r,
            'emp_rate': emp_rate,
            'unemp_rate': unemp_rate,
            'avg_wage': avg_wage,
            'headcount_m': headcount_m
        })

    return pd.DataFrame(rows)


def get_demographics_gender_data(df, filters):
    """
    Get gender comparison data (Male vs Female) for wages, rates, and headcount.
    """
    year = filters.get('year', 'ทั้งหมด')
    quarter = filters.get('quarter', 'ทั้งหมด')
    region = filters.get('region', 'ทั้งหมด')
    area = filters.get('area', 'ทั้งหมด')
    age_group = filters.get('age_group', 'ทั้งหมด')

    cur_year = int(year) if year != 'ทั้งหมด' else 2568
    cur_q = int(quarter) if (quarter != 'ทั้งหมด' and int(quarter) > 0) else None

    target_region = 'รวม' if region == 'ทั้งหมด' else region
    target_area = 'รวม' if area == 'ทั้งหมด' else area
    target_age = 'รวม' if age_group == 'ทั้งหมด' else age_group

    r_area = 'ในเขตเทศบาล' if (target_region == 'กรุงเทพมหานคร' and target_area == 'รวม') else target_area

    rows = []
    for s in ['ชาย', 'หญิง']:
        mask = (
            (df['clean_region'] == target_region) &
            (df['clean_area'] == r_area) &
            (df['clean_sex'] == s) &
            (df['clean_age'] == target_age) &
            (df['year'] == cur_year)
        )
        sub = df[mask]
        if cur_q:
            sub_q = sub[sub['quarter'] == cur_q]
        else:
            sub_q = sub[sub['quarter'] > 0]
            if not sub_q.empty:
                sub_q = sub_q[sub_q['quarter'] == sub_q['quarter'].max()]

        emp_rate = sub_q['emp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['emp_rate'].notnull().any() else None
        unemp_rate = sub_q['unemp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['unemp_rate'].notnull().any() else None

        if cur_year in [2567, 2568]:
            q0_sub = df[mask & (df['quarter'] == 0)]
            avg_wage = q0_sub['avg_wage'].dropna().mean() if not q0_sub.empty and q0_sub['avg_wage'].notnull().any() else None
        else:
            avg_wage = sub_q['avg_wage'].dropna().iloc[0] if not sub_q.empty and sub_q['avg_wage'].notnull().any() else None

        rows.append({
            'sex': s,
            'avg_wage': avg_wage,
            'emp_rate': emp_rate,
            'unemp_rate': unemp_rate
        })

    return pd.DataFrame(rows)


def get_demographics_age_data(df, filters):
    """
    Get age group breakdown data (15-19 to 60+).
    """
    year = filters.get('year', 'ทั้งหมด')
    quarter = filters.get('quarter', 'ทั้งหมด')
    region = filters.get('region', 'ทั้งหมด')
    area = filters.get('area', 'ทั้งหมด')
    sex = filters.get('sex', 'ทั้งหมด')

    cur_year = int(year) if year != 'ทั้งหมด' else 2568
    cur_q = int(quarter) if (quarter != 'ทั้งหมด' and int(quarter) > 0) else None

    target_region = 'รวม' if region == 'ทั้งหมด' else region
    target_area = 'รวม' if area == 'ทั้งหมด' else area
    target_sex = 'รวม' if sex == 'ทั้งหมด' else sex

    r_area = 'ในเขตเทศบาล' if (target_region == 'กรุงเทพมหานคร' and target_area == 'รวม') else target_area

    age_brackets = [
        '15-19 ปี', '20-24 ปี', '25-29 ปี', '30-34 ปี',
        '35-39 ปี', '40-49 ปี', '50-59 ปี', '60 ปีขึ้นไป'
    ]

    rows = []
    for ag in age_brackets:
        mask = (
            (df['clean_region'] == target_region) &
            (df['clean_area'] == r_area) &
            (df['clean_sex'] == target_sex) &
            (df['clean_age'] == ag) &
            (df['year'] == cur_year)
        )
        sub = df[mask]
        if cur_q:
            sub_q = sub[sub['quarter'] == cur_q]
        else:
            sub_q = sub[sub['quarter'] > 0]
            if not sub_q.empty:
                sub_q = sub_q[sub_q['quarter'] == sub_q['quarter'].max()]

        emp_rate = sub_q['emp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['emp_rate'].notnull().any() else None
        unemp_rate = sub_q['unemp_rate'].dropna().iloc[0] if not sub_q.empty and sub_q['unemp_rate'].notnull().any() else None

        if cur_year in [2567, 2568]:
            q0_sub = df[mask & (df['quarter'] == 0)]
            avg_wage = q0_sub['avg_wage'].dropna().mean() if not q0_sub.empty and q0_sub['avg_wage'].notnull().any() else None
        else:
            avg_wage = sub_q['avg_wage'].dropna().iloc[0] if not sub_q.empty and sub_q['avg_wage'].notnull().any() else None

        rows.append({
            'age_group': ag,
            'avg_wage': avg_wage,
            'emp_rate': emp_rate,
            'unemp_rate': unemp_rate
        })

    return pd.DataFrame(rows)


def get_area_wage_comparison_data(df, filters):
    """
    Get municipal vs non-municipal wage comparisons across regions.
    """
    year = filters.get('year', 'ทั้งหมด')
    cur_year = int(year) if year != 'ทั้งหมด' else 2568

    regions = ['ภาคกลาง', 'ภาคเหนือ', 'ภาคตะวันออกเฉียงเหนือ', 'ภาคใต้']
    if cur_year >= 2568:
        regions += ['ภาคตะวันออก', 'ภาคใต้ชายแดน']

    rows = []
    for r in regions:
        # In municipal
        m_in = (
            (df['clean_region'] == r) &
            (df['clean_area'] == 'ในเขตเทศบาล') &
            (df['clean_sex'] == 'รวม') &
            (df['clean_age'] == 'รวม') &
            (df['year'] == cur_year)
        )
        # Out municipal
        m_out = (
            (df['clean_region'] == r) &
            (df['clean_area'] == 'นอกเขตเทศบาล') &
            (df['clean_sex'] == 'รวม') &
            (df['clean_age'] == 'รวม') &
            (df['year'] == cur_year)
        )

        wage_in = None
        wage_out = None

        if cur_year in [2567, 2568]:
            sub_in = df[m_in & (df['quarter'] == 0)]
            sub_out = df[m_out & (df['quarter'] == 0)]
            if not sub_in.empty:
                wage_in = sub_in['avg_wage'].dropna().mean()
            if not sub_out.empty:
                wage_out = sub_out['avg_wage'].dropna().mean()
        else:
            sub_in = df[m_in & (df['quarter'] > 0)]
            sub_out = df[m_out & (df['quarter'] > 0)]
            if not sub_in.empty:
                wage_in = sub_in['avg_wage'].dropna().iloc[-1]
            if not sub_out.empty:
                wage_out = sub_out['avg_wage'].dropna().iloc[-1]

        rows.append({
            'region': r,
            'wage_in': wage_in,
            'wage_out': wage_out,
            'wage_gap': (wage_in - wage_out) if (wage_in and wage_out) else None
        })

    return pd.DataFrame(rows)
