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
st.write("Scan barcode barang untuk mengurangi stok sebanyak 1.")

# ======================================================
# CAMERA INPUT 
# ======================================================

if "barcode_input" not in st.session_state:
    st.session_state["barcode_input"] = ""

capture = st.camera_input("📸 Scan Barcode Barang")

if capture:
    img = Image.open(capture)
    frame = np.array(img)

    qr = cv2.QRCodeDetector()
    data, pts, _ = qr.detectAndDecode(frame)

    if data:
        bc = data.strip()

        st.session_state["barcode_input"] = bc
        st.success(f"Barcode terbaca: **{bc}**")

        try:
            conn = get_conn()
            cur = conn.cursor()

            # ==========================
            # CEK ITEM LANGSUNG DARI DB
            # ==========================
            cur.execute("SELECT item_id, nama_barang FROM items WHERE barcode=%s", (bc,))
            row = cur.fetchone()

            if not row:
                st.error("Item tidak ditemukan di database.")
                raise Exception()

            item_id, item_name = row
            st.info(f"🛒 Nama Item: **{item_name}**")

            # ==========================
            # CEK STOK ITEM
            # ==========================
            cur.execute("""
                SELECT rak, jumlah 
                FROM stock
                WHERE item_id=%s
                ORDER BY rak
            """, (item_id,))
            stok_list = cur.fetchall()

            if not stok_list:
                st.error("Stok item ini belum ada.")
                raise Exception()

            stok_valid = [(rak, qty) for rak, qty in stok_list if qty > 0]

            if not stok_valid:
                st.error("Tidak ada stok dengan jumlah > 0.")
                raise Exception()

            rak_set = [rak for rak, qty in stok_valid]

            # ==========================================================
            # FUNGSI CEK DAN HAPUS ITEM
            # ==========================================================
            def hapus_item_jika_habis(item_id, item_name):
                cur.execute("SELECT COUNT(*) FROM stock WHERE item_id=%s", (item_id,))
                sisa = cur.fetchone()[0]

                if sisa == 0:
                    cur.execute("DELETE FROM items WHERE item_id=%s", (item_id,))
                    conn.commit()
                    st.success(f"Item **{item_name}** dihapus karena semua stoknya habis.")

            # ==========================================================
            # KASUS 1 — cuma ada 1 rak → langsung kurangi
            # ==========================================================
            if len(rak_set) == 1:
                rak_auto = rak_set[0]

                cur.execute("""
                    SELECT jumlah FROM stock
                    WHERE item_id=%s AND rak=%s
                """, (item_id, rak_auto))
                qty_now = cur.fetchone()[0]

                qty_new = qty_now - 1

                if qty_new <= 0:
                    cur.execute("""
                        DELETE FROM stock 
                        WHERE item_id=%s AND rak=%s
                    """, (item_id, rak_auto))
                    msg = "Stok habis → baris stok dihapus."
                else:
                    cur.execute("""
                        UPDATE stock SET jumlah=%s
                        WHERE item_id=%s AND rak=%s
                    """, (qty_new, item_id, rak_auto))
                    msg = f"Sisa stok: {qty_new}"

                conn.commit()
                hapus_item_jika_habis(item_id, item_name)

                st.success(
                    f"Stok **{item_name}** di rak {rak_auto} dikurangi 1. {msg}"
                )
                raise Exception()

            # ==========================================================
            # KASUS 2 — banyak rak → pilih rak
            # ==========================================================
            st.warning(f"Item tersedia di rak: {', '.join(rak_set)}")

            rak_pilih = st.selectbox("Pilih rak yang ingin dikurangi:", rak_set, key="pilih_rak")

            if st.button("Kurangi 1"):

                cur.execute("""
                    SELECT jumlah FROM stock
                    WHERE item_id=%s AND rak=%s
                """, (item_id, rak_pilih))
                qty_now = cur.fetchone()[0]

                qty_new = qty_now - 1

                if qty_new <= 0:
                    cur.execute("""
                        DELETE FROM stock 
                        WHERE item_id=%s AND rak=%s
                    """, (item_id, rak_pilih))
                    msg2 = "Stok habis → baris stok dihapus."
                else:
                    cur.execute("""
                        UPDATE stock SET jumlah=%s
                        WHERE item_id=%s AND rak=%s
                    """, (qty_new, item_id, rak_pilih))
                    msg2 = f"Sisa stok: {qty_new}"

                conn.commit()
                hapus_item_jika_habis(item_id, item_name)

                st.success(
                    f"Stok item **{item_name}** di rak {rak_pilih} dikurangi 1. {msg2}"
                )

        except Exception:
            pass

    else:
        st.error("Gagal membaca QR Code — pastikan kamera fokus & jelas.")
