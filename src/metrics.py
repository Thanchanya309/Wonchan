
"""
Statistical Calculation and Metric Engine
Thailand Labor Market Analytics Dashboard

- Uses the project's existing NSO labor dataset.
- Keeps official rate rows instead of summing percentages.
- Supports year-dependent regional classifications.
- Returns period_label for app.py.
- Applies sex and age filters to municipal wage comparisons.
"""

import numpy as np
import pandas as pd


ALL = "ทั้งหมด"
TOTAL = "รวม"

METRIC_COLUMNS = [
    "avg_wage",
    "emp_rate",
    "unemp_rate",
    "emp_headcount",
]

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

AGE_GROUPS = [
    "15-19 ปี",
    "20-24 ปี",
    "25-29 ปี",
    "30-34 ปี",
    "35-39 ปี",
    "40-49 ปี",
    "50-59 ปี",
    "60 ปีขึ้นไป",
]


def _year(df, filters):
    """Get selected year, falling back to the latest available year."""
    years = pd.to_numeric(df["year"], errors="coerce").dropna()

    if years.empty:
        return None

    requested = filters.get("year", ALL)

    if requested != ALL:
        try:
            return int(requested)
        except (TypeError, ValueError):
            pass

    return int(years.max())


def _quarter(filters):
    """Return a selected quarter, or None for the default period."""
    value = filters.get("quarter", ALL)

    if value == ALL or value is None:
        return None

    try:
        quarter = int(value)
        return quarter if 1 <= quarter <= 4 else None
    except (TypeError, ValueError):
        return None


def _target(filters, dimension):
    """Map an unselected dimension to its official total row."""
    value = filters.get(dimension, ALL)
    return TOTAL if value == ALL else value


def _regions_for_year(df, year):
    """
    Use only region names actually present in the selected year.
    The expected classification is 5 regions before 2568,
    and 7 regions from 2568 onward.
    """
    if year is None:
        return []

    frame = df[df["year"] == year]

    if frame.empty:
        return []

    found = set(
        frame["clean_region"]
        .dropna()
        .astype(str)
        .unique()
    )

    ordered = REGIONS_7 if year >= 2568 else REGIONS_5

    return [region for region in ordered if region in found]


def _area_for_region(region, area):
    """Bangkok has a municipal-only reporting convention."""
    if region == "กรุงเทพมหานคร" and area == TOTAL:
        return "ในเขตเทศบาล"
    return area


def _base_mask(df, year, region, area, sex, age):
    """Exact slice for official wage and rate observations."""
    if year is None:
        return pd.Series(False, index=df.index)

    selected_area = _area_for_region(region, area)

    return (
        (df["year"] == year)
        & (df["clean_region"] == region)
        & (df["clean_area"] == selected_area)
        & (df["clean_sex"] == sex)
        & (df["clean_age"] == age)
    )


def _numeric_values(frame, column):
    """Extract finite numeric observations."""
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=float)

    values = pd.to_numeric(frame[column], errors="coerce")
    return values.replace([np.inf, -np.inf], np.nan).dropna()


def _rate_value(frame, column, quarter=None):
    """
    Read a reported rate from a single quarter.
    Never sum or average quarterly percentage rates.
    """
    if frame.empty:
        return None, None

    available = frame[
        (frame["quarter"] > 0)
        & frame[column].notna()
    ]

    if quarter is not None:
        available = available[available["quarter"] == quarter]
    elif not available.empty:
        available = available[
            available["quarter"] == available["quarter"].max()
        ]

    values = _numeric_values(available, column)

    if values.empty:
        return None, None

    # Do not choose an arbitrary value when a supposedly
    # identical statistical slice contains conflicting rates.
    if values.nunique() > 1:
        return None, None

    used_quarter = int(available["quarter"].iloc[0])
    return float(values.iloc[0]), used_quarter


