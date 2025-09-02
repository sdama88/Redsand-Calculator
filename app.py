import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os

st.set_page_config(page_title="Redsand Partner Portal", layout="wide")
ADMIN_EMAIL = "sdama@redsand.ai"

@st.cache_data
def load_data():
    workloads = pd.read_csv("workloads.csv")
    upgrade_rules = pd.read_csv("gpu_upgrade_rules.csv")
    pricing = pd.read_csv("pricing.csv")
    configs = pd.read_csv("redbox_configs.csv")
    credentials = pd.read_csv("partner_credentials.csv")
    return workloads, upgrade_rules, pricing, configs, credentials

workloads, upgrade_rules, pricing, configs, credentials = load_data()

if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False
if "admin" not in st.session_state:
    st.session_state['admin'] = False

st.title("🔐 Redsand Partner Portal")
col1, col2 = st.columns(2)
with col1:
    login_input = st.text_input("Partner Code or Admin Email").strip().lower()
with col2:
    password_input = st.text_input("Password", type="password")

if st.button("Login"):
    if login_input == ADMIN_EMAIL.lower():
        st.session_state['admin'] = True
        st.session_state['logged_in'] = True
        st.success("Admin logged in.")
    else:
        match = credentials[credentials['partner_code'].str.lower() == login_input]
        if not match.empty:
            stored_password = match.iloc[0]['password']
            if password_input == stored_password:
                st.session_state['partner_name'] = match.iloc[0]['partner_name']
                st.session_state['partner_code'] = match.iloc[0]['partner_code']
                st.session_state['admin'] = False
                st.session_state['logged_in'] = True
                st.success(f"Welcome {st.session_state['partner_name']}!")
            else:
                st.error("Incorrect password for partner.")
        else:
            st.error("Invalid partner code.")

if st.session_state['logged_in']:
    st.info("Session active")
    st.write("Admin:", st.session_state['admin'])
    if not st.session_state['admin']:
        st.write("Partner:", st.session_state.get('partner_name'))

# ...rest of app logic continues...
