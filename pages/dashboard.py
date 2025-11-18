import streamlit as st
import pandas as pd
import time
from db import get_conn

st.set_page_config(page_title="Dashboard", page_icon="🏠", layout="wide")

# LOGIN CEK
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.warning("Silakan login terlebih dahulu.")
    time.sleep(2)
    st.switch_page("home.py")

# ============================
# HEADER
# ============================
col1, col2 = st.columns([6, 1])
with col1:
    st.markdown(
        f"<h2>🏠 Dashboard</h2>Selamat datang, <b>{st.session_state.username}</b>!",
        unsafe_allow_html=True
    )
with col2:
    if st.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.switch_page("home.py")

st.markdown("---")

st.subheader("📦 Stok Barang Per Rak")


# ============================
# SEARCH BAR
# ============================
search = st.text_input("Cari barang (nama/barcode/rak):", value="", placeholder="misal: H705 / 0101 / 3")

colA, colB = st.columns([1, 1])
with colA:
    search_button = st.button("🔎 Search", use_container_width=True)
with colB:
    reset_button = st.button("🔙 Reset", use_container_width=True)


# ============================
# QUERY DATABASE
# ============================
try:
    conn = get_conn()
    cur = conn.cursor()

    # --- FILTER MODE ---
    if search_button and search.strip() != "":
        query = f"""
            SELECT 
                s.stock_id,
                s.item_id,
                i.nama_barang,
                s.rak,
                s.jumlah,
                s.terakhir_update
            FROM stock s
            LEFT JOIN items i ON s.item_id = i.item_id
            WHERE 
                LOWER(i.nama_barang) LIKE LOWER('%{search}%')
                OR LOWER(i.barcode) LIKE LOWER('%{search}%')
                OR LOWER(s.rak) LIKE LOWER('%{search}%')
            ORDER BY s.item_id ASC;
        """
    else:
        # --- FULL MODE ---
        query = """
            SELECT 
                s.stock_id,
                s.item_id,
                i.nama_barang,
                s.rak,
                s.jumlah,
                s.terakhir_update
            FROM stock s
            LEFT JOIN items i ON s.item_id = i.item_id
            ORDER BY s.item_id ASC;
        """

    cur.execute(query)
    rows = cur.fetchall()

    df = pd.DataFrame(rows, columns=[
        "stock_id", "item_id", "nama_barang",
         "rak", "jumlah", "updated_at"
    ])

    # Buang kolom ID
    df = df.drop(columns=["stock_id", "item_id"])

    # Index mulai dari 1
    df.index = range(1, len(df) + 1)

    st.dataframe(df, use_container_width=True)

    # ==============================================
    # DELETE ITEM (WITH CONFIRMATION)
    # ==============================================
    st.markdown("### 🗑 Hapus Item")

    # Ambil list item
    cur.execute("SELECT item_id, nama_barang FROM items ORDER BY item_id")
    item_rows = cur.fetchall()

    if item_rows:
        pilihan = st.selectbox(
            "Pilih item yang akan dihapus:",
            options=[f"{row[0]} - {row[1]}" for row in item_rows]
        )

        # Tombol hapus → tampilkan konfirmasi
        if st.button("Hapus Item Ini", type="primary", use_container_width=True):
            st.session_state.delete_target = pilihan

        # Tampilkan konfirmasi jika state aktif
        if "delete_target" in st.session_state and st.session_state.delete_target == pilihan:

            st.warning(
                f"⚠ Yakin ingin menghapus **{pilihan}**?\n"
                f"Tindakan ini tidak dapat dibatalkan."
            )

            colY, colN = st.columns(2)

            with colY:
                if st.button("✅ YA, Hapus!", use_container_width=True):
                    item_id_to_delete = int(pilihan.split(" - ")[0])
                    cur.execute("DELETE FROM items WHERE item_id = %s", (item_id_to_delete,))
                    conn.commit()

                    del st.session_state.delete_target
                    st.success(f"Item '{pilihan}' berhasil dihapus!")
                    time.sleep(1)
                    st.rerun()

            with colN:
                if st.button("❌ Batal", use_container_width=True):
                    # Hapus state & refresh halaman
                    del st.session_state.delete_target
                    st.rerun()

    else:
        st.info("Belum ada item untuk dihapus.")


    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Terjadi error: {e}")
