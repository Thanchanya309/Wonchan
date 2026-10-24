"""
Unit tests for data loader and normalization
"""
import unittest
import pandas as pd
from src.data_loader import load_labor_data, normalize_sex, normalize_age_group, normalize_area, normalize_region


class TestDataLoader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = load_labor_data()

    def test_dataset_loaded(self):
        self.assertFalse(self.df.empty)
        self.assertEqual(len(self.df), 29530)
        self.assertIn('clean_sex', self.df.columns)
        self.assertIn('clean_age', self.df.columns)
        self.assertIn('clean_area', self.df.columns)
        self.assertIn('clean_region', self.df.columns)

    def test_normalize_sex(self):
        self.assertEqual(normalize_sex('1. ชาย'), 'ชาย')
        self.assertEqual(normalize_sex('2. หญิง'), 'หญิง')
        self.assertEqual(normalize_sex('รวม'), 'รวม')

    def test_normalize_age(self):
        self.assertEqual(normalize_age_group('1. 15-19 ปี'), '15-19 ปี')
        self.assertEqual(normalize_age_group('60 ขึ้นไป'), '60 ปีขึ้นไป')
        self.assertEqual(normalize_age_group('Total'), 'รวม')

    def test_normalize_area(self):
        self.assertEqual(normalize_area('1) ในเขตเทศบาล'), 'ในเขตเทศบาล')
        self.assertEqual(normalize_area('1) เขตเทศบาล'), 'ในเขตเทศบาล')
        self.assertEqual(normalize_area('2) นอกเขตเทศบาล'), 'นอกเขตเทศบาล')

    def test_normalize_region(self):
        self.assertEqual(normalize_region('1) กรุงเทพมหานคร'), 'กรุงเทพมหานคร')
        self.assertEqual(normalize_region('2) ภาคกลาง'), 'ภาคกลาง')
        self.assertEqual(normalize_region('Total'), 'รวม')


if __name__ == '__main__':
    unittest.main()
