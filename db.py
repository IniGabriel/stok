import psycopg2
import streamlit as st

DB_CONFIG = {
    "host": st.secrets["db_host"],
    "dbname": st.secrets["db_dbname"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
    "port": st.secrets["db_port"]
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)