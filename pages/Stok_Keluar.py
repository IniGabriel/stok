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

        # ==========================
        # VALIDASI MINIMAL 4 DIGIT
        # ==========================
        if len(bc) < 4:
            st.error("Barcode tidak valid.")
        else:
            try:
                item_code = bc[:4]

                conn = get_conn()
                cur = conn.cursor()

                # ==========================
                # CEK NAMA ITEM
                # ==========================
                cur.execute("SELECT item_id, nama_barang FROM items WHERE barcode=%s", (item_code,))
                row = cur.fetchone()

                if not row:
                    st.error("Item tidak ditemukan di database.")
                    stop = True
                else:
                    item_id, item_name = row
                    st.info(f"🛒 Nama Item: **{item_name}**")

                    # ==========================
                    # AMBIL SEMUA STOK ITEM INI
                    # ==========================
                    cur.execute("""
                        SELECT rak, jumlah, terakhir_update
                        FROM stock
                        WHERE item_id=%s
                        ORDER BY rak
                    """, (item_id,))
                    stok_list = cur.fetchall()

                    if not stok_list:
                        st.error("Stok item ini belum ada.")
                    else:
                        # FILTER yang qty > 0
                        stok_valid = [(rak, qty, tgl) for rak, qty, tgl in stok_list if qty > 0]

                        if len(stok_valid) == 0:
                            st.error("Tidak ada stok yang jumlahnya > 0.")
                            raise Exception()

                        # ===========================================
                        # LIST RAK VALID + LIST TANGGAL VALID
                        # ===========================================
                        rak_set = sorted(list({rak for rak, qty, tgl in stok_valid}))
                        tanggal_set = sorted(list({tgl for rak, qty, tgl in stok_valid}))

                        # ==========================================================
                        # KASUS 1 — hanya ada SATU rak dan SATU tanggal → AUTO KURANGI
                        # ==========================================================
                        if len(rak_set) == 1 and len(tanggal_set) == 1:
                            rak_auto = rak_set[0]
                            tgl_auto = tanggal_set[0]

                            cur.execute("""
                                SELECT jumlah FROM stock
                                WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                            """, (item_id, rak_auto, tgl_auto))
                            qty_now = cur.fetchone()[0]

                            qty_new = qty_now - 1

                            if qty_new <= 0:
                                cur.execute("""
                                    DELETE FROM stock 
                                    WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                                """, (item_id, rak_auto, tgl_auto))
                                msg = "Stok menjadi 0 → baris stok dihapus."
                            else:
                                cur.execute("""
                                    UPDATE stock SET jumlah=%s
                                    WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                                """, (qty_new, item_id, rak_auto, tgl_auto))
                                msg = f"Sisa stok: {qty_new}"

                            conn.commit()

                            st.success(
                                f"Stok item **{item_name}** di rak {rak_auto} (batch {tgl_auto}) dikurangi 1. {msg}"
                            )
                            raise Exception()   # Stop agar tidak lanjut logic bawah

                        # ==========================================================
                        # KASUS 2 — banyak rak → pilih rak
                        # ==========================================================
                        if len(rak_set) > 1:
                            st.warning(f"Item tersedia di rak: {', '.join(rak_set)}")
                            rak_pilih = st.selectbox("Pilih rak:", rak_set, key="pilih_rak")

                            # FILTER stok batch dalam rak itu
                            batch_rak = [tgl for rak, qty, tgl in stok_valid if rak == rak_pilih]
                        else:
                            rak_pilih = rak_set[0]
                            batch_rak = tanggal_set

                        # ==========================================================
                        # KASUS 3 — kalau dalam rak itu ada banyak tanggal → pilih tanggal
                        # ==========================================================
                        if len(batch_rak) > 1:
                            st.warning(f"Batch tersedia: {', '.join(batch_rak)}")
                            tgl_pilih = st.selectbox("Pilih batch (tanggal):", batch_rak, key="pilih_batch")
                        else:
                            tgl_pilih = batch_rak[0]

                        # ==========================================================
                        # TOMBOL KONFIRMASI
                        # ==========================================================
                        if st.button("Kurangi 1"):

                            cur.execute("""
                                SELECT jumlah FROM stock
                                WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                            """, (item_id, rak_pilih, tgl_pilih))
                            qty_now = cur.fetchone()[0]

                            qty_new = qty_now - 1

                            if qty_new <= 0:
                                cur.execute("""
                                    DELETE FROM stock 
                                    WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                                """, (item_id, rak_pilih, tgl_pilih))
                                msg2 = "Stok menjadi 0 → baris stok DIHAPUS."
                            else:
                                cur.execute("""
                                    UPDATE stock SET jumlah=%s
                                    WHERE item_id=%s AND rak=%s AND terakhir_update=%s
                                """, (qty_new, item_id, rak_pilih, tgl_pilih))
                                msg2 = f"Sisa stok: {qty_new}"

                            conn.commit()

                            st.success(
                                f"Stok item **{item_name}** di rak {rak_pilih} (batch {tgl_pilih}) dikurangi 1. {msg2}"
                            )

            except Exception:
                pass   # biar tidak spam error bawah

    else:
        st.error("Gagal membaca QR Code — pastikan kamera fokus & jelas.")
