"""
UI Styling and Custom CSS for Modern Admin Dashboard Bento Grid
Theme: Soft Pastel Canvas, Pink-Purple Highlights, Kanit Font
"""

def get_custom_css():
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

    /* Global Typography */
    html, body, [class*="css"], .stMarkdown, .stText, .stButton, .stSelectbox, .stRadio {
        font-family: 'Kanit', sans-serif !important;
    }

    /* Main background canvas */
    .stApp {
        background-color: #F8F4EC;
        color: #43334C;
    }

    /* Hide standard Streamlit header clutter */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #EFE3EC;
        box-shadow: 2px 0 16px rgba(67, 51, 76, 0.04);
    }
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #43334C !important;
        font-weight: 600;
    }

    /* Sidebar brand card */
    .sidebar-brand-card {
        background: linear-gradient(135deg, #E83C91 0%, #843A7D 100%);
        border-radius: 16px;
        padding: 18px 20px;
        color: #FFFFFF;
        margin-bottom: 24px;
        box-shadow: 0 8px 20px rgba(232, 60, 145, 0.25);
    }
    .sidebar-brand-card h2 {
        color: #FFFFFF !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
        letter-spacing: -0.02em;
    }
    .sidebar-brand-card p {
        color: rgba(255, 255, 255, 0.85);
        font-size: 0.85rem;
        margin: 4px 0 0 0;
    }

    /* Main Area Header */
    .main-header-banner {
        background: #FFFFFF;
        border: 1px solid #EFE3EC;
        border-radius: 20px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 24px rgba(67, 51, 76, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
    }
    .main-header-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #43334C;
        margin: 0;
        line-height: 1.2;
    }
    .main-header-subtitle {
        font-size: 0.95rem;
        color: #7A6882;
        margin: 6px 0 0 0;
    }

    /* Active filter badges container */
    .active-filters-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
        align-items: center;
    }
    .filter-pill {
        display: inline-flex;
        align-items: center;
        background: #FBEAF3;
        color: #843A7D;
        border: 1px solid #E83C91;
        padding: 4px 12px;
        border-radius: 30px;
        font-size: 0.85rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .filter-pill-label {
        color: #7A6882;
        margin-right: 4px;
    }
    .filter-pill-val {
        font-weight: 600;
        color: #E83C91;
    }

    /* KPI Bento Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 18px;
        margin-bottom: 28px;
    }
    .kpi-card {
        border-radius: 20px;
        padding: 22px 24px;
        color: #FFFFFF;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 8px 24px rgba(67, 51, 76, 0.08);
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(67, 51, 76, 0.12);
    }
    .kpi-card-1 {
        background: linear-gradient(135deg, #E83C91 0%, #C82A78 100%);
    }
    .kpi-card-2 {
        background: linear-gradient(135deg, #843A7D 0%, #5E2659 100%);
    }
    .kpi-card-3 {
        background: linear-gradient(135deg, #57C7FF 0%, #30A4DF 100%);
    }
    .kpi-card-4 {
        background: linear-gradient(135deg, #F7A531 0%, #E08512 100%);
    }
    .kpi-title {
        font-size: 0.9rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .kpi-value {
        font-size: 2.1rem;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 6px;
    }
    .kpi-unit {
        font-size: 0.9rem;
        font-weight: 400;
        margin-left: 4px;
        opacity: 0.85;
    }
    .kpi-subtext {
        font-size: 0.8rem;
        opacity: 0.85;
        margin-top: 4px;
    }

    /* Content Bento Cards */
    .bento-card {
        background: #FFFFFF;
        border: 1px solid #EFE3EC;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(67, 51, 76, 0.04);
        transition: box-shadow 0.2s ease;
    }
    .bento-card:hover {
        box-shadow: 0 8px 28px rgba(67, 51, 76, 0.07);
    }
    .bento-card-title {
        font-size: 1.15rem;
        font-weight: 600;
        color: #43334C;
        margin: 0 0 4px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .bento-card-subtitle {
        font-size: 0.85rem;
        color: #7A6882;
        margin-bottom: 16px;
    }

    /* Alert / Caveat Box */
    .caveat-banner {
        background: #FBEAF3;
        border-left: 4px solid #E83C91;
        border-radius: 12px;
        padding: 14px 18px;
        margin: 14px 0 20px 0;
        font-size: 0.88rem;
        color: #6E2D57;
        line-height: 1.5;
    }
    .caveat-title {
        font-weight: 600;
        margin-bottom: 4px;
        color: #843A7D;
    }

    /* Tab bar styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: transparent;
        padding-bottom: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #FFFFFF !important;
        border: 1px solid #EFE3EC !important;
        border-radius: 14px !important;
        padding: 10px 22px !important;
        color: #43334C !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }
    .stTabs [aria-selected="true"] {
        background: #843A7D !important;
        color: #FFFFFF !important;
        border-color: #843A7D !important;
        box-shadow: 0 4px 14px rgba(132, 58, 125, 0.25) !important;
    }

    /* Primary and Reset Buttons */
    .stButton > button {
        border-radius: 12px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    button[kind="primary"] {
        background: linear-gradient(135deg, #E83C91 0%, #843A7D 100%) !important;
        border: none !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(232, 60, 145, 0.3) !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(232, 60, 145, 0.4) !important;
    }

    /* Plotly Chart Container Customizer */
    .stPlotlyChart {
        border-radius: 14px;
        overflow: hidden;
    }
    </style>
    """
