import streamlit as st
from db import get_conn
import datetime
from PIL import Image
import numpy as np
import zxingcpp

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Stable Scanner (ZXing Python)")
st.write("Gunakan kamera HP / laptop atau upload foto barcode.")

barcode_value = st.text_input("Barcode terbaca:", key="barcode_input")

# =====================================================
# 1. CAMERA INPUT (dijamin muncul kamera)
# =====================================================

st.subheader("📸 Kamera Scanner (Pasti Muncul)")

img_file = st.camera_input("Ambil foto barcode:")

if img_file:
    img = Image.open(img_file)
    frame = np.array(img)

    result = zxingcpp.read_barcodes(frame)

    if result:
        code = result[0].text
        st.session_state["barcode_input"] = code
        st.success(f"Barcode terbaca: {code}")
    else:
        st.error("Gagal membaca barcode")


# =====================================================
# 2. UPLOAD FOTO
# =====================================================

st.subheader("🖼 Upload Foto Barcode")

uploaded = st.file_uploader("Upload gambar barcode", type=["png", "jpg", "jpeg"])

if uploaded:
    img = Image.open(uploaded)
    frame = np.array(img)

    result = zxingcpp.read_barcodes(frame)
    if result:
        code = result[0].text
        st.session_state["barcode_input"] = code
        st.success(f"Barcode terbaca: {code}")
    else:
        st.error("Gagal membaca barcode")

# =====================================================
# 3. SIMPAN KE DATABASE
# =====================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = st.session_state.get("barcode_input", "").strip()

    if len(bc) < 10:
        st.error("Barcode tidak valid.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = bc[:4]
            date_code = bc[4:10]

            day = int(date_code[:2])
            month = int(date_code[2:4])
            year = 2000 + int(date_code[4:6])

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
            srow = cur.fetchone()

            if srow:
                jumlah = srow[0] + 1
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

            st.success(f"Stok {item_code} berhasil ditambahkan!")

        except Exception as e:
            st.error(str(e))
