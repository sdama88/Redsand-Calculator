
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Redsand Partner Portal", layout="wide")

# Load data
@st.cache_data
def load_data():
    gpu_specs = pd.read_excel("Redsand_Calculator_Backend_Template.xlsx", sheet_name="gpu_specs")
    prebuilt_configs = pd.read_excel("Redsand_Calculator_Backend_Template.xlsx", sheet_name="prebuilt_configs")
    use_cases = pd.read_excel("Redsand_Calculator_Backend_Template.xlsx", sheet_name="use_cases")
    partner_codes = pd.read_excel("Redsand_Calculator_Backend_Template.xlsx", sheet_name="partner_codes")
    return gpu_specs, prebuilt_configs, use_cases, partner_codes

gpu_specs, prebuilt_configs, use_cases, partner_codes = load_data()

# Redsand logo
st.image("Redsand Logo_White.png", width=150)

# Login page
st.title("🔐 Redsand Partner Portal Login")
partner_code = st.text_input("Enter your Partner Access Code", type="password")
if st.button("Login"):
    if partner_code in partner_codes['code'].values:
        partner_name = partner_codes.loc[partner_codes['code'] == partner_code, 'partner_name'].values[0]
        st.session_state['logged_in'] = True
        st.session_state['partner_name'] = partner_name
        st.experimental_rerun()
    else:
        st.error("Invalid partner code. Please try again.")

# If logged in, show configurator (placeholder for now)
if st.session_state.get('logged_in'):
    st.success(f"Welcome, {st.session_state['partner_name']} 👋")
    st.subheader("🔧 Configuration Builder")
    st.write("This is where the multi-step configurator will go.")
