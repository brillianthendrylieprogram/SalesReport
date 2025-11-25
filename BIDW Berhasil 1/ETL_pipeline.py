import pandas as pd
from sqlalchemy import create_engine, text
import os
import sqlite3

# --- KONFIGURASI ---
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'my_data_warehouse.db')
engine = create_engine(f'sqlite:///{db_path}')

def find_data_directory():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Mencari folder 'source_crm' di: {current_dir}")
    for root, dirs, files in os.walk(current_dir):
        if 'source_crm' in dirs:
            print(f" -> Folder DITEMUKAN di: {root}")
            return root
    print("!!! ERROR FATAL: Folder 'source_crm' tidak ditemukan!")
    exit()

def debug_print_file_head(filepath):
    """Mencetak 3 baris pertama file untuk memastikan file tidak kosong/rusak"""
    print(f"\n--- CEK FISIK FILE: {os.path.basename(filepath)} ---")
    try:
        with open(filepath, 'r', encoding='latin1') as f: # Gunakan latin1 biar aman
            for i in range(3):
                print(f"Line {i+1}: {f.readline().strip()}")
    except Exception as e:
        print(f"Gagal membaca file: {e}")

def run_etl():
    print("\n=== MEMULAI PROSES ETL (VERSI DIAGNOSIS) ===")
    BASE_DIR = find_data_directory()
    
    # --- 1. EXTRACT ---
    sales_path = os.path.join(BASE_DIR, 'source_crm', 'sales_details.csv')
    cust_path = os.path.join(BASE_DIR, 'source_crm', 'cust_info.csv')
    prd_path = os.path.join(BASE_DIR, 'source_crm', 'prd_info.csv')
    
    # Debug print
    debug_print_file_head(sales_path)

    print("\n-> Membaca CSV dengan Pandas...")
    # Gunakan encoding latin1 dan paksa semua jadi string dulu biar tidak error parsing
    df_sales = pd.read_csv(sales_path, dtype=str, encoding='latin1')
    print(f"   [OK] Sales terbaca: {len(df_sales)} baris")

    df_cust_crm = pd.read_csv(cust_path, encoding='latin1')
    df_prd_crm = pd.read_csv(prd_path, encoding='latin1')
    
    # --- 2. TRANSFORM ---
    print("\n-> Transformasi Data...")

    # A. FIX FORMAT TANGGAL (Penyebab utama data 0)
    # Format di CSV: 20140128 (String sambung tanpa spasi/strip)
    # Kita ubah manual stringnya menjadi format YYYY-MM-DD agar SQLite paham
    def fix_date_format(val):
        s = str(val).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:]}" # 2014-01-28
        return None # Jika format aneh, biarkan kosong

    print("   ...Memperbaiki format tanggal...")
    date_cols = ['sls_order_dt', 'sls_ship_dt', 'sls_due_dt']
    for col in date_cols:
        # Terapkan fungsi fix manual
        df_sales[col] = df_sales[col].apply(fix_date_format)
        # Pastikan tipe datanya datetime
        df_sales[col] = pd.to_datetime(df_sales[col], errors='coerce')

    # B. FIX ANGKA (Sales Amount)
    print("   ...Memperbaiki angka penjualan...")
    df_sales['sls_sales'] = pd.to_numeric(df_sales['sls_sales'], errors='coerce').fillna(0)
    df_sales['sls_quantity'] = pd.to_numeric(df_sales['sls_quantity'], errors='coerce').fillna(0)
    
    # C. RENAME KOLOM
    fact_sales = df_sales.rename(columns={
        'sls_ord_num': 'Order_Number', 
        'sls_prd_key': 'Product_Key', 
        'sls_cust_id': 'Customer_ID',
        'sls_order_dt': 'Order_Date', 
        'sls_sales': 'Sales_Amount',
        'sls_quantity': 'Quantity',
        'sls_price': 'Unit_Price'
    })

    # Cek jumlah baris setelah transform
    print(f"   [INFO] Jumlah baris siap load: {len(fact_sales)}")
    if len(fact_sales) == 0:
        print("!!! ERROR: Data hilang saat transformasi! Cek format CSV Anda.")
        exit()

    # D. TRANSFORM PRODUCT & CUSTOMER (Sederhana)
    # Product
    df_prd_crm['prd_key'] = df_prd_crm['prd_key'].astype(str).str.strip().str.upper()
    dim_product = df_prd_crm.rename(columns={
        'prd_id': 'Product_ID', 'prd_key': 'Product_Key', 'prd_nm': 'Product_Name',
        'prd_cost': 'Product_Cost', 'prd_line': 'Product_Line'
    })

    # Customer (Simple Load)
    dim_customer = df_cust_crm[['cst_id', 'cst_key', 'cst_firstname', 'cst_lastname', 'cst_gndr']].copy()
    dim_customer.columns = ['Customer_ID', 'Customer_Key', 'First_Name', 'Last_Name', 'Gender']

    # --- 3. LOAD ---
    print("\n-> Loading ke Database SQLite...")
    try:
        fact_sales.to_sql('FactSales', engine, if_exists='replace', index=False)
        dim_product.to_sql('DimProduct', engine, if_exists='replace', index=False)
        dim_customer.to_sql('DimCustomer', engine, if_exists='replace', index=False)
        print("   [SUKSES] Tabel berhasil dibuat.")
    except Exception as e:
        print(f"!!! Gagal Load ke DB: {e}")

    # --- 4. VERIFIKASI AKHIR ---
    print("\n=== VERIFIKASI HASIL ===")
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM FactSales")).scalar()
        print(f"TOTAL DATA DI FactSales: {count} baris")
        
        if count > 0:
            print(">>> SELAMAT! Data sudah masuk. Silakan jalankan 'python app.py' sekarang.")
            # Cek sampel data
            sample = conn.execute(text("SELECT * FROM FactSales LIMIT 1")).fetchone()
            print(f"Contoh Data: {sample}")
        else:
            print(">>> MASIH 0? Ada masalah aneh pada library pandas/sqlite Anda.")

if __name__ == "__main__":
    run_etl()