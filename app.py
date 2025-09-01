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
    login_input = st.text_input("Partner Code or Admin Email")
with col2:
    password_input = st.text_input("Password", type="password")

if st.button("Login"):
    if login_input == ADMIN_EMAIL:
        st.session_state['admin'] = True
        st.session_state['logged_in'] = True
    else:
        match = credentials[(credentials['partner_code'] == login_input) & (credentials['password'] == password_input)]
        if not match.empty:
            st.session_state['partner_name'] = match.iloc[0]['partner_name']
            st.session_state['partner_code'] = match.iloc[0]['partner_code']
            st.session_state['admin'] = False
            st.session_state['logged_in'] = True
        else:
            st.error("Invalid partner code or password.")
def log_config(partner_code, partner_name, mode, use_case, config, gpu_type, qty, monthly, yearly, total_3yr, pdf_file):
    now = datetime.now()
    log_row = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "partner_code": partner_code,
        "partner_name": partner_name,
        "mode": mode,
        "use_case_or_selection": use_case,
        "configuration": config,
        "gpu_type": gpu_type,
        "quantity": qty,
        "monthly": monthly,
        "yearly": yearly,
        "three_year_total": total_3yr,
        "pdf_file": pdf_file
    }
    try:
        log_df = pd.read_csv("config_log.csv")
        log_df = pd.concat([log_df, pd.DataFrame([log_row])], ignore_index=True)
    except FileNotFoundError:
        log_df = pd.DataFrame([log_row])
    log_df.to_csv("config_log.csv", index=False)

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

            # Fully override logic for Voicebot
            if use_case == "Voicebot":
                selected_config = "RedBox Voice"
                config_row = configs[configs["configuration_name"] == selected_config].iloc[0]
                final_gpu = config_row["gpu_type"]
                workload_row = workloads[workloads["workload_name"] == use_case].iloc[0]
                users_per_box = workload_row["users_per_gpu"]
                num_boxes = max(1, int(users / users_per_box))

                # DEBUG LOGGING for verification
                st.warning(f"[DEBUG] VOICEBOT SELECTED")
                st.warning(f"[DEBUG] Config: {selected_config}")
                st.warning(f"[DEBUG] GPU: {final_gpu}")
                st.warning(f"[DEBUG] Users per Box: {users_per_box}")
                st.warning(f"[DEBUG] Boxes Needed: {num_boxes}")
            else:
                workload_row = workloads[workloads["workload_name"] == use_case].iloc[0]
                base_gpu = workload_row["gpu_type"]
                users_per_box = workload_row["users_per_gpu"]
                num_boxes = max(1, int(users / users_per_box))

                upgrade = upgrade_rules[(upgrade_rules["current_gpu"] == base_gpu) & (users >= upgrade_rules["user_threshold"])]
                final_gpu = upgrade.iloc[0]["upgrade_gpu"] if not upgrade.empty else base_gpu

                matching_configs = configs[configs["gpu_type"] == final_gpu]
                if matching_configs.empty:
                    st.error(f"No configuration available for GPU type {final_gpu}.")
                    st.stop()
                selected_config = matching_configs.iloc[0]["configuration_name"]

            price_row = pricing[pricing["configuration_name"] == selected_config]
            if price_row.empty:
                st.error(f"No pricing found for {selected_config}.")
            else:
                price_per_box = price_row["monthly_price_usd"].values[0]
                monthly = price_per_box * num_boxes
                yearly = monthly * 12
                total_3yr = yearly * 3

                st.success("Configuration Recommended")
                st.write(f"**Configuration:** {selected_config}")
                st.write(f"**GPU Type:** {final_gpu}")
                st.write(f"**Boxes Needed:** {num_boxes}")
                st.metric("💰 Monthly", f"${monthly:,.0f}")
                st.metric("📅 Yearly", f"${yearly:,.0f}")
                st.metric("🪙 3-Year Total", f"${total_3yr:,.0f}")

                filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                doc = SimpleDocTemplate(filename, pagesize=A4)
                styles = getSampleStyleSheet()
                story = [Paragraph("Redsand Partner Configuration Summary", styles['Title']), Spacer(1, 12)]

                data = [
                    ["Partner", st.session_state['partner_name']],
                    ["Use Case", use_case],
                    ["GPU Type", final_gpu],
                    ["Boxes Needed", num_boxes],
                    ["Configuration", selected_config],
                    ["Monthly Cost", f"${monthly:,.0f}"],
                    ["Yearly Cost", f"${yearly:,.0f}"],
                    ["3-Year Total", f"${total_3yr:,.0f}"]
                ]
                table = Table(data, hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ]))
                story.append(table)
                doc.build(story)

                with open(filename, "rb") as f:
                    st.download_button("📄 Download PDF", f, file_name=filename)

                log_config(st.session_state['partner_code'], st.session_state['partner_name'], "Auto", use_case, selected_config, final_gpu, num_boxes, monthly, yearly, total_3yr, filename)

        elif mode == "✋ Manual Selection":
            selected_config = st.selectbox("Choose Configuration", configs["configuration_name"].unique())
            quantity = st.number_input("Quantity", min_value=1, step=1)
            price_row = pricing[pricing["configuration_name"] == selected_config]
            if price_row.empty:
                st.error(f"No pricing found for {selected_config}.")
            else:
                price_per_box = price_row["monthly_price_usd"].values[0]
                monthly = price_per_box * quantity
                yearly = monthly * 12
                total_3yr = yearly * 3

                st.success("Manual Configuration Selected")
                st.write(f"**Configuration:** {selected_config}")
                st.write(f"**Quantity:** {quantity}")
                st.metric("💰 Monthly", f"${monthly:,.0f}")
                st.metric("📅 Yearly", f"${yearly:,.0f}")
                st.metric("🪙 3-Year Total", f"${total_3yr:,.0f}")

                filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                doc = SimpleDocTemplate(filename, pagesize=A4)
                styles = getSampleStyleSheet()
                story = [Paragraph("Redsand Partner Configuration Summary", styles['Title']), Spacer(1, 12)]

                data = [
                    ["Partner", st.session_state['partner_name']],
                    ["Manual Selection", selected_config],
                    ["Quantity", quantity],
                    ["Monthly Cost", f"${monthly:,.0f}"],
                    ["Yearly Cost", f"${yearly:,.0f}"],
                    ["3-Year Total", f"${total_3yr:,.0f}"]
                ]
                table = Table(data, hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ]))
                story.append(table)
                doc.build(story)

                with open(filename, "rb") as f:
                    st.download_button("📄 Download PDF", f, file_name=filename)

                log_config(st.session_state['partner_code'], st.session_state['partner_name'], "Manual", "Manual", selected_config, "", quantity, monthly, yearly, total_3yr, filename)
