import streamlit as st
import streamlit.components.v1 as components
from db import get_conn
import psycopg2
import datetime
import base64

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Ultra Reader")
st.write("Gunakan kamera Streamlit atau upload foto barcode. Sistem akan mencoba membaca otomatis.")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

# ============================================================
#  1. KAMERA STREAMLIT + QUAGGA2 (PALING AMAN & STABIL)
# ============================================================

st.markdown("---")
st.subheader("📸 Ambil Foto Barcode")

img = st.camera_input("Ambil foto barcode:")

if img:
    data = base64.b64encode(img.read()).decode()

    decode_js = f"""
    <script src="https://cdn.jsdelivr.net/npm/quagga@0.12.1/dist/quagga.min.js"></script>

    <img id="qrimg" src="data:image/png;base64,{data}" style="display:none">

    <script>
    function enhance(canvas, ctx, img) {{
        canvas.width = img.width * 2;
        canvas.height = img.height * 2;
        ctx.filter = "contrast(180%) brightness(120%)";
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    }}

    setTimeout(() => {{
        const img = document.getElementById("qrimg");
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        enhance(canvas, ctx, img);

        Quagga.decodeSingle(
            {{
                src: canvas.toDataURL(),
                numOfWorkers: 0,
                locate: true,
                inputStream: {{ size: 800 }},
                decoder: {{
                    readers: [
                        "qr_reader",
                        "datamatrix_reader",
                        "code_128_reader",
                        "code_39_reader",
                        "ean_reader"
                    ]
                }}
            }},
            function(result) {{
                if (result && result.codeResult) {{
                    window.parent.postMessage({{barcode: result.codeResult.code}}, "*");
                }} else {{
                    window.parent.postMessage({{barcode: ""}}, "*");
                }}
            }}
        );
    }}, 500);
    </script>
    """

    components.html(decode_js, height=1)


# ============================================================
#   2. TERIMA HASIL DECODE BARCODE
# ============================================================

st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.barcode !== undefined) {
        const target = window.parent.document.querySelector('input[id="barcode_input"]');
        target.value = event.data.barcode;
        target.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)


# ============================================================
#   3. UPLOAD FOTO BARCODE
# ============================================================

st.markdown("---")
st.subheader("🖼 Upload Foto Barcode")

uploaded = st.file_uploader("Upload gambar barcode", type=["png","jpg","jpeg"])

if uploaded:
    data = base64.b64encode(uploaded.read()).decode()

    decode_js = f"""
    <script src="https://cdn.jsdelivr.net/npm/quagga@0.12.1/dist/quagga.min.js"></script>
    <img id="upimg" src="data:image/png;base64,{data}" style="display:none" />

    <script>
    setTimeout(() => {{
        const img = document.getElementById("upimg");
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        canvas.width = img.width * 2;
        canvas.height = img.height * 2;

        ctx.filter = "contrast(180%) brightness(115%)";
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        Quagga.decodeSingle(
            {{
                src: canvas.toDataURL(),
                numOfWorkers: 0,
                locate: true,
                decoder: {{
                    readers: [
                        "qr_reader",
                        "datamatrix_reader",
                        "code_128_reader",
                        "code_39_reader",
                        "ean_reader"
                    ]
                }}
            }},
            function(result) {{
                if (result && result.codeResult) {{
                    window.parent.postMessage({{barcode: result.codeResult.code}}, "*");
                }} else {{
                    window.parent.postMessage({{barcode: ""}}, "*");
                }}
            }}
        );
    }}, 500);
    </script>
    """

    components.html(decode_js, height=1)



# ============================================================
#   4. SIMPAN KE DATABASE
# ============================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()

    st.write("Nilai BC =", bc)

    if len(bc) < 10:
        st.error("Barcode tidak valid atau gagal dibaca.")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            item_code = bc[:4]
            date_code = bc[4:10]

            day = int(date_code[:2])
            month = int(date_code[2:4])
            year = 2000 + int(date_code[4:6])

            tanggal = datetime.date(year, month, day).strftime("%d %b %Y")

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
                    UPDATE stock 
                    SET jumlah=%s, rak=%s, terakhir_update=%s
                    WHERE item_id=%s
                """, (jumlah, rak, tanggal, item_id))
            else:
                cur.execute("""
                    INSERT INTO stock (item_id, rak, jumlah, terakhir_update)
                    VALUES (%s, %s, %s, %s)
                """, (item_id, rak, 1, tanggal))

            conn.commit()
            st.success(f"Stok {item_code} berhasil ditambahkan!")

        except Exception as e:
            st.error(str(e))
