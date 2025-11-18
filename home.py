import streamlit as st
import bcrypt
from db import get_conn

st.set_page_config(page_title="Login", page_icon="🔐")

# BUAT SESSION LOGIN
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None


# ============================
# JIKA SUDAH LOGIN → PINDAH KE DASHBOARD
# ============================
if st.session_state.logged_in:
    st.switch_page("pages/dashboard.py")


st.title("🔐 Login Pengguna")

username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username == "" or password == "":
        st.error("Username dan password wajib diisi!")
    else:
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT id, username, password FROM pengguna WHERE username=%s", (username,))
            user = cur.fetchone()

            cur.close()
            conn.close()

            if user is None:
                st.error("❌ Username tidak ditemukan.")

            else:
                user_id, user_name, stored_hash = user

                if bcrypt.checkpw(password.encode(), stored_hash.encode()):
                    st.success("✔ Login berhasil!")
                    st.session_state.logged_in = True
                    st.session_state.username = user_name
                    st.switch_page("pages/dashboard.py")
                else:
                    st.error("❌ Username atau Password Salah.")

        except Exception as e:
            st.error(f"Database error: {e}")
