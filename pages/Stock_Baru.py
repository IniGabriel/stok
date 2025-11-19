import streamlit as st
from db import get_conn
import datetime
from PIL import Image
import numpy as np
import cv2
import time

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

# ===== CEK LOGIN =====
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")


st.title("📷 Scan Barcode – QR Live Reader (OpenCV)")
st.write("Arahkan kamera HP/Laptop ke QR Code. Sistem membaca otomatis.")


# ======================================================
# CAMERA INPUT 
# ======================================================

if "barcode_input" not in st.session_state:
    st.session_state["barcode_input"] = ""

capture = st.camera_input("📸 Scan QR Code")

if capture:
    img = Image.open(capture)
    frame = np.array(img)

    qr = cv2.QRCodeDetector()
    data, pts, _ = qr.detectAndDecode(frame)

    if data:
        st.session_state["barcode_input"] = data
        st.success(f"Barcode terbaca: **{data}**")
    else:
        st.error("Gagal membaca QR Code — pastikan kamera fokus & jelas.")


# ======================================================
# INPUT RAK & JUMLAH
# ======================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

# 🔽 Dropdown rak 1–8
rak = st.selectbox("Rak tujuan", [str(i) for i in range(1, 9)])
qty = st.number_input("Jumlah item", min_value=1, value=1, step=1)


# ======================================================
# SIMPAN KE DATABASE
# ======================================================

if st.button("➕ Tambahkan Stok"):

    bc = st.session_state["barcode_input"].strip()

    if len(bc) < 10:
        st.error("Barcode tidak valid.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            # Ambil 4 digit pertama sebagai kode barang
            item_code = bc[:4]

            # =========================================
            # CEK BARANG ADA DI TABEL ITEMS?
            # =========================================
            cur.execute(
                "SELECT item_id, nama_barang FROM items WHERE barcode=%s",
                (item_code,)
            )
            row = cur.fetchone()

            if not row:
                st.error("Item tidak ada. Tambahkan dulu di halaman Add Items.")
                raise Exception("Item not found")

            item_id = row[0]
            item_name = row[1]

            # =========================================
            # EXTRACT TANGGAL dari barcode: DDMMYY
            # =========================================
            date = bc[4:10]
            day = int(date[:2])
            month = int(date[2:4])
            year = 2000 + int(date[4:6])

            tanggal = datetime.date(year, month, day).strftime("%d %b %Y")

            # =========================================
            # CEK APAKAH ITEM SUDAH ADA DI RAK TERSEBUT?
            # =========================================
            cur.execute("""
                SELECT jumlah FROM stock
                WHERE item_id=%s AND rak=%s
            """, (item_id, rak))
            s = cur.fetchone()

            if s:
                # Jika item & rak sama → update
                jumlah = s[0] + qty
                cur.execute("""
                    UPDATE stock
                    SET jumlah=%s, terakhir_update=%s
                    WHERE item_id=%s AND rak=%s
                """, (jumlah, tanggal, item_id, rak))
            else:
                # Jika rak berbeda → insert baris baru
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, rak, qty, tanggal))

            conn.commit()

            # =========================================
            # SUCCESS MESSAGE
            # =========================================
            st.success(
                f"Stok item {item_code} ({item_name}) di rak {rak} berhasil ditambahkan sebanyak {qty} item!"
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan saat menambahkan stok: {e}")
