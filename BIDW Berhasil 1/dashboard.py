import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, pool
import plotly.express as px
import os

# --- 1. CONFIG & SESSION STATE ---
try:
    st.set_page_config(
        page_title="Executive Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except:
    pass # Hindari error jika config dipanggil dua kali

# Inisialisasi State Dark Mode
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False

# --- 2. CEK DATABASE (DEBUGGING) ---
db_filename = 'my_data_warehouse.db'
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_filename)

if not os.path.exists(db_path):
    st.error(f"❌ ERROR FATAL: File database '{db_filename}' tidak ditemukan!")
    st.warning(f"Sistem mencari di folder ini: {os.path.dirname(db_path)}")
    st.info("👉 Pastikan file 'dashboard.py' dan 'my_data_warehouse.db' ada di folder yang SAMA.")
    st.stop() # Hentikan aplikasi jika DB tidak ada

# --- 3. DEFINISI WARNA (PALET DINAMIS) ---
if st.session_state['dark_mode']:
    # DARK MODE
    THEME = {
        "bg": "#0f172a", "card": "#1e293b", "text_main": "#f8fafc",
        "text_sub": "#94a3b8", "sidebar": "#020617", "border": "#334155",
        "chart_bg": "#1e293b", "plotly_theme": "plotly_dark"
    }
else:
    # LIGHT MODE
    THEME = {
        "bg": "#f3f4f6", "card": "#ffffff", "text_main": "#111827",
        "text_sub": "#6b7280", "sidebar": "#1f2937", "border": "#e5e7eb",
        "chart_bg": "#ffffff", "plotly_theme": "plotly_white"
    }

# --- 4. INJEKSI CSS AMAN ---
# Menggunakan double curly braces {{ }} untuk CSS agar tidak bentrok dengan Python f-string
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    /* BACKGROUND */
    .stApp {{
        background-color: {THEME['bg']};
    }}

    /* PAKSA WARNA TEKS (Override Streamlit) */
    h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stText {{
        color: {THEME['text_main']} !important;
    }}
    
    /* SIDEBAR */
    [data-testid="stSidebar"] {{
        background-color: {THEME['sidebar']};
        border-right: 1px solid {THEME['border']};
    }}
    [data-testid="stSidebar"] h1 {{
        color: white !important;
    }}
    [data-testid="stSidebar"] * {{
        color: #94a3b8 !important; /* Sidebar text tetap abu terang */
    }}

    /* CARDS */
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
    .icon-box {{ width: 50px; height: 50px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 24px; }}
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
</style>
""", unsafe_allow_html=True)

# --- 5. KONEKSI DATABASE (DENGAN NULLPOOL) ---
# Menggunakan NullPool mencegah error 'Database is locked'
@st.cache_resource
def get_engine():
    return create_engine(f'sqlite:///{db_path}', poolclass=pool.NullPool)

engine = get_engine()

# --- 6. NAVIGASI & SIDEBAR ---
with st.sidebar:
    st.markdown("<h1>📊 DataViz</h1>", unsafe_allow_html=True)
    selected_page = st.radio("Menu", ["Dashboard", "Products", "Customers", "Settings"], label_visibility="collapsed")
    st.markdown("---")
    
    # Ambil Tahun
    years = []
    try:
        conn = engine.connect()
        df_years = pd.read_sql(text("SELECT DISTINCT strftime('%Y', Order_Date) as y FROM FactSales WHERE y IS NOT NULL ORDER BY y DESC"), conn)
        years = df_years['y'].tolist()
        conn.close()
    except Exception as e:
        st.error(f"DB Error: {e}")

    selected_year = 'All Time'
    if selected_page == "Dashboard":
        st.write("**Filter Year**")
        selected_year = st.selectbox("Select Year", ['All Time'] + years)

# --- 7. KONTEN HALAMAN ---

# Header Umum
st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div>
        <h2 style="margin:0;">{selected_page}</h2>
        <small style="color:{THEME['text_sub']} !important;">Welcome Back, Admin</small>
    </div>
    <div style="text-align:right;">
        <span style="color:{THEME['text_sub']} !important;">{selected_year if selected_page=='Dashboard' else ''}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# >>> HALAMAN DASHBOARD
if selected_page == "Dashboard":
    try:
        conn = engine.connect()
        filter_sql = "" if selected_year == 'All Time' else f"WHERE strftime('%Y', Order_Date) = '{selected_year}'"

        # KPI Query
        sales = pd.read_sql(text(f"SELECT IFNULL(SUM(Sales_Amount), 0) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        orders = pd.read_sql(text(f"SELECT COUNT(*) FROM FactSales {filter_sql}"), conn).iloc[0,0]
        
        # Trend Query
        trend_q = text(f"SELECT strftime('%Y-%m', Order_Date) as month, SUM(Sales_Amount) as total FROM FactSales {filter_sql} GROUP BY month ORDER BY month")
        df_trend = pd.read_sql(trend_q, conn)
        
        # Top Products Query
        prod_q = text(f"SELECT p.Product_Name, SUM(f.Sales_Amount) as total FROM FactSales f JOIN (SELECT DISTINCT Product_Key, Product_Name FROM DimProduct) p ON p.Product_Key LIKE '%' || f.Product_Key {filter_sql} GROUP BY p.Product_Name ORDER BY total DESC LIMIT 5")
        df_prod = pd.read_sql(prod_q, conn)
        
        conn.close()

        # KPI Display (Custom HTML)
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

        # Charts
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
        st.error(f"Terjadi kesalahan saat memuat Dashboard: {e}")

# >>> HALAMAN PRODUCTS
elif selected_page == "Products":
    try:
        conn = engine.connect()
        q = text("""SELECT p.Product_Name, p.Product_Line, IFNULL(SUM(f.Sales_Amount), 0) as sales FROM (SELECT DISTINCT Product_Key, Product_Name, Product_Line FROM DimProduct) p LEFT JOIN FactSales f ON p.Product_Key LIKE '%' || f.Product_Key GROUP BY p.Product_Name ORDER BY sales DESC LIMIT 50""")
        df = pd.read_sql(q, conn)
        conn.close()
        
        # Render Table
        html = f'<div class="table-card"><table class="custom-table"><thead><tr><th>Product Name</th><th>Category</th><th>Total Sales</th></tr></thead><tbody>'
        for _, r in df.iterrows():
            html += f"<tr><td>{r['Product_Name']}</td><td>{r['Product_Line'] or '-'}</td><td>${r['sales']:,.2f}</td></tr>"
        html += '</tbody></table></div>'
        st.markdown(html, unsafe_allow_html=True)
    except Exception as e: st.error(f"Error: {e}")

# >>> HALAMAN CUSTOMERS
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
    except Exception as e: st.error(f"Error: {e}")

# >>> HALAMAN SETTINGS
elif selected_page == "Settings":
    st.markdown(f"""
    <div class="kpi-card" style="display:block;">
        <h3 style="margin-bottom:10px;">Appearance</h3>
        <p style="font-size:14px; color:{THEME['text_sub']} !important;">Toggle switch di bawah untuk mengubah tema.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Toggle Switch
    is_dark = st.toggle("Enable Dark Mode", value=st.session_state['dark_mode'])
    if is_dark != st.session_state['dark_mode']:
        st.session_state['dark_mode'] = is_dark
        st.rerun()
