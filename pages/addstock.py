import streamlit as st
import streamlit.components.v1 as components
from db import get_conn
import psycopg2
import datetime
from PIL import Image
from pyzbar.pyzbar import decode

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Auto Reader")
st.write("Gunakan kamera belakang atau upload foto barcode.")

# ===============================================
# INPUT BARCODE MANUAL
# ===============================================

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

st.markdown("---")

# ===============================================
# MODE 1 — SCAN DENGAN KAMERA
# ===============================================

st.subheader("📸 Scan Pakai Kamera")

scanner_html = """
<script src="https://unpkg.com/html5-qrcode"></script>

<div id="reader" style="width:100%; border-radius:10px;"></div>

<script>
async function startScanner() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const cams = devices.filter(d => d.kind === "videoinput");

        let backCam = cams.find(c => c.label.toLowerCase().includes("back"));
        let useCam = backCam ? backCam.deviceId : (cams[0]?.deviceId || null);

        if (!useCam) return;

        const qr = new Html5Qrcode("reader");

        qr.start(
            useCam,
            {
                fps: 10,
                qrbox: function(w, h){
                    let min = Math.min(w, h);
                    return { width: min * 0.7, height: min * 0.7 };
                }
            },
            (decodedText) => {
                window.parent.postMessage({barcode: decodedText}, "*");
            },
            (error) => {}
        );
    } catch (e) {
        console.log("Camera failed:", e);
    }
}
startScanner();
</script>
"""

components.html(scanner_html, height=480)

# Terima hasil scan JS → ke input Streamlit
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

st.markdown("---")

# ===============================================
# MODE 2 — UPLOAD FOTO (BACKUP)
# ===============================================

st.subheader("🖼 Upload Foto Barcode (Backup)")

uploaded = st.file_uploader("Upload gambar barcode", type=["jpg","jpeg","png"])

if uploaded:
    img = Image.open(uploaded)
    results = decode(img)

    if len(results) == 0:
        st.error("Barcode tidak terbaca dari gambar.")
    else:
        bc = results[0].data.decode("utf-8")
        st.success(f"Barcode terbaca: **{bc}**")

        # Masukkan ke input Streamlit
        st.session_state["barcode_input"] = bc


# ===============================================
# PROSES UPDATE STOK
# ===============================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan:", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok", type="primary"):
    barcode = barcode_value.strip()

    if len(barcode) < 10:
        st.error("Barcode tidak valid (minimal 10 digit).")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            # Format barcode: 0101021125
            item_code = barcode[:4]         # 0101
            date_code = barcode[4:10]       # 021125

            # Parse tanggal
            day = int(date_code[:2])
            month = int(date_code[2:4])
            year = 2000 + int(date_code[4:6])

            tanggal_update = datetime.date(year, month, day).strftime("%d %b %Y")

            # Cek item
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

            # Cek stock
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
