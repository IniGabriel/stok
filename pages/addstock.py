import streamlit as st
import streamlit.components.v1 as components
import datetime
from db import get_conn
import psycopg2

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Auto Reader")
st.write("Arahkan kamera belakang ke barcode. Sistem akan membaca otomatis.")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

# ===========================================
# FIXED CAMERA SCANNER (AUTO BACK CAMERA)
# ===========================================

scanner_html = """
<script src="https://unpkg.com/html5-qrcode"></script>

<div id="reader" style="width:100%; border-radius:10px;"></div>

<script>
async function startScanner() {
    const videoDevices = (await navigator.mediaDevices.enumerateDevices())
        .filter(device => device.kind === "videoinput");

    // Cari kamera belakang
    let backCam = videoDevices.find(d => d.label.toLowerCase().includes("back"));

    const cameraId = backCam ? backCam.deviceId : videoDevices[0].deviceId;

    const html5Qr = new Html5Qrcode("reader");

    html5Qr.start(
        cameraId,
        {
            fps: 10,
            qrbox: function(viewfinderWidth, viewfinderHeight) {
                let min = Math.min(viewfinderWidth, viewfinderHeight);
                return { width: min * 0.7, height: min * 0.7 };
            }
        },
        (decodedText) => {
            window.parent.postMessage({barcode: decodedText}, "*");
        },
        (errorMessage) => {}
    );
}

startScanner();
</script>
"""

components.html(scanner_html, height=480)

# ===========================================
# RECEIVE BARCODE FROM JS → INPUT STREAMLIT
# ===========================================

st.markdown("""
<script>
window.addEventListener("message", (event) => {
    const bc = event.data.barcode;
    if (bc) {
        const box = window.parent.document.querySelector('input[id="barcode_input"]');
        box.value = bc;
        box.dispatchEvent(new Event('input', { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)


# ===========================================
# FORM TAMBAH STOK
# ===========================================

rak = st.text_input("Rak tujuan:", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok", type="primary"):
    barcode = barcode_value.strip()
    st.write(f"Memproses barcode: {barcode} ke rak {rak}...")

    if len(barcode) < 10:
        st.error("Barcode tidak valid.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            # QR format: 0101021125
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
