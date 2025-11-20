import streamlit as st
from db import get_conn
import time
from PIL import Image
import numpy as np
import cv2

st.set_page_config(page_title="Tambah Stok", page_icon="📦")

# ===== CEK LOGIN =====
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")

st.title("📦 Tambah Stok Barang")

# ======================================
# SCAN QR → HASILNYA ADALAH RAK!
# ======================================
st.subheader("📷 Scan QR Rak")
qr_capture = st.camera_input("Scan QR RAK (contoh: 01, 02, 03)")

rak_from_qr = None

if qr_capture:
    img = Image.open(qr_capture)
    frame = np.array(img)

    qr = cv2.QRCodeDetector()
    data, pts, _ = qr.detectAndDecode(frame)

    if data:
        rak_from_qr = data.strip()

        # pastikan hanya 2 digit
        if len(rak_from_qr) == 2 and rak_from_qr.isdigit():
            rak_number = int(rak_from_qr)
            st.success(f"📍 Rak terbaca: **Rak {rak_number}**")
        else:
            st.error("QR tidak valid — harus 2 digit angka (misal: 01, 02).")
            rak_from_qr = None
    else:
        st.error("Gagal membaca QR Code.")

# ======================================
# AMBIL DATA ITEM DARI DATABASE
# ======================================
try:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT barcode, nama_barang FROM items ORDER BY nama_barang")
    item_rows = cur.fetchall()

    if not item_rows:
        st.error("Belum ada data item di database.")
        st.stop()

    # Buat mapping dari nama_barang → barcode
    ITEM_LOOKUP = {row[1]: row[0] for row in item_rows}

except Exception as e:
    st.error(f"Gagal mengambil data item: {e}")
    st.stop()

# ======================================
# PILIH ITEM & JUMLAH
# ======================================
item_name = st.selectbox("Pilih Barang", list(ITEM_LOOKUP.keys()))
item_code = ITEM_LOOKUP[item_name]
qty = st.number_input("Jumlah", min_value=1, value=1, step=1)

# ======================================
# SIMPAN DATA KE DATABASE
# ======================================
if st.button("➕ Tambah Stok ke RAK"):

    if not rak_from_qr:
        st.error("QR Rak belum terbaca!")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            # Cari item_id dari barcode
            cur.execute("SELECT item_id FROM items WHERE barcode=%s", (item_code,))
            row = cur.fetchone()

            if not row:
                st.error("Item belum ada di database. Tambahkan dulu.")
                raise Exception("Item not found")

            item_id = row[0]
            rak = str(int(rak_from_qr))  # "01" → "1"

            # Cek stok lama
            cur.execute("""
                SELECT jumlah FROM stock
                WHERE item_id=%s AND rak=%s
            """, (item_id, rak))
            s = cur.fetchone()

            if s:
                jumlah_baru = s[0] + qty
                cur.execute("""
                    UPDATE stock
                    SET jumlah=%s
                    WHERE item_id=%s AND rak=%s
                """, (jumlah_baru, item_id, rak))
                pesan = f"Jumlah stok diperbarui menjadi {jumlah_baru}"
            else:
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah)
                    VALUES (%s, %s, %s)
                """, (item_id, rak, qty))
                pesan = "Stok baru berhasil ditambahkan"

            conn.commit()

            st.success(
                f"Barang **{item_name}** (kode {item_code}) "
                f"ditambahkan ke **Rak {rak}**. {pesan}."
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
