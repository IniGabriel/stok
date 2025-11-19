import streamlit as st
from db import get_conn
import psycopg2
import time

st.set_page_config(page_title="Tambah Item", page_icon="➕", layout="wide")

# CEK LOGIN
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")

st.title("➕ Tambah Item Baru")

st.markdown("Masukkan barcode dan nama barang untuk menambahkan item baru.")

# ============================
# FORM INPUT
# ============================
barcode = st.text_input("Barcode", max_chars=100)
nama_barang = st.text_input("Nama Barang", max_chars=200)

if st.button("Simpan", type="primary"):
    if barcode == "" or nama_barang == "":
        st.error("Barcode dan Nama Barang wajib diisi!")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            # -----------------------------------
            # INSERT KE ITEMS
            # -----------------------------------
            cur.execute("""
                INSERT INTO items (barcode, nama_barang)
                VALUES (%s, %s)
                RETURNING item_id
            """, (barcode, nama_barang))

            item_id = cur.fetchone()[0]  # ambil ID hasil insert

            # -----------------------------------
            # INSERT DEFAULT KE STOCK
            # updated_at FORMAT "18 Nov 2025"
            # -----------------------------------
            cur.execute("""
                INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                VALUES (%s, %s, %s, TO_CHAR(NOW(), 'DD Mon YYYY'))
            """, (item_id, "0", 0))

            # SAVE
            conn.commit()
            cur.close()
            conn.close()

            st.success(f"Item '{nama_barang}' berhasil ditambahkan!")
            st.info("Stock default berhasil dibuat (rak 0, jumlah 0).")

        except psycopg2.errors.UniqueViolation:
            st.error("Barcode sudah terdaftar!")
        except Exception as e:
            st.error(f"Terjadi error: {e}")
