from flask import Flask, render_template, jsonify, request
from sqlalchemy import create_engine, text
import pandas as pd
import os

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_data_warehouse.db')
engine = create_engine(f'sqlite:///{db_path}')

@app.route('/')
def index():
    return render_template('index.html')

# --- API BARU: AMBIL LIST TAHUN YANG TERSEDIA ---
@app.route('/api/years')
def get_years():
    conn = engine.connect()
    try:
        # Mengambil tahun unik dari Order_Date
        query = text("SELECT DISTINCT strftime('%Y', Order_Date) as year FROM FactSales WHERE year IS NOT NULL ORDER BY year DESC")
        df = pd.read_sql(query, conn)
        # Mengembalikan list tahun [2014, 2013, 2012, ...]
        return jsonify(df['year'].tolist())
    except Exception as e:
        print(f"Error getting years: {e}")
        return jsonify([])
    finally:
        conn.close()

@app.route('/api/data')
def get_dashboard_data():
    year = request.args.get('year', 'All')
    
    # 1. Filter Tahun
    date_filter = ""
    if year != 'All':
        date_filter = f"WHERE strftime('%Y', Order_Date) = '{year}'"

    conn = engine.connect()
    try:
        # 2. KPI
        sales_query = text(f"SELECT IFNULL(SUM(Sales_Amount), 0) as val FROM FactSales {date_filter}")
        orders_query = text(f"SELECT COUNT(*) as val FROM FactSales {date_filter}")
        
        sales = pd.read_sql(sales_query, conn).iloc[0]['val']
        orders = pd.read_sql(orders_query, conn).iloc[0]['val']

        # 3. TOP 5 PRODUK (Logic JOIN sudah diperbaiki)
        top_prod_query = text(f"""
            SELECT p.Product_Name, SUM(f.Sales_Amount) as total
            FROM FactSales f
            JOIN (
                SELECT DISTINCT Product_Key, Product_Name 
                FROM DimProduct
            ) p ON p.Product_Key LIKE '%' || f.Product_Key 
            {date_filter}
            GROUP BY p.Product_Name
            ORDER BY total DESC
            LIMIT 5
        """)
        df_prod = pd.read_sql(top_prod_query, conn)
        
        products_data = {
            'labels': df_prod['Product_Name'].tolist(),
            'values': df_prod['total'].tolist()
        }

        # 4. TREND BULANAN
        trend_query = text(f"""
            SELECT strftime('%Y-%m', Order_Date) as month, SUM(Sales_Amount) as total
            FROM FactSales
            {date_filter}
            GROUP BY month
            ORDER BY month
        """)
        df_trend = pd.read_sql(trend_query, conn)
        trend_data = {
            'labels': df_trend['month'].tolist(),
            'values': df_trend['total'].tolist()
        }

        return jsonify({
            'total_sales': f"${sales:,.2f}", 
            'total_orders': f"{orders:,}",
            'products': products_data, 
            'trend': trend_data
        })
        
    except Exception as e:
        print(f"ERROR API: {e}")
        return jsonify({
            'total_sales': '$0', 'total_orders': '0',
            'products': {'labels': [], 'values': []},
            'trend': {'labels': [], 'values': []}
        })
    finally:
        conn.close()

@app.route('/api/products_list')
def get_products_list():
    conn = engine.connect()
    try:
        q = text("""
            SELECT p.Product_Name, p.Product_Line, IFNULL(SUM(f.Sales_Amount), 0) as sales 
            FROM (SELECT DISTINCT Product_Key, Product_Name, Product_Line FROM DimProduct) p 
            LEFT JOIN FactSales f ON p.Product_Key LIKE '%' || f.Product_Key
            GROUP BY p.Product_Name 
            ORDER BY sales DESC 
            LIMIT 50
        """)
        df = pd.read_sql(q, conn)
        return jsonify(df.to_dict(orient='records'))
    except: return jsonify([])
    finally: conn.close()

@app.route('/api/customers_list')
def get_customers_list():
    conn = engine.connect()
    try:
        df = pd.read_sql("SELECT Customer_ID as id, First_Name || ' ' || Last_Name as name, 'USA' as country FROM DimCustomer LIMIT 50", conn)
        return jsonify(df.to_dict(orient='records'))
    except: return jsonify([])
    finally: conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)