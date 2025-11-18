import streamlit as st
import streamlit.components.v1 as components
from db import get_conn
import datetime
import psycopg2

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Live Scanner (ZXing)")
st.write("Gunakan kamera HP untuk memindai barcode. Sistem membaca secara otomatis.")

barcode_value = st.text_input("Barcode terbaca:", key="barcode_input")

st.markdown("---")
st.subheader("📸 Kamera Barcode Scanner (ZXing JS)")

scanner_html = """
<div id="reader" style="width:100%; height:350px; border:2px solid #555; border-radius:10px;"></div>

<script src="https://unpkg.com/@zxing/browser@latest"></script>

<script>
async function startScanner() {
    const codeReader = new ZXingBrowser.BrowserMultiFormatReader();

    const devices = await ZXingBrowser.BrowserCodeReader.listVideoInputDevices();

    let backCam = devices.find(d => d.label.toLowerCase().includes("back"));
    let selected = backCam ? backCam.deviceId : devices[0].deviceId;

    codeReader.decodeFromVideoDevice(
        selected,
        "reader",
        (result, err) => {
            if (result) {
                window.parent.postMessage({barcode: result.text}, "*");
            }
        }
    );
}

startScanner();
</script>
"""

components.html(scanner_html, height=420)

st.markdown("""
<script>
window.addEventListener("message", (e) => {
    if (e.data.barcode) {
        const input = window.parent.document.querySelector('input[id="barcode_input"]');
        input.value = e.data.barcode;
        input.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)


# ===========================
# SIMPAN KE DATABASE
# ===========================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()
    st.write("Barcode =", bc)

    if len(bc) < 10:
        st.error("Barcode tidak valid!")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = bc[:4]
            date_code = bc[4:10]

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
            cek = cur.fetchone()

            if cek:
                jumlah = cek[0] + 1
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
            st.success(f"Stok item {item_code} berhasil ditambahkan!")

        except Exception as e:
            st.error(str(e))
