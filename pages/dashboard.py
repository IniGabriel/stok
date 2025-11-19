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
search = st.text_input("Cari barang (nama/barcode/rak):", value="",
                       placeholder="misal: H705 / 0101 / 3")

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

    # FILTER MODE
    if search_button and search.strip() != "":
        query = f"""
            SELECT 
                s.stock_id,
                s.item_id,
                i.barcode,
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
        # FULL MODE
        query = """
            SELECT 
                s.stock_id,
                s.item_id,
                i.barcode,
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
        "stock_id", "item_id", "barcode", "nama_barang",
        "rak", "jumlah", "updated_at"
    ])

    df = df.drop(columns=["stock_id", "item_id"])
    df.index = range(1, len(df) + 1)

    st.dataframe(df, use_container_width=True)

    # ==============================================
    # DELETE STOK PER RAK
    # ==============================================
    st.markdown("### 🗑 Hapus Stok Barang")

    cur.execute("SELECT item_id, nama_barang FROM items ORDER BY nama_barang")
    item_rows = cur.fetchall()

    if item_rows:

        # Mapping nama → item_id
        item_dict = {row[1]: row[0] for row in item_rows}

        pilihan = st.selectbox(
            "Pilih item yang akan dihapus stoknya:",
            options=list(item_dict.keys()),
            key="item_delete_select"
        )

        item_name_selected = pilihan
        item_id_selected = item_dict[pilihan]

        # Ambil rak item itu
        cur.execute("SELECT rak FROM stock WHERE item_id = %s ORDER BY rak",
                    (item_id_selected,))
        rak_list = [r[0] for r in cur.fetchall()]

        if not rak_list:
            st.info("Item ini tidak punya stok di rak mana pun.")

        else:
            if st.button("Hapus Stok", use_container_width=True, key="hapus_stok_btn"):
                st.session_state.delete_item = item_id_selected

            # POPUP DELETE
            if "delete_item" in st.session_state and st.session_state.delete_item == item_id_selected:
                st.warning(
                    f"Item **{item_name_selected}** ditemukan di rak: "
                    f"**{', '.join(rak_list)}**"
                )

                rak_dipilih = st.selectbox(
                    "Pilih rak yang ingin dihapus stoknya:",
                    options=rak_list,
                    key="rak_delete_select"
                )

                colY, colN = st.columns(2)

                # YA
                with colY:
                    if st.button("✅ YA, Hapus Stok!", use_container_width=True):
                        cur.execute(
                            "DELETE FROM stock WHERE item_id=%s AND rak=%s",
                            (item_id_selected, rak_dipilih)
                        )
                        conn.commit()

                        st.success(
                            f"Stok item **{item_name_selected}** di rak **{rak_dipilih}** berhasil dihapus!"
                        )

                        del st.session_state.delete_item
                        time.sleep(1)
                        st.rerun()

                # BATAL
                with colN:
                    if st.button("❌ Batal", use_container_width=True):
                        del st.session_state.delete_item
                        st.rerun()

    else:
        st.info("Belum ada item.")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Terjadi error: {e}")
