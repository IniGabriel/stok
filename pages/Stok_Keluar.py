import streamlit as st
from db import get_conn
from PIL import Image
import numpy as np
import cv2
import time

st.set_page_config(page_title="Kurangi Stok", page_icon="➖")

# ===== CEK LOGIN =====
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")

st.title("➖ Kurangi Stok Barang")
st.write("Scan barcode untuk mengurangi stok sebanyak 1.")


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

        bc = data.strip()

        # ======================================================
        # VALIDASI BARCODE
        # ======================================================
        if len(bc) < 4:
            st.error("Barcode tidak valid.")
        else:
            try:
                item_code = bc[:4]

                conn = get_conn()
                cur = conn.cursor()

                # Cek apakah barang ada
                cur.execute("SELECT item_id, nama_barang FROM items WHERE barcode=%s", (item_code,))
                row = cur.fetchone()

                if not row:
                    st.error("Item tidak ditemukan di database.")
                else:
                    item_id, item_name = row

                    # Ambil stok per rak
                    cur.execute("SELECT rak, jumlah FROM stock WHERE item_id=%s ORDER BY rak", (item_id,))
                    rak_data = cur.fetchall()

                    if not rak_data:
                        st.error("Stok item ini belum ada.")
                    else:
                        # ================================================
                        # FILTER → hanya rak dengan qty > 0
                        # ================================================
                        rak_valid = [(rak, qty) for rak, qty in rak_data if qty > 0]

                        if len(rak_valid) == 0:
                            st.error("Tidak ada rak yang memiliki stok (>0).")
                        elif len(rak_valid) == 1:
                            # ================================================
                            # Hanya 1 rak punya stok → langsung kurangi
                            # ================================================
                            rak, qty = rak_valid[0]
                            jumlah_baru = max(0, qty - 1)

                            cur.execute("""
                                UPDATE stock
                                SET jumlah=%s
                                WHERE item_id=%s AND rak=%s
                            """, (jumlah_baru, item_id, rak))

                            conn.commit()

                            st.success(
                                f"Item {item_code} ({item_name}) di rak {rak} dikurangi 1. "
                                f"Sisa stok: {jumlah_baru}"
                            )

                        else:
                            # ================================================
                            # Banyak rak punya stok → user pilih rak
                            # ================================================
                            list_rak = [rak for rak, qty in rak_valid]

                            st.warning(
                                f"Item **{item_name}** memiliki stok di rak: "
                                f"{', '.join(list_rak)}"
                            )

                            rak_dipilih = st.selectbox(
                                "Pilih rak yang ingin dikurangi 1:",
                                options=list_rak,
                                key="rak_pilihan"
                            )

                            if st.button("Kurangi 1 di rak ini"):
                                cur.execute(
                                    "SELECT jumlah FROM stock WHERE item_id=%s AND rak=%s",
                                    (item_id, rak_dipilih)
                                )
                                current_qty = cur.fetchone()[0]
                                jumlah_baru = max(0, current_qty - 1)

                                cur.execute("""
                                    UPDATE stock
                                    SET jumlah=%s
                                    WHERE item_id=%s AND rak=%s
                                """, (jumlah_baru, item_id, rak_dipilih))

                                conn.commit()

                                st.success(
                                    f"Stok item {item_code} ({item_name}) di rak {rak_dipilih} dikurangi 1. "
                                    f"Sisa stok: {jumlah_baru}"
                                )

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.error("Gagal membaca QR Code — pastikan kamera fokus & jelas.")