import streamlit as st
import streamlit.components.v1 as components
import datetime
from db import get_conn
import psycopg2

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Auto Reader")
st.write("Arahkan kamera belakang ke barcode. Sistem akan membaca otomatis.")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

# ============================
# CAMERA + BARCODE SCANNER JS
# ============================

scanner_html = """
<html>
<head>
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
#reader {
    width: 100%;
    height: 450px;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
}

/* Paksa kamera full width */
html5-qrcode-video {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
}

/* Atur qrbox supaya selalu di tengah */
#reader__scan_region {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
</style>

</head>
<body>

<div id="reader"></div>

<script>
function onScanSuccess(decodedText, decodedResult) {
    const message = {barcode: decodedText};
    window.parent.postMessage(message, "*");
}

function onScanFailure(error) {}

let html5QrcodeScanner = new Html5QrcodeScanner(
    "reader",
    {
        fps: 12,
        qrbox: { width: 250, height: 150 },
        aspectRatio: 1.777 // 16:9
    },
    false
);
html5QrcodeScanner.render(onScanSuccess, onScanFailure);
</script>

</body>
</html>
"""


components.html(scanner_html, height=500)

# ============================
# RECEIVE BARCODE FROM JS
# ============================

st.markdown("""
<script>
window.addEventListener("message", (event) => {
    const barcode = event.data.barcode;
    if (barcode) {
        const inputBox = window.parent.document.querySelector('input[id="barcode_input"]');
        inputBox.value = barcode;
        inputBox.dispatchEvent(new Event('input', { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)


# ============================
# FORM TAMBAH STOK
# ============================

rak = st.text_input("Rak tujuan:", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok", type="primary"):
    barcode = barcode_value.strip()

    if len(barcode) < 10:
        st.error("Barcode tidak valid.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = barcode[:4]
            date_code = barcode[4:10]

            day = int(date_code[:2])
            month = int(date_code[2:4])
            year = 2000 + int(date_code[4:6])

            tanggal_update = datetime.date(year, month, day).strftime("%d %b %Y")

            cur.execute("SELECT item_id FROM items WHERE barcode=%s", (item_code,))
            item = cur.fetchone()

            if item:
                item_id = item[0]
            else:
                cur.execute("""
                    INSERT INTO items (barcode, nama_barang)
                    VALUES (%s, %s)
                    RETURNING item_id
                """, (item_code, f"Item {item_code}"))
                item_id = cur.fetchone()[0]

            cur.execute("SELECT jumlah FROM stock WHERE item_id=%s", (item_id,))
            stok = cur.fetchone()

            if stok:
                jumlah = stok[0] + 1
                cur.execute("""
                    UPDATE stock SET jumlah=%s, rak=%s, terakhir_update=%s
                    WHERE item_id=%s
                """, (jumlah, rak, tanggal_update, item_id))
            else:
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, rak, 1, tanggal_update))

            conn.commit()
            cur.close()
            conn.close()

            st.success(f"Stok item {item_code} berhasil ditambahkan!")

        except Exception as e:
            st.error(f"Error: {e}")
