"""
Unit tests for filter state and cross-filtering event logic
"""
import unittest
from unittest.mock import MagicMock
from src.filters import (
    DEFAULT_FILTERS,
    init_filter_state,
    get_current_filters,
    set_filter,
    reset_all_filters,
    clear_filter,
    handle_chart_selection
)


class TestFilters(unittest.TestCase):
    def setUp(self):
        # Provide a mock for st.session_state
        import streamlit as st
        if not hasattr(st, 'session_state') or not isinstance(st.session_state, dict):
            # If running in unit test without streamlit session
            pass

    def test_default_filters_structure(self):
        self.assertIn('year', DEFAULT_FILTERS)
        self.assertIn('quarter', DEFAULT_FILTERS)
        self.assertIn('region', DEFAULT_FILTERS)
        self.assertIn('area', DEFAULT_FILTERS)
        self.assertIn('sex', DEFAULT_FILTERS)
        self.assertIn('age_group', DEFAULT_FILTERS)
        self.assertEqual(DEFAULT_FILTERS['year'], 2568)


if __name__ == '__main__':
    unittest.main()