def _wage_value(frame, year, quarter=None):
    """
    Preserve the previous project convention:
    Q0 wage observations in 2567-2568 are annual.
    Multiple reported values are averaged with an explicit caveat.
    """
    if frame.empty or year is None:
        return None, ""

    if year in (2567, 2568):
        annual = frame[frame["quarter"] == 0]
        values = _numeric_values(annual, "avg_wage")

        if values.empty:
            return None, ""

        wage = float(values.mean())

        if quarter is not None:
            caveat = (
                f"ค่าจ้างปี {year} มีเฉพาะข้อมูลรายปี "
                "(quarter = 0) จึงไม่ใช่ค่าจ้างของไตรมาสที่เลือก"
            )
        else:
            caveat = ""

        if values.nunique() > 1:
            caveat += (
                " ค่าจ้างในชุดข้อมูลมีหลายค่าต่อกลุ่มเดียวกัน "
                "ระบบใช้ค่าเฉลี่ยตามแนวทางเดิมของโครงการ "
                "ซึ่งควรตรวจสอบความหมายของรายการต้นทางก่อนตีความ"
            )

        return wage, caveat.strip()

    if quarter is not None:
        selected = frame[frame["quarter"] == quarter]
    else:
        selected = frame[
            (frame["quarter"] > 0)
            & frame["avg_wage"].notna()
        ]

        if not selected.empty:
            selected = selected[
                selected["quarter"] == selected["quarter"].max()
            ]

    values = _numeric_values(selected, "avg_wage")

    if values.empty:
        return None, ""

    if values.nunique() > 1:
        return None, (
            "พบค่าจ้างหลายค่าที่ขัดแย้งกันในช่วงเวลา "
            "และกลุ่มข้อมูลเดียวกัน จึงไม่เลือกค่าหนึ่งโดยพลการ"
        )

    return float(values.iloc[0]), ""


def _headcount_value(df, year, quarter, region, sex, age):
    """
    Sum non-overlapping headcount cells only.

    Headcount is reported in thousands of persons.
    Area is intentionally excluded because the source does not
    support a reliable municipal/non-municipal headcount split.
    """
    if year is None:
        return None

    frame = df[
        (df["year"] == year)
        & (df["emp_headcount"].notna())
        & (df["quarter"] > 0)
    ].copy()

    if quarter is not None:
        frame = frame[frame["quarter"] == quarter]
    elif not frame.empty:
        frame = frame[
            frame["quarter"] == frame["quarter"].max()
        ]

    if frame.empty:
        return None

    if region != ALL:
        frame = frame[frame["clean_region"] == region]
    else:
        regions = _regions_for_year(df, year)
        frame = frame[frame["clean_region"].isin(regions)]

    if sex != ALL:
        frame = frame[frame["clean_sex"] == sex]
    else:
        frame = frame[frame["clean_sex"].isin(["ชาย", "หญิง"])]

    if age != ALL:
        frame = frame[frame["clean_age"] == age]
    else:
        frame = frame[frame["clean_age"].isin(AGE_GROUPS)]

    if frame.empty:
        return None

    keys = [
        "year",
        "quarter",
        "clean_region",
        "clean_sex",
        "clean_age",
    ]

    # Conflicting repeated cells cannot safely be counted.
    conflicts = frame.groupby(keys, dropna=False)["emp_headcount"].nunique()
    if (conflicts > 1).any():
        return None

    frame = frame.drop_duplicates(subset=keys)

    values = _numeric_values(frame, "emp_headcount")
    if values.empty:
        return None

    return float(values.sum())


def _period_label(year, quarter, rate_quarters=None):
    """Human-readable label for the dashboard."""
    if year is None:
        return "ไม่มีข้อมูลช่วงเวลา"

    if quarter is not None:
        return f"ปี พ.ศ. {year} · ไตรมาส {quarter}"

    if rate_quarters:
        available = [q for q in rate_quarters if q is not None]
        if available:
            return f"ปี พ.ศ. {year} · ข้อมูลอัตราล่าสุดไตรมาส {max(available)}"

    return f"ปี พ.ศ. {year} · ช่วงเวลาล่าสุดที่มีข้อมูล"


def _round(value, digits=2):
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), digits)


def get_kpis(df, filters):
    """
    Return:
      avg_wage, emp_rate, unemp_rate,
      emp_headcount_k, emp_headcount_m,
      wage_caveat, headcount_caveat, period_label.
    """
    year = _year(df, filters)
    quarter = _quarter(filters)

    region = _target(filters, "region")
    area = _target(filters, "area")
    sex = _target(filters, "sex")
    age = _target(filters, "age_group")

    mask = _base_mask(
        df, year, region, area, sex, age
    )
    frame = df[mask]

    emp_rate, emp_q = _rate_value(
        frame, "emp_rate", quarter
    )
    unemp_rate, unemp_q = _rate_value(
        frame, "unemp_rate", quarter
    )
    wage, wage_caveat = _wage_value(
        frame, year, quarter
    )

    hc_region = filters.get("region", ALL)
    hc_sex = filters.get("sex", ALL)
    hc_age = filters.get("age_group", ALL)

    headcount_k = _headcount_value(
        df, year, quarter,
        hc_region, hc_sex, hc_age
    )

    headcount_caveat = ""
    if filters.get("area", ALL) != ALL and headcount_k is not None:
        headcount_caveat = (
            "จำนวนผู้มีงานทำไม่มีข้อมูลจำแนกเขตเทศบาล"
            "ในชุดข้อมูลนี้ จึงแสดงยอดรวมพื้นที่แทน"
        )

    return {
        "avg_wage": _round(wage),
        "emp_rate": _round(emp_rate),
        "unemp_rate": _round(unemp_rate),
        "emp_headcount_k": _round(headcount_k, 1),
        "emp_headcount_m": (
            _round(headcount_k / 1000)
            if headcount_k is not None else None
        ),
        "wage_caveat": wage_caveat,
        "headcount_caveat": headcount_caveat,
        "period_label": _period_label(
            year, quarter, [emp_q, unemp_q]
        ),
    }


def get_time_series_data(df, filters):
    """
    Historical time series for the selected demographic group.
    Year is intentionally not restricted so charts can show trends.
    Region names are not silently harmonized across definitions.
    """
    region = _target(filters, "region")
    area = _target(filters, "area")
    sex = _target(filters, "sex")
    age = _target(filters, "age_group")

    area = _area_for_region(region, area)

    base = df[
        (df["clean_region"] == region)
        & (df["clean_area"] == area)
        & (df["clean_sex"] == sex)
        & (df["clean_age"] == age)
    ].copy()

    results = []

    for (year, quarter), group in base[
        base["quarter"] > 0
    ].groupby(["year", "quarter"], sort=True):

        emp, _ = _rate_value(group, "emp_rate", int(quarter))
        unemp, _ = _rate_value(group, "unemp_rate", int(quarter))

        hc_k = _headcount_value(
            df, int(year), int(quarter),
            filters.get("region", ALL),
            filters.get("sex", ALL),
            filters.get("age_group", ALL),
        )

        results.append({
            "year": int(year),
            "quarter": int(quarter),
            "time_label": f"พ.ศ. {int(year)} Q{int(quarter)}",
            "emp_rate": emp,
            "unemp_rate": unemp,
            "avg_wage": None,
            "emp_headcount_m": (
                hc_k / 1000 if hc_k is not None else None
            ),
        })

    time_columns = [
        "year", "quarter", "time_label",
        "emp_rate", "unemp_rate",
        "avg_wage", "emp_headcount_m",
    ]
    ts_data = pd.DataFrame(results, columns=time_columns)

    wage_rows = []
    if not base.empty:
        for year, group in base.groupby("year", sort=True):
            wage, _ = _wage_value(group, int(year), None)
            if wage is not None:
                wage_rows.append({
                    "year": int(year),
                    "annual_avg_wage": wage,
                })

    wage_data = pd.DataFrame(
        wage_rows, columns=["year", "annual_avg_wage"]
    )

    return ts_data, wage_data


def get_regional_comparison_data(df, filters):
    """
    Regional metrics for all actual regions in the selected year.
    The currently selected region is not used to remove other
    regions, allowing map colors and rankings to remain comparable.
    """
    year = _year(df, filters)
    quarter = _quarter(filters)
    area = _target(filters, "area")
    sex = _target(filters, "sex")
    age = _target(filters, "age_group")

    rows = []

    for region in _regions_for_year(df, year):
        mask = _base_mask(
            df, year, region, area, sex, age
        )
        frame = df[mask]

        emp, _ = _rate_value(
            frame, "emp_rate", quarter
        )
        unemp, _ = _rate_value(
            frame, "unemp_rate", quarter
        )
        wage, _ = _wage_value(
            frame, year, quarter
        )

        headcount_k = _headcount_value(
            df, year, quarter,
            region,
            filters.get("sex", ALL),
            filters.get("age_group", ALL),
        )

        rows.append({
            "region": region,
            "emp_rate": _round(emp),
            "unemp_rate": _round(unemp),
            "avg_wage": _round(wage),
            "headcount_m": (
                _round(headcount_k / 1000)
                if headcount_k is not None else None
            ),
        })

    return pd.DataFrame(
        rows,
        columns=[
            "region", "emp_rate", "unemp_rate",
            "avg_wage", "headcount_m",
        ],
    )


