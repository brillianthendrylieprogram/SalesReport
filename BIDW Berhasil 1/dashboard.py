import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, pool
import plotly.express as px
import os

# --- 1. CONFIG HALAMAN (WAJIB PALING ATAS) ---
st.set_page_config(
    page_title="Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STATE MANAGEMENT (FITUR STABIL) ---
# Inisialisasi status Dark Mode jika belum ada
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False

# Ambil status saat ini dengan aman
is_dark_mode = st.session_state.get("dark_mode", False)

# --- 3. DEFINISI TEMA (WARNA) ---
if is_dark_mode:
    # DARK MODE PALETTE
    THEME = {
        "bg": "#0f172a", "card": "#1e293b", "text_main": "#f8fafc",
        "text_sub": "#94a3b8", "sidebar": "#020617", "border": "#334155",
        "chart_bg": "#1e293b", "plotly_theme": "plotly_dark",
        "icon_bg": "rgba(255,255,255,0.05)"
    }
else:
    # LIGHT MODE PALETTE
    THEME = {
        "bg": "#f3f4f6", "card": "#ffffff", "text_main": "#111827",
        "text_sub": "#6b7280", "sidebar": "#1f2937", "border": "#e5e7eb",
        "chart_bg": "#ffffff", "plotly_theme": "plotly_white",
        "icon_bg": "rgba(0,0,0,0.05)"
    }

# --- 4. INJEKSI CSS (SUPRES ERROR & PAKSA WARNA) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    /* Global Override */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    /* BACKGROUND UTAMA */
    .stApp {{
        background-color: {THEME['bg']};
    }}

    /* PAKSA SEMUA TEKS BERUBAH WARNA */
    h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stText, .stMetricValue, .stMetricLabel {{
        color: {THEME['text_main']} !important;
    }}
    
    /* SIDEBAR KHUSUS */
    [data-testid="stSidebar"] {{
        background-color: {THEME['sidebar']};
        border-right: 1px solid {THEME['border']};
    }}
    [data-testid="stSidebar"] h1 {{ color: white !important; }}
    [data-testid="stSidebar"] span {{ color: #94a3b8 !important; }}

    /* KPI CARDS (KARTU) */
    .kpi-card {{
        background-color: {THEME['card']};
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid {THEME['border']};
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    /* ICONS */
    .icon-box {{ 
        width: 50px; height: 50px; border-radius: 10px; 
        display: flex; align-items: center; justify-content: center; font-size: 24px; 
    }}
    .icon-blue {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6 !important; }}
    .icon-green {{ background: rgba(16, 185, 129, 0.2); color: #10b981 !important; }}
    
    /* TABLES */
    .table-card {{
        background-color: {THEME['card']};
        padding: 20px;
        border-radius: 10px;
        border: 1px solid {THEME['border']};
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

    /* CHART CONTAINER */
    .chart-box {{
        background-color: {THEME['card']};
        padding: 15px;
        border-radius: 12px;
        border: 1px solid {THEME['border']};
    }}
    
    /* HIDE DEFAULT HEADER STRIP */
    header[data-testid="stHeader"] {{
        background-color: {THEME['bg']};
    }}
</style>
""", unsafe_allow_html=True)

# --- 5. KONEKSI DATABASE AMAN (ANTI-LOCK) ---
@st.cache_resource
def get_engine():
    # Pastikan path benar
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_data_warehouse.db')
    # Gunakan NullPool agar SQLite tidak terkunci (Database Locked Error)
    return create_engine(f'sqlite:///{db_path}', poolclass=pool.NullPool)

engine = get_engine()

# --- 6. SIDEBAR MENU ---
with st.sidebar:
    st.markdown("<h1>📊 DataViz</h1>", unsafe_allow_html=True)
    selected_page = st.radio("Menu", ["Dashboard", "Products", "Customers", "Settings"], label_visibility="collapsed")
    st.markdown("---")
    
    # Ambil Tahun (Error Handling jika DB sibuk)
    years = []
    try:
        conn = engine.connect()
        df_years = pd.read_sql(text("SELECT DISTINCT strftime('%Y', Order_Date) as y FROM FactSales WHERE y IS NOT NULL ORDER BY y DESC"), conn)
        years = df_years['y'].tolist()
        conn.close()
    except:
        pass # Jika gagal load tahun, biarkan kosong dulu

    selected_year = 'All Time'
    if selected_page == "Dashboard":
        st.write("**Filter Year**")
        if years:
            selected_year = st.selectbox("Select Year", ['All Time'] + years)

# --- 7. LOGIKA HALAMAN ---

# Header Halaman
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div>
        <h2 style="margin:0;">{selected_page}</h2>
        <small style="color:{THEME['text_sub']} !important;">Welcome Back, Admin</small>
    </div>
</div>
""", unsafe_allow_html=True)

# >>> DASHBOARD
if selected_page == "Dashboard":
    try:
        conn = engine.connect()
        filter_sql = "" if selected_year == 'All Time' else f"WHERE strftime('%Y', Order_Date) = '{selected_year}'"

        # Query Data
        sales = pd.read_sql(text(f"SELECT IFNULL(SUM(Sales_Amount), 0) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        orders = pd.read_sql(text(f"SELECT COUNT(*) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        
        # Trend
        df_trend = pd.read_sql(text(f"SELECT strftime('%Y-%m', Order_Date) as month, SUM(Sales_Amount) as total FROM FactSales {filter_sql} GROUP BY month ORDER BY month"), conn)
        
        # Top Products (Fixed Logic)
        prod_sql = f"""
            SELECT p.Product_Name, SUM(f.Sales_Amount) as total 
            FROM FactSales f 
            JOIN (SELECT DISTINCT Product_Key, Product_Name FROM DimProduct) p 
            ON p.Product_Key LIKE '%' || f.Product_Key 
            {filter_sql} 
            GROUP BY p.Product_Name ORDER BY total DESC LIMIT 5
        """
        df_prod = pd.read_sql(text(prod_sql), conn)
        conn.close()

        # KPI CARDS
        c1, c2 = st.columns(2)
        c1.markdown(f"""
        <div class="kpi-card">
            <div>
                <h3 style="margin:0; font-size:14px; color:{THEME['text_sub']} !important;">Total Sales</h3>
                <h2 style="margin:5px 0 0 0; font-size:24px;">${sales:,.2f}</h2>
            </div>
            <div class="icon-box icon-blue"><span>$</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        c2.markdown(f"""
        <div class="kpi-card">
            <div>
                <h3 style="margin:0; font-size:14px; color:{THEME['text_sub']} !important;">Total Orders</h3>
                <h2 style="margin:5px 0 0 0; font-size:24px;">{orders:,}</h2>
            </div>
            <div class="icon-box icon-green"><span>🛒</span></div>
        </div>
        """, unsafe_allow_html=True)

        # CHARTS
        c3, c4 = st.columns(2)
        
        with c3:
            st.markdown('<div class="chart-box"><h3>Sales Trend</h3>', unsafe_allow_html=True)
            if not df_trend.empty:
                fig = px.area(df_trend, x='month', y='total', markers=True, template=THEME['plotly_theme'])
                fig.update_traces(line_color='#3b82f6', fillcolor='rgba(59, 130, 246, 0.1)')
                fig.update_layout(paper_bgcolor=THEME['chart_bg'], plot_bgcolor=THEME['chart_bg'], margin=dict(t=10, l=10, r=10, b=10), height=300, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor=THEME['border']))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c4:
            st.markdown('<div class="chart-box"><h3>Top 5 Products</h3>', unsafe_allow_html=True)
            if not df_prod.empty:
                fig = px.bar(df_prod, x='total', y='Product_Name', orientation='h', template=THEME['plotly_theme'])
                fig.update_traces(marker_color=['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444'])
                fig.update_layout(paper_bgcolor=THEME['chart_bg'], plot_bgcolor=THEME['chart_bg'], margin=dict(t=10, l=10, r=10, b=10), height=300, yaxis={'categoryorder':'total ascending'}, xaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Gagal memuat data dashboard. Error: {e}")

# >>> PRODUCTS
elif selected_page == "Products":
    try:
        conn = engine.connect()
        # Query product list (logic sama dengan app.py)
        q = text("""
            SELECT p.Product_Name, p.Product_Line, IFNULL(SUM(f.Sales_Amount), 0) as sales 
            FROM (SELECT DISTINCT Product_Key, Product_Name, Product_Line FROM DimProduct) p 
            LEFT JOIN FactSales f ON p.Product_Key LIKE '%' || f.Product_Key 
            GROUP BY p.Product_Name ORDER BY sales DESC LIMIT 50
        """)
        df = pd.read_sql(q, conn)
        conn.close()
        
        html = f'<div class="table-card"><table class="custom-table"><thead><tr><th>Product Name</th><th>Category</th><th>Total Sales</th></tr></thead><tbody>'
        for _, r in df.iterrows():
            html += f"<tr><td>{r['Product_Name']}</td><td>{r['Product_Line'] or '-'}</td><td>${r['sales']:,.2f}</td></tr>"
        html += '</tbody></table></div>'
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e: st.error(f"Error Products: {e}")

# >>> CUSTOMERS
elif selected_page == "Customers":
    try:
        conn = engine.connect()
        df = pd.read_sql("SELECT Customer_ID, First_Name || ' ' || Last_Name as name, 'USA' as country FROM DimCustomer LIMIT 50", conn)
        conn.close()

        html = f'<div class="table-card"><table class="custom-table"><thead><tr><th>ID</th><th>Name</th><th>Country</th></tr></thead><tbody>'
        for _, r in df.iterrows():
            html += f"<tr><td>{r['Customer_ID']}</td><td>{r['name']}</td><td>{r['country']}</td></tr>"
        html += '</tbody></table></div>'
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e: st.error(f"Error Customers: {e}")

# >>> SETTINGS (PERBAIKAN UTAMA)
elif selected_page == "Settings":
    # Gunakan Container Card
    st.markdown(f"""
    <div class="kpi-card" style="display:block;">
        <h3 style="margin-bottom:10px;">Appearance</h3>
        <p style="font-size:14px; color:{THEME['text_sub']} !important;">Toggle switch di bawah untuk mengubah tema Light/Dark.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- LOGIKA TOGGLE YANG AMAN ---
    # Kita gunakan parameter 'key' agar Streamlit yang mengurus statenya.
    # Tidak perlu if manual atau st.rerun().
    st.toggle("Enable Dark Mode", key="dark_mode")
    
    # Penjelasan: Saat toggle diklik, Streamlit otomatis update st.session_state['dark_mode'] 
    # dan melakukan RERUN script dari awal.
    # Di awal script (Baris 20), 'is_dark_mode' akan mengambil nilai baru tersebut
    # dan tema akan berubah otomatis.
