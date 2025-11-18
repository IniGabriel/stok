import streamlit as st
import streamlit.components.v1 as components
from db import get_conn
import psycopg2
import datetime
import base64

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Auto Reader")
st.write("Gunakan kamera Streamlit atau upload foto barcode.")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

st.markdown("---")
st.subheader("📸 Scan Menggunakan Kamera Streamlit (Paling Stabil)")

# ===========================
# Kamera Streamlit (AMAN)
# ===========================

img = st.camera_input("Ambil foto barcode:")

if img:
    # convert foto ke base64
    data = base64.b64encode(img.read()).decode()

    decode_js = f"""
    <script type="module">
    import {{ BrowserQRCodeReader }} from 
        "https://cdn.jsdelivr.net/npm/@zxing/library@0.19.1/esm/index.min.js";

    const img = document.createElement("img");
    img.src = "data:image/png;base64,{data}";
    img.style.display = "none";
    document.body.appendChild(img);

    const reader = new BrowserQRCodeReader();

    async function tryDecode() {{
        for (let i = 0; i < 5; i++) {{
            try {{
                const res = await reader.decodeFromImageElement(img);
                window.parent.postMessage({{barcode: res.getText()}}, "*");
                return;
            }} catch (e) {{
                await new Promise(r => setTimeout(r, 150)); 
            }}
        }}
        window.parent.postMessage({{barcode: ""}}, "*");
    }}

    // tunggu gambar load
    setTimeout(() => tryDecode(), 300);
    </script>
    """

    components.html(decode_js, height=1)



# Terima hasil decode
st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.barcode) {
        const box = window.parent.document.querySelector('input[id="barcode_input"]');
        box.value = event.data.barcode;
        box.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)

# ===========================
# Upload Foto
# ===========================

st.markdown("---")
st.subheader("🖼 Upload Foto Barcode")

uploaded = st.file_uploader("Upload gambar barcode", type=["png","jpg","jpeg"])

if uploaded:
    data = base64.b64encode(uploaded.read()).decode()

    decode_js = f"""
    <script src="https://unpkg.com/@zxing/browser@latest"></script>
    <img id="img" src="data:image/png;base64,{data}" style="display:none" />

    <script>
    setTimeout(async () => {{
        const reader = new ZXingBrowser.BrowserMultiFormatReader();
        const img = document.getElementById("img");

        try {{
            const res = await reader.decodeFromImageElement(img);
            window.parent.postMessage({{barcode: res.text}}, "*");
        }} catch (e) {{
            window.parent.postMessage({{barcode: ""}}, "*");
        }}
    }}, 300);
    </script>
    """

    components.html(decode_js, height=1)

# ===========================
# Simpan ke Database
# ===========================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()
    st.write("Niali bc = ",bc)

    if len(bc) < 10:
        st.error("Barcode tidak valid.")
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
                    UPDATE stock SET jumlah=%s, rak=%s, terakhir_update=%s
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
