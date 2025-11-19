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

item_name_scanned = None  # untuk menampilkan nama barang

if capture:
    img = Image.open(capture)
    frame = np.array(img)

    qr = cv2.QRCodeDetector()
    data, pts, _ = qr.detectAndDecode(frame)

    if data:
        st.session_state["barcode_input"] = data
        st.success(f"Barcode terbaca: **{data}**")

        # Try fetch nama item
        bc = data.strip()
        if len(bc) >= 4:
            item_code = bc[:4]

            try:
                conn = get_conn()
                cur = conn.cursor()

                cur.execute(
                    "SELECT nama_barang FROM items WHERE barcode=%s",
                    (item_code,)
                )
                row = cur.fetchone()

                if row:
                    item_name_scanned = row[0]
                    st.info(f"🛒 Nama barang: **{item_name_scanned}**")
                else:
                    st.warning("Nama barang tidak ditemukan di database.")

            except:
                st.warning("Gagal mengambil nama barang dari database.")

    else:
        st.error("Gagal membaca QR Code — pastikan kamera fokus & jelas.")


# ======================================================
# INPUT RAK & JUMLAH
# ======================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

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

            item_code = bc[:4]

            # Ambil item_id & nama_barang
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

            # Extract tanggal dari barcode
            date = bc[4:10]
            day = int(date[:2])
            month = int(date[2:4])
            year = 2000 + int(date[4:6])

            tanggal = datetime.date(year, month, day).strftime("%d %b %Y")

            # Cek stok di rak
            cur.execute("""
                SELECT jumlah FROM stock
                WHERE item_id=%s AND rak=%s
            """, (item_id, rak))
            s = cur.fetchone()

            if s:
                jumlah = s[0] + qty
                cur.execute("""
                    UPDATE stock
                    SET jumlah=%s, terakhir_update=%s
                    WHERE item_id=%s AND rak=%s
                """, (jumlah, tanggal, item_id, rak))
            else:
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, rak, qty, tanggal))

            conn.commit()

            st.success(
                f"Stok item {item_code} (**{item_name}**) di rak {rak} berhasil "
                f"ditambahkan sebanyak {qty} item!"
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan saat menambahkan stok: {e}")
