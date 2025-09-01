
import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Redsand Partner Portal", layout="wide")
ADMIN_EMAIL = "sdama@redsand.ai"

@st.cache_data
def load_data():
    workloads = pd.read_csv("workloads.csv")
    upgrade_rules = pd.read_csv("gpu_upgrade_rules.csv")
    pricing = pd.read_csv("pricing.csv")
    configs = pd.read_csv("redbox_configs.csv")
    partners = pd.read_csv("partner_codes.csv")
    return workloads, upgrade_rules, pricing, configs, partners

workloads, upgrade_rules, pricing, configs, partners = load_data()

if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False
if "admin" not in st.session_state:
    st.session_state['admin'] = False

st.title("🔐 Redsand Partner Portal")
login_input = st.text_input("Enter your Partner Code or Admin Email", type="password")
if st.button("Login"):
    if login_input == ADMIN_EMAIL:
        st.session_state['admin'] = True
        st.session_state['logged_in'] = True
    elif login_input in partners['partner_code'].values:
        st.session_state['partner_name'] = partners.loc[partners['partner_code'] == login_input, 'partner_name'].values[0]
        st.session_state['partner_code'] = login_input
        st.session_state['admin'] = False
        st.session_state['logged_in'] = True
    else:
        st.error("Invalid login. Try again.")

if st.session_state['logged_in']:
    if st.session_state['admin']:
        st.subheader("🔧 Admin Panel")
        try:
            logs = pd.read_csv("config_log.csv")
            st.dataframe(logs)
            st.download_button("Download All Logs", logs.to_csv(index=False), file_name="config_log.csv")
        except FileNotFoundError:
            st.info("No configuration logs found yet.")
    else:
        st.subheader(f"Welcome, {st.session_state['partner_name']}")
        mode = st.radio("Choose Mode", ["🔍 Use Case Recommendation", "✋ Manual Selection"])

        if mode == "🔍 Use Case Recommendation":
            use_case = st.selectbox("Select Use Case", workloads['workload_name'].unique())
            users = st.number_input("Number of Concurrent Users", min_value=1, step=1)

            row = workloads[workloads["workload_name"] == use_case].iloc[0]
            gpu_type = row["gpu_type"]
            users_per_box = row["users_per_gpu"]
            num_boxes = max(1, int(users / users_per_box))

            # Apply upgrade logic if needed
            upgrade = upgrade_rules[
                (upgrade_rules["current_gpu"] == gpu_type) & (users >= upgrade_rules["user_threshold"])
            ]
            if not upgrade.empty:
                gpu_type = upgrade.iloc[0]["upgrade_gpu"]

            # Find matching configuration
            config_match = configs[configs["gpu_type"] == gpu_type]
            if config_match.empty:
                st.error(f"No RedBox configuration found for GPU type {gpu_type}.")
            else:
                selected_config = config_match.iloc[0]["configuration_name"]
                price_per_box = pricing[pricing["configuration_name"] == selected_config]["monthly_price_usd"].values[0]
                monthly = price_per_box * num_boxes
                yearly = monthly * 12
                total_3yr = yearly * 3

                st.success("Configuration Recommended")
                st.write(f"**Configuration:** {selected_config}")
                st.write(f"**GPU Type:** {gpu_type}")
                st.write(f"**Boxes Needed:** {num_boxes}")
                st.metric("💰 Monthly", f"${monthly:,.0f}")
                st.metric("📅 Yearly", f"${yearly:,.0f}")
                st.metric("🪙 3-Year Total", f"${total_3yr:,.0f}")

        elif mode == "✋ Manual Selection":
            selected_config = st.selectbox("Choose Configuration", configs["configuration_name"].unique())
            quantity = st.number_input("Quantity", min_value=1, step=1)
            price_per_box = pricing[pricing["configuration_name"] == selected_config]["monthly_price_usd"].values[0]
            monthly = price_per_box * quantity
            yearly = monthly * 12
            total_3yr = yearly * 3

            st.success("Manual Configuration Selected")
            st.write(f"**Configuration:** {selected_config}")
            st.write(f"**Quantity:** {quantity}")
            st.metric("💰 Monthly", f"${monthly:,.0f}")
            st.metric("📅 Yearly", f"${yearly:,.0f}")
            st.metric("🪙 3-Year Total", f"${total_3yr:,.0f}")
