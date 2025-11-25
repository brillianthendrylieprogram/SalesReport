import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import os

# --- 1. CONFIG & SESSION STATE ---
st.set_page_config(
    page_title="Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi State Dark Mode
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False

# --- 2. DEFINISI WARNA (PALET DINAMIS) ---
if st.session_state['dark_mode']:
    # --- DARK MODE ---
    THEME = {
        "bg": "#0f172a",          # Background Gelap (Deep Navy)
        "card": "#1e293b",        # Kartu Sedikit Lebih Terang
        "text_main": "#f8fafc",   # Putih Terang
        "text_sub": "#94a3b8",    # Abu Terang
        "sidebar": "#020617",     # Sidebar Sangat Gelap
        "border": "#334155",      # Border Abu Gelap
        "chart_bg": "#1e293b",
        "plotly_theme": "plotly_dark"
    }
else:
    # --- LIGHT MODE ---
    THEME = {
        "bg": "#f3f4f6",          # Abu Sangat Muda
        "card": "#ffffff",        # Putih
        "text_main": "#111827",   # Hitam Pekat
        "text_sub": "#6b7280",    # Abu Gelap
        "sidebar": "#1f2937",     # Sidebar Abu Tua
        "border": "#e5e7eb",      # Border Abu Muda
        "chart_bg": "#ffffff",
        "plotly_theme": "plotly_white"
    }

# --- 3. INJEKSI CSS SUPER KUAT ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    /* Global Font & Color Override */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    /* BACKGROUND UTAMA */
    .stApp {{
        background-color: {THEME['bg']};
    }}

    /* PAKSA SEMUA TEKS STREAMLIT MENGIKUTI TEMA (PENTING!) */
    .stMarkdown, .stMarkdown p, .stText, h1, h2, h3, h4, h5, h6, 
    .stToggle p, .stToggle label, div[data-testid="stMetricLabel"] {{
        color: {THEME['text_main']} !important;
    }}
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: {THEME['sidebar']};
        border-right: 1px solid {THEME['border']};
    }}
    [data-testid="stSidebar"] * {{
        color: #94a3b8 !important; /* Text sidebar selalu abu terang */
    }}
    [data-testid="stSidebar"] h1 {{
        color: white !important;
        border-bottom: 1px solid #334155;
    }}

    /* KPI CARD STYLE */
    .kpi-card {{
        background-color: {THEME['card']};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid {THEME['border']};
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }}
    .kpi-text h3 {{ margin: 0; font-size: 14px; color: {THEME['text_sub']} !important; font-weight: 500; }}
    .kpi-text h2 {{ margin: 5px 0 0 0; font-size: 24px; color: {THEME['text_main']} !important; font-weight: 700; }}
    
    .icon-box {{ width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }}
    .icon-blue {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; }}
    .icon-green {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}

    /* CHART CONTAINER */
    .chart-container {{
        background-color: {THEME['card']};
        padding: 20px;
        border-radius: 12px;
        border: 1px solid {THEME['border']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .chart-container h3 {{
        color: {THEME['text_main']} !important;
        margin-bottom: 15px;
    }}

    /* TABLE STYLE */
    .table-card {{
        background-color: {THEME['card']};
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        overflow-x: auto;
    }}
    table.custom-table {{ width: 100%; border-collapse: collapse; }}
    table.custom-table th {{
        text-align: left; padding: 12px;
        border-bottom: 2px solid {THEME['border']};
        color: {THEME['text_sub']} !important;
    }}
    table.custom-table td {{
        padding: 12px;
        border-bottom: 1px solid {THEME['border']};
        color: {THEME['text_main']} !important;
    }}

    /* HEADER */
    .welcome-text h4 {{ margin: 0; color: {THEME['text_main']} !important; font-weight: 700; }}
    .welcome-text small {{ color: {THEME['text_sub']} !important; }}

</style>
""", unsafe_allow_html=True)

# --- 4. DATABASE CONNECTION ---
@st.cache_resource
def get_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_data_warehouse.db')
    return create_engine(f'sqlite:///{db_path}')

engine = get_connection()

# Helper Functions
def format_currency(val): return f"${val:,.2f}"

def render_html_table(df, col_mapping):
    html = '<div class="table-card"><table class="custom-table">'
    html += '<thead><tr>' + ''.join([f'<th>{h}</th>' for h in col_mapping.values()]) + '</tr></thead><tbody>'
    for _, row in df.iterrows():
        html += '<tr>'
        for col_key in col_mapping.keys():
            val = row[col_key]
            if 'sales' in col_key.lower() and isinstance(val, (int, float)): val = format_currency(val)
            val = '-' if val is None or val == '' else val
            html += f'<td>{val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    return html

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h1>📊 DataViz</h1>", unsafe_allow_html=True)
    selected_page = st.radio("Menu", ["Dashboard", "Products", "Customers", "Settings"], label_visibility="collapsed")
    st.markdown("---")
    
    conn = engine.connect()
    try:
        years = pd.read_sql(text("SELECT DISTINCT strftime('%Y', Order_Date) as y FROM FactSales WHERE y IS NOT NULL ORDER BY y DESC"), conn)['y'].tolist()
    except: years = []
    conn.close()
    
    selected_year = 'All Time'
    if selected_page == "Dashboard":
        st.write("**Filter Data**")
        selected_year = st.selectbox("Select Year", ['All Time'] + years)

# --- 6. MAIN CONTENT ---
st.markdown("""
<div class="header-style" style="display:flex; justify-content:space-between; margin-bottom:20px;">
    <div class="welcome-text">
        <h4>Welcome Back,</h4>
        <small>Admin User</small>
    </div>
</div>
""", unsafe_allow_html=True)

if selected_page == "Dashboard":
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1: st.title("Overview")
    with col_h2: st.markdown(f"<div style='text-align:right; color:{THEME['text_sub']}; padding-top:10px;'>Data: <b>{selected_year}</b></div>", unsafe_allow_html=True)

    conn = engine.connect()
    filter_sql = "" if selected_year == 'All Time' else f"WHERE strftime('%Y', Order_Date) = '{selected_year}'"
    
    try:
        sales = pd.read_sql(text(f"SELECT IFNULL(SUM(Sales_Amount), 0) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        orders = pd.read_sql(text(f"SELECT COUNT(*) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        df_trend = pd.read_sql(text(f"SELECT strftime('%Y-%m', Order_Date) as month, SUM(Sales_Amount) as total FROM FactSales {filter_sql} GROUP BY month ORDER BY month"), conn)
        df_prod = pd.read_sql(text(f"SELECT p.Product_Name, SUM(f.Sales_Amount) as total FROM FactSales f JOIN (SELECT DISTINCT Product_Key, Product_Name FROM DimProduct) p ON p.Product_Key LIKE '%' || f.Product_Key {filter_sql} GROUP BY p.Product_Name ORDER BY total DESC LIMIT 5"), conn)
    except Exception as e:
        sales, orders = 0, 0
        df_trend, df_prod = pd.DataFrame(), pd.DataFrame()
    finally:
        conn.close()

    c1, c2 = st.columns(2)
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-text"><h3>Total Sales</h3><h2>{format_currency(sales)}</h2></div><div class="icon-box icon-blue"><span>$</span></div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card"><div class="kpi-text"><h3>Total Orders</h3><h2>{orders:,}</h2></div><div class="icon-box icon-green"><span>🛒</span></div></div>""", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        st.markdown('<div class="chart-container"><h3>Sales Trend</h3>', unsafe_allow_html=True)
        if not df_trend.empty:
            fig = px.area(df_trend, x='month', y='total', markers=True, template=THEME['plotly_theme'])
            fig.update_traces(line_color='#3b82f6', fillcolor='rgba(59, 130, 246, 0.1)')
            fig.update_layout(paper_bgcolor=THEME['chart_bg'], plot_bgcolor=THEME['chart_bg'], margin=dict(l=10, r=10, t=10, b=10), height=300, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=THEME['border']), font=dict(color=THEME['text_sub']))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="chart-container"><h3>Top 5 Products</h3>', unsafe_allow_html=True)
        if not df_prod.empty:
            fig = px.bar(df_prod, x='total', y='Product_Name', orientation='h', text_auto='.2s', template=THEME['plotly_theme'])
            fig.update_traces(marker_color=['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444'])
            fig.update_layout(paper_bgcolor=THEME['chart_bg'], plot_bgcolor=THEME['chart_bg'], margin=dict(l=10, r=10, t=10, b=10), height=300, yaxis={'categoryorder':'total ascending'}, xaxis=dict(showgrid=False), font=dict(color=THEME['text_sub']))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_page == "Products":
    st.title("Product List")
    conn = engine.connect()
    try:
        q = text("""SELECT p.Product_Name, p.Product_Line, IFNULL(SUM(f.Sales_Amount), 0) as sales FROM (SELECT DISTINCT Product_Key, Product_Name, Product_Line FROM DimProduct) p LEFT JOIN FactSales f ON p.Product_Key LIKE '%' || f.Product_Key GROUP BY p.Product_Name ORDER BY sales DESC LIMIT 50""")
        df = pd.read_sql(q, conn)
        st.markdown(render_html_table(df, {'Product_Name': 'Product Name', 'Product_Line': 'Category', 'sales': 'Total Sales'}), unsafe_allow_html=True)
    except: st.error("Database Error")
    finally: conn.close()

elif selected_page == "Customers":
    st.title("Customer List")
    conn = engine.connect()
    try:
        df = pd.read_sql(text("SELECT Customer_ID as id, First_Name || ' ' || Last_Name as name, 'USA' as country FROM DimCustomer LIMIT 50"), conn)
        st.markdown(render_html_table(df, {'id': 'ID', 'name': 'Name', 'country': 'Country'}), unsafe_allow_html=True)
    except: st.error("Database Error")
    finally: conn.close()

elif selected_page == "Settings":
    st.title("Settings")
    
    with st.container():
        # HTML Header untuk Card
        st.markdown(f"""
        <div class="kpi-card" style="display:block; min-height:120px; padding-bottom:10px;">
            <h3 style="margin-bottom:15px; font-size:18px; color:{THEME['text_main']} !important;">Appearance</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Toggle ditaruh menggunakan margin negatif via CSS atau Columns agar terlihat masuk ke card
        # Tapi cara paling aman adalah menaruhnya di bawah header dalam layout column
        
        # Kita "inject" toggle ini seolah-olah di dalam card menggunakan layout visual
        col1, col2 = st.columns([3, 1])
        with col1:
             st.markdown(f"<p style='margin-top:-80px; margin-left:25px; position:relative; z-index:99; color:{THEME['text_sub']} !important;'>Toggle theme to switch between Light and Dark mode.</p>", unsafe_allow_html=True)
        with col2:
             st.markdown("<div style='margin-top:-85px; margin-right:25px; position:relative; z-index:99;'>", unsafe_allow_html=True)
             is_dark = st.toggle("Enable Dark Mode", value=st.session_state['dark_mode'])
             st.markdown("</div>", unsafe_allow_html=True)

             if is_dark != st.session_state['dark_mode']:
                st.session_state['dark_mode'] = is_dark
                st.rerun()
