"""
Unit tests for statistical calculations and metric extraction
"""
import unittest
import pandas as pd
from src.data_loader import load_labor_data
from src.metrics import (
    get_kpis,
    get_time_series_data,
    get_regional_comparison_data,
    get_demographics_gender_data,
    get_demographics_age_data
)
from src.filters import DEFAULT_FILTERS


class TestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_labor_data()

    def test_national_kpis_2568(self):
        filters = DEFAULT_FILTERS.copy()
        kpis = get_kpis(self.df, filters)

        # Average wage should be positive and in reasonable range (~15,000 - 25,000 THB)
        self.assertIsNotNone(kpis['avg_wage'])
        self.assertGreater(kpis['avg_wage'], 12000)
        self.assertLess(kpis['avg_wage'], 30000)

        # Employment rate should be ~60-75%
        self.assertIsNotNone(kpis['emp_rate'])
        self.assertGreater(kpis['emp_rate'], 50.0)
        self.assertLess(kpis['emp_rate'], 90.0)

        # Unemployment rate should be ~0.5 - 3.0%
        self.assertIsNotNone(kpis['unemp_rate'])
        self.assertGreater(kpis['unemp_rate'], 0.1)
        self.assertLess(kpis['unemp_rate'], 5.0)

        # Headcount for Thailand should be ~37 - 42 million
        self.assertIsNotNone(kpis['emp_headcount_m'])
        self.assertGreater(kpis['emp_headcount_m'], 35.0)
        self.assertLess(kpis['emp_headcount_m'], 45.0)

    def test_regional_comparison(self):
        filters = DEFAULT_FILTERS.copy()
        reg_df = get_regional_comparison_data(self.df, filters)
        self.assertFalse(reg_df.empty)
        # 2568 has 7 regions
        self.assertIn('กรุงเทพมหานคร', reg_df['region'].values)
        self.assertIn('ภาคเหนือ', reg_df['region'].values)

    def test_gender_comparison(self):
        filters = DEFAULT_FILTERS.copy()
        gender_df = get_demographics_gender_data(self.df, filters)
        self.assertEqual(len(gender_df), 2)
        self.assertIn('ชาย', gender_df['sex'].values)
        self.assertIn('หญิง', gender_df['sex'].values)

    def test_age_comparison(self):
        filters = DEFAULT_FILTERS.copy()
        age_df = get_demographics_age_data(self.df, filters)
        self.assertEqual(len(age_df), 8)


if __name__ == '__main__':
    unittest.main()
