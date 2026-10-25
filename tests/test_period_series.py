"""
Cross-check wage / headcount period series against the RAW CSV
(independent calculation: raw labels, no use of the clean_* columns).
Run:  python -m unittest tests.test_period_series
"""
import os
import re
import unittest

import pandas as pd

from src.data_loader import load_labor_data
from src.metrics import (
    get_wage_period_series,
    get_headcount_period_series,
)

ALL = "ทั้งหมด"
RAW = os.path.join("data", "raw", "final_labor_master_data.csv")


def _strip(series):
    return series.astype(str).str.replace(r"^\d+[\.\)]\s*", "", regex=True).str.strip()


class TestPeriodSeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_labor_data()
        cls.df = cls.df[cls.df["year"].between(2561, 2568)]
        raw = pd.read_csv(RAW)
        for col in ("region", "area", "sex", "age_group"):
            raw[col] = _strip(raw[col].fillna("ไม่ระบุ"))
        cls.raw = raw[raw["year"].between(2561, 2568)]
        cls.f = dict(year=2564, quarter=ALL, region=ALL,
                     area=ALL, sex=ALL, age_group=ALL)

    def test_scope_2561_2568_only(self):
        s = get_wage_period_series(self.df, self.f)
        self.assertEqual(s["year"].tolist(), list(range(2561, 2569)))
        h = get_headcount_period_series(self.df, self.f)
        self.assertEqual(h["year"].tolist(), list(range(2561, 2569)))

    def test_quarterly_wage_matches_raw(self):
        f = dict(self.f, region="ภาคเหนือ", sex="หญิง")
        s = get_wage_period_series(self.df, f, 2564)
        r = self.raw
        for q in (1, 2, 3, 4):
            v = r[(r.year == 2564) & (r.quarter == q) & (r.region == "ภาคเหนือ")
                  & (r.area == "รวม") & (r.sex == "หญิง") & (r.age_group == "รวม")]["avg_wage"].dropna()
            self.assertEqual(len(v), 1)
            got = s.loc[s["quarter"] == q, "avg_wage"].iloc[0]
            self.assertAlmostEqual(got, round(float(v.iloc[0]), 2), places=2)

    def test_2567_has_no_fake_quarters(self):
        s = get_wage_period_series(self.df, self.f, 2567)
        self.assertEqual(len(s), 1)
        self.assertEqual(int(s["quarter"].iloc[0]), 0)
        self.assertEqual(s["kind"].iloc[0], "unlabeled")

    def test_headcount_matches_raw_thousands(self):
        r = self.raw
        sub = r[(r.year == 2566) & (r.quarter == 4) & r.emp_headcount.notna()
                & (r.region != "รวม") & (r.sex != "รวม") & (r.age_group != "รวม")]
        sub = sub.drop_duplicates(["region", "sex", "age_group"])
        expected = sub["emp_headcount"].sum() / 1000
        h = get_headcount_period_series(self.df, self.f)
        got = h.loc[h["year"] == 2566, "headcount_m"].iloc[0]
        self.assertAlmostEqual(got, round(expected, 2), places=2)

    def test_missing_region_year_returns_none_not_other_year(self):
        f = dict(self.f, region="ภาคตะวันออก")      # exists only from 2568
        s = get_wage_period_series(self.df, f)
        self.assertTrue(s.loc[s["year"] < 2568, "avg_wage"].isna().all())


if __name__ == "__main__":
    unittest.main()