import streamlit as st
import streamlit.components.v1 as components
from db import get_conn
import psycopg2
import datetime
import base64

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Auto Reader")
st.write("Gunakan kamera atau upload foto barcode.")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

st.markdown("---")
st.subheader("📸 Scan Pakai Kamera")

# ======================
# Kamera Scanner (JS)
# ======================

camera_js = """
<script src="https://unpkg.com/@zxing/browser@latest"></script>

<div id="camera" style="width:100%; border-radius:10px; overflow:hidden;"></div>

<script>
async function startCam() {
    const codeReader = new ZXingBrowser.BrowserMultiFormatReader();
    const cams = await ZXingBrowser.BrowserCodeReader.listVideoInputDevices();

    let backCam = cams.find(c => c.label.toLowerCase().includes("back"));
    let selected = backCam ? backCam.deviceId : cams[0].deviceId;

    codeReader.decodeFromVideoDevice(selected, "camera", (result, err) => {
        if (result) {
            window.parent.postMessage({barcode: result.text}, "*");
        }
    });
}
startCam();
</script>
"""

components.html(camera_js, height=400)

# terima data dari JS
st.markdown("""
<script>
window.addEventListener("message", (event) => {
    const bc = event.data.barcode;
    if (bc) {
        const i = window.parent.document.querySelector('input[id="barcode_input"]');
        i.value = bc;
        i.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)

st.markdown("---")

# ======================
# Upload Gambar ZXing
# ======================

st.subheader("🖼 Upload Foto Barcode")

uploaded = st.file_uploader("Upload file barcode", type=["jpg", "jpeg", "png"])

if uploaded:
    data = base64.b64encode(uploaded.read()).decode("utf-8")

    decode_js = f"""
    <script src="https://unpkg.com/@zxing/browser@latest"></script>
    <img id="img" src="data:image/png;base64,{data}" style="display:none" />

    <script>
    setTimeout(async () => {{
        const codeReader = new ZXingBrowser.BrowserMultiFormatReader();
        const img = document.getElementById("img");

        try {{
            const result = await codeReader.decodeFromImageElement(img);
            window.parent.postMessage({{barcode: result.text}}, "*");
        }} catch (e) {{
            window.parent.postMessage({{barcode: ""}}, "*");
        }}
    }}, 500);
    </script>
    """

    components.html(decode_js, height=1)

st.markdown("---")
st.subheader("📦 Tambah Stok")


# ======================
# Simpan ke Database
# ======================

rak = st.text_input("Rak tujuan", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()

    if len(bc) < 10:
        st.error("Barcode tidak valid.")
        st.write(bc)
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
            s = cur.fetchone()

            if s:
                jumlah = s[0] + 1
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
            st.error(e)