def get_demographics_gender_data(df, filters):
    """Gender comparison using the same selected year and region."""
    year = _year(df, filters)
    quarter = _quarter(filters)
    region = _target(filters, "region")
    area = _target(filters, "area")
    age = _target(filters, "age_group")

    selected_sex = filters.get("sex", ALL)
    sexes = (
        ["ชาย", "หญิง"]
        if selected_sex == ALL
        else [selected_sex]
    )

    rows = []
    for sex in sexes:
        frame = df[_base_mask(
            df, year, region, area, sex, age
        )]

        emp, _ = _rate_value(
            frame, "emp_rate", quarter
        )
        unemp, _ = _rate_value(
            frame, "unemp_rate", quarter
        )
        wage, _ = _wage_value(
            frame, year, quarter
        )

        rows.append({
            "sex": sex,
            "avg_wage": _round(wage),
            "emp_rate": _round(emp),
            "unemp_rate": _round(unemp),
        })

    return pd.DataFrame(
        rows,
        columns=["sex", "avg_wage", "emp_rate", "unemp_rate"],
    )


def get_demographics_age_data(df, filters):
    """Age comparison using the selected year, region and sex."""
    year = _year(df, filters)
    quarter = _quarter(filters)
    region = _target(filters, "region")
    area = _target(filters, "area")
    sex = _target(filters, "sex")

    selected_age = filters.get("age_group", ALL)
    ages = (
        AGE_GROUPS
        if selected_age == ALL
        else [selected_age]
    )

    rows = []
    for age in ages:
        frame = df[_base_mask(
            df, year, region, area, sex, age
        )]

        emp, _ = _rate_value(
            frame, "emp_rate", quarter
        )
        unemp, _ = _rate_value(
            frame, "unemp_rate", quarter
        )
        wage, _ = _wage_value(
            frame, year, quarter
        )

        rows.append({
            "age_group": age,
            "avg_wage": _round(wage),
            "emp_rate": _round(emp),
            "unemp_rate": _round(unemp),
        })

    return pd.DataFrame(
        rows,
        columns=[
            "age_group", "avg_wage",
            "emp_rate", "unemp_rate",
        ],
    )


def get_area_wage_comparison_data(df, filters):
    """
    Municipal vs non-municipal wages.

    Honors year, quarter, sex and age group.
    Region selection is intentionally retained as a highlight
    in the presentation layer, rather than removing every other
    region from the comparison.
    """
    year = _year(df, filters)
    quarter = _quarter(filters)
    sex = _target(filters, "sex")
    age = _target(filters, "age_group")

    rows = []

    for region in _regions_for_year(df, year):
        # Bangkok has no separate non-municipal observations
        # in this dataset's reporting convention.
        if region == "กรุงเทพมหานคร":
            continue

        municipal = df[_base_mask(
            df, year, region,
            "ในเขตเทศบาล", sex, age
        )]
        non_municipal = df[_base_mask(
            df, year, region,
            "นอกเขตเทศบาล", sex, age
        )]

        wage_in, _ = _wage_value(
            municipal, year, quarter
        )
        wage_out, _ = _wage_value(
            non_municipal, year, quarter
        )

        gap = None
        if wage_in is not None and wage_out is not None:
            gap = wage_in - wage_out

        rows.append({
            "region": region,
            "wage_in": _round(wage_in),
            "wage_out": _round(wage_out),
            "wage_gap": _round(gap),
        })

    return pd.DataFrame(
        rows,
        columns=["region", "wage_in", "wage_out", "wage_gap"],
    )
