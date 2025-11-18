import streamlit as st
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import datetime
from db import get_conn
import base64
import psycopg2

st.set_page_config(page_title="Scan Barcode", page_icon="📷")

st.title("📷 Scan Barcode – Live Scanner (OpenCV Style)")

barcode_value = st.text_input("Barcode Terbaca:", key="barcode_input")

st.markdown("""
<style>
#camera-box {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

st.subheader("📸 Live Scan (Webcam)")

# =========================================================
#  CAMERA STREAM → SEND FRAMES TO PYTHON
# =========================================================

frame_placeholder = st.empty()

# JS membaca camera, mengirim base64 frame ke Streamlit
st.markdown("""
<script>
let video = document.createElement('video');
video.setAttribute('playsinline', ''); // iPhone fix
video.setAttribute('autoplay', '');
video.setAttribute('muted', '');
video.style.width = "100%";

navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
});

let canvas = document.createElement('canvas');
let ctx = canvas.getContext('2d');

setInterval(() => {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    let dataURL = canvas.toDataURL('image/jpeg');
    window.parent.postMessage({frame: dataURL}, "*");

}, 300); // 300ms per frame
</script>
""", unsafe_allow_html=True)


# Streamlit menerima frame
st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.frame) {
        const i = window.parent.document.querySelector('input[id="frame_input"]');
        i.value = event.data.frame;
        i.dispatchEvent(new Event("input", { bubbles: true }));
    }
});
</script>
""", unsafe_allow_html=True)

frame_input = st.text_input("frame_input", key="frame_input", label_visibility="hidden")


# =========================================================
# DECODE FRAME USING PYZBAR + OPENCV
# =========================================================

if frame_input.startswith("data:image"):
    # Remove header base64
    frame_bytes = base64.b64decode(frame_input.split(",")[1])
    frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

    detected = decode(frame)

    if detected:
        barcode = detected[0].data.decode()

        # draw rectangle
        for d in detected:
            x, y, w, h = d.rect
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)

        # update UI text
        barcode_value = barcode
        st.session_state["barcode_input"] = barcode

    frame_placeholder.image(frame, channels="BGR")


# =========================================================
#  SIMPAN STOK
# =========================================================

st.markdown("---")
st.subheader("📦 Tambah Stok")

rak = st.text_input("Rak tujuan:", placeholder="misal: 3")

if st.button("➕ Tambahkan Stok"):
    bc = barcode_value.strip()
    st.write("Barcode terbaca =", bc)

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
