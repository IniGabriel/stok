import streamlit as st
from db import get_conn
import datetime

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Browser Live Scanner (HTML5)")
st.write("Gunakan kamera HP / Laptop untuk memindai barcode.")

barcode_value = st.text_input("Barcode terbaca:", key="barcode_input")

# =========================================================
# 1. CAMERA SCANNER (HTML5 WORKING)
# =========================================================

st.subheader("📸 Kamera Barcode Scanner (Working)")

scanner_html = """
<div id="reader" style="width:100%; min-height:350px;"></div>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
function onScanSuccess(decodedText, decodedResult) {
    window.parent.postMessage({barcode: decodedText}, "*");
}

function onScanFailure(error) {}

let html5Qr = new Html5Qrcode("reader");

Html5Qrcode.getCameras().then(cameras => {
    let camId = cameras.length > 1 ? cameras[1].id : cameras[0].id;

    html5Qr.start(
        camId,
        { fps: 12, qrbox: 250 },
        onScanSuccess,
        onScanFailure
    );
});
</script>
"""

st.components.v1.html(scanner_html, height=420)

# RECEIVE BARCODE FROM JS
st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.barcode) {
        const inp = window.parent.document.querySelector('input[id="barcode_input"]');
        inp.value = event.data.barcode;
        inp.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)

# =========================================================
# 2. SIMPAN STOK
# =========================================================

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

            # sesuai format barcode kamu: 0101021125
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
