import bcrypt
from db import get_conn

# ==============================
# SET USERNAME & PASSWORD DI SINI
# ==============================
USERNAME = "admin"
PASSWORD = "Admin705Net"
# ==============================

def create_user():
    # hash password
    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO pengguna (username, password)
            VALUES (%s, %s)
        """, (USERNAME, password_hash))

        conn.commit()
        cur.close()
        conn.close()

        print(f"[SUCCESS] User '{USERNAME}' berhasil dibuat!")

    except Exception as e:
        if "duplicate key value" in str(e):
            print(f"[FAILED] Username '{USERNAME}' sudah ada!")
        else:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    create_user()
