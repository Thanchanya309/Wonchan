"""
Global Filter State and Cross-Filtering Management for Thailand Labor Market Dashboard
"""
import streamlit as st


DEFAULT_FILTERS = {
    'year': 2568,
    'quarter': 'ทั้งหมด',
    'region': 'ทั้งหมด',
    'area': 'ทั้งหมด',
    'sex': 'ทั้งหมด',
    'age_group': 'ทั้งหมด'
}


def init_filter_state():
    """Initialize filters in st.session_state if not already present."""
    if 'filters' not in st.session_state:
        st.session_state.filters = DEFAULT_FILTERS.copy()
    if 'last_clicked_event' not in st.session_state:
        st.session_state.last_clicked_event = None


def get_current_filters():
    """Retrieve current active filters dictionary."""
    init_filter_state()
    return st.session_state.filters


def set_filter(dimension, value):
    """Update a single filter in session state."""
    init_filter_state()
    st.session_state.filters[dimension] = value


def reset_all_filters():
    """Reset all filters back to default values."""
    st.session_state.filters = DEFAULT_FILTERS.copy()
    st.session_state.last_clicked_event = None


def clear_filter(dimension):
    """Reset a single filter to default 'ทั้งหมด'."""
    init_filter_state()
    if dimension == 'year':
        st.session_state.filters['year'] = DEFAULT_FILTERS['year']
    else:
        st.session_state.filters[dimension] = 'ทั้งหมด'


def handle_chart_selection(event, dimension, value_key='x'):
    """
    Safely process Plotly selection events from st.plotly_chart(..., on_select="rerun").
    Updates the corresponding filter dimension without causing infinite rerun loops.
    """
    if not event or 'selection' not in event:
        return False

    points = event.get('selection', {}).get('points', [])
    if not points:
        return False

    first_pt = points[0]
    clicked_val = None

    # Handle customdata, x, y, or point_index
    if 'customdata' in first_pt and first_pt['customdata'] is not None:
        cd = first_pt['customdata']
        clicked_val = cd[0] if isinstance(cd, (list, tuple)) else cd
    elif value_key in first_pt:
        clicked_val = first_pt[value_key]

    if clicked_val is not None:
        # Avoid redundant rerun loop if already set to that value
        curr_val = st.session_state.filters.get(dimension)
        if str(curr_val) != str(clicked_val):
            st.session_state.filters[dimension] = clicked_val
            return True

    return False
