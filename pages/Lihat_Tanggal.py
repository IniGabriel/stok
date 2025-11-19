import streamlit as st
from db import get_conn
from PIL import Image
import numpy as np
import cv2
import datetime
import time

st.set_page_config(page_title="Cek Tanggal Barang", page_icon="📅")

# ===== CEK LOGIN =====
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")

st.title("📅 Cek Tanggal dari Barcode")
st.write("Scan barcode untuk melihat tanggalnya.")

# ===========================
# STATE BARCODE
# ===========================
if "barcode_input" not in st.session_state:
    st.session_state["barcode_input"] = ""

# ===========================
# CAMERA INPUT
# ===========================
capture = st.camera_input("📸 Scan Barcode")

if capture:
    img = Image.open(capture)
    frame = np.array(img)

    qr = cv2.QRCodeDetector()
    data, pts, _ = qr.detectAndDecode(frame)

    if data:
        st.session_state["barcode_input"] = data
        barcode = data
        st.success(f"Barcode terbaca: **{data}**")

        # ======================================================
        # TAMPILKAN NAMA ITEM (4 DIGIT AWAL)
        # ======================================================
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = barcode[:4]

            cur.execute(
                "SELECT nama_barang FROM items WHERE barcode=%s",
                (item_code,)
            )
            row = cur.fetchone()

            if row:
                st.info(f"🛒 **Nama Item: {row[0]}**")
            else:
                st.warning("Nama item tidak ditemukan di database.")

        except Exception:
            st.warning("Gagal mengambil data item.")

        # ======================================================
        # AUTO TAMPILKAN TANGGAL
        # ======================================================
        try:
            if len(barcode) < 10:
                st.error("Barcode tidak valid.")
            else:
                tanggal_raw = barcode[-6:]

                dd = int(tanggal_raw[:2])
                mm = int(tanggal_raw[2:4])
                yy = int(tanggal_raw[4:6])

                year = 2000 + yy

                tanggal_obj = datetime.date(year, mm, dd)
                tanggal_format = tanggal_obj.strftime("%d %B %Y")

                st.success(f"📅 **Tanggal pada barcode: {tanggal_format}**")

        except Exception as e:
            st.error(f"Gagal membaca tanggal: {e}")

    else:
        st.error("Gagal membaca QR Code. Coba dekatkan barcode ke kamera.")
