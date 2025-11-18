import streamlit as st
from db import get_conn
import datetime
from PIL import Image
import numpy as np
import cv2

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – QR Live Reader (OpenCV)")
st.write("Arahkan kamera HP/Laptop ke QR Code. Sistem membaca otomatis.")


# ======================================================
# CAMERA INPUT (Tanpa preview & tanpa kolom kanan/kiri)
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
# BARCODE TERBACA
# ======================================================

barcode_value = st.text_input(
    "Barcode terbaca:",
    value=st.session_state.get("barcode_input", "")
)


# ======================================================
# SIMPAN KE DATABASE
# ======================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()

    if len(bc) < 10:
        st.error("Barcode tidak valid.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = bc[:4]
            date = bc[4:10]

            day = int(date[:2])
            month = int(date[2:4])
            year = 2000 + int(date[4:6])
            tanggal = datetime.date(year, month, day).strftime("%d %b %Y")

            cur.execute("SELECT item_id FROM items WHERE barcode=%s", (item_code,))
            row = cur.fetchone()

            if row:
                item_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO items (barcode, nama_barang)
                    VALUES (%s, %s)
                    RETURNING item_id
                """, (item_code, f"Item {item_code}"))
                item_id = cur.fetchone()[0]

            cur.execute("SELECT jumlah FROM stock WHERE item_id=%s", (item_id,))
            s = cur.fetchone()

            if s:
                jumlah = s[0] + 1
                cur.execute("""
                    UPDATE stock SET jumlah=%s, rak=%s, terakhir_update=%s
                    WHERE item_id=%s
                """, (jumlah, rak, tanggal, item_id))
            else:
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, rak, 1, tanggal))

            conn.commit()
            st.success(f"Stok item {item_code} berhasil ditambahkan!")

        except Exception as e:
            st.error(str(e))
