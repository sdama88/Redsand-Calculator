import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import os
import uuid

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

if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False
if "admin" not in st.session_state:
    st.session_state['admin'] = False
if "pdf_ready" not in st.session_state:
    st.session_state["pdf_ready"] = False
if "quote_id" not in st.session_state:
    st.session_state["quote_id"] = str(uuid.uuid4())[:8]

# ------------------ PDF GENERATOR ------------------
def generate_pdf(filename, summary_data, partner_name, quote_id):
    try:
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        title_style = styles['Title']
        title_style.fontSize = 18
        normal_style.fontSize = 11
        story = []

        logo_path = "Redsand Logo_White.png"
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=1.8*inch, preserveAspectRatio=True, mask='auto')
        else:
            logo = Paragraph("<b>Redsand.ai</b>", ParagraphStyle('fallbackLogo', fontSize=20, textColor=colors.HexColor("#d71920")))

        header = [[Paragraph("Redsand Partner Configuration Summary", title_style), logo]]
        ht = Table(header, colWidths=[4.5*inch, 1.8*inch])
        ht.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(ht)

        story.append(Spacer(1, 8))
        story.append(Paragraph(datetime.now().strftime("%A, %d %B %Y — %H:%M:%S"), normal_style))
        story.append(Paragraph(f"Quote ID: {quote_id}", normal_style))
        story.append(Paragraph(f"Partner: {partner_name}", normal_style))
        story.append(Spacer(1, 18))

        config_rows = [row for row in summary_data if row[0] in ["Use Case", "GPU Type", "Configuration", "Units"]]
        pricing_rows = [row for row in summary_data if "Cost" in row[0] or "Total" in row[0]]

        if config_rows:
            story.append(Paragraph("Configuration Details", ParagraphStyle('Heading', fontSize=12, textColor=colors.black, spaceAfter=6)))
            config_table = Table([["Field", "Value"]] + config_rows, hAlign='LEFT', colWidths=[150, 300])
            config_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey)
            ]))
            story.append(config_table)
            story.append(Spacer(1, 18))

        if pricing_rows:
            story.append(Paragraph("Pricing Details", ParagraphStyle('Heading', fontSize=12, textColor=colors.black, spaceAfter=6)))
            pricing_table = Table([["Field", "Value"]] + pricing_rows, hAlign='LEFT', colWidths=[150, 300])
            pricing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey)
            ]))
            story.append(pricing_table)
            story.append(Spacer(1, 24))

        disclaimer = (
            "<b>Disclaimer:</b> The pricing provided in this summary is indicative only. "
            "Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, "
            "service-level agreements, hardware availability, and customer-specific requirements. "
            "Please contact Redsand at <b>hello@redsand.ai</b> for an official quote or custom configuration."
        )
        story.append(Paragraph(disclaimer, ParagraphStyle('Disclaimer', fontSize=9, textColor=colors.grey, leading=12)))

        doc.build(story)
    except Exception as e:
        st.error(f"PDF generation failed: {e}")

# ------------------ LOGIN PAGE ------------------
if st.session_state["page"] == "login":
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.title("🔐 Redsand Partner Portal")
    login_input = st.text_input("Partner Code or Admin Email")
    password_input = st.text_input("Password", type="password")

    if st.button("Login", key="login_btn"):
        if login_input == ADMIN_EMAIL:
            st.session_state['admin'] = True
            st.session_state['logged_in'] = True
            st.session_state["page"] = "welcome"
        else:
            match = credentials[(credentials['partner_code'] == login_input) & (credentials['password'] == password_input)]
            if not match.empty:
                st.session_state['partner_name'] = match.iloc[0]['partner_name']
                st.session_state['partner_code'] = match.iloc[0]['partner_code']
                st.session_state['admin'] = False
                st.session_state['logged_in'] = True
                st.session_state["page"] = "welcome"
            else:
                st.error("Invalid partner code or password.")

# ------------------ WELCOME PAGE ------------------
elif st.session_state["page"] == "welcome" and st.session_state.get("logged_in") and not st.session_state.get("admin"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader(f"🔐 Welcome, {st.session_state['partner_name']}")
    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.markdown("### 🚀 Start a New Quote")

        selected_mode = st.radio("Choose Mode", ["Auto (Recommended)", "Manual Selection"], key="quote_mode_selection")

        if "Auto" in selected_mode:
            selected_use_case = st.selectbox("Select Use Case", workloads["workload_name"].unique(), key="welcome_use_case")
            num_users = st.number_input("Number of Concurrent Users", min_value=1, step=1, key="welcome_users")

            if selected_use_case == "Voice Bot":
                config_row = configs[configs["configuration_name"] == "RedBox Voice"].iloc[0]
                preview_config = config_row["configuration_name"]
                preview_gpu = config_row["gpu_type"]
                users_per_unit = workloads[workloads["workload_name"] == selected_use_case].iloc[0]["users_per_gpu"]
                preview_units = max(1, int(num_users / users_per_unit))
            else:
                workload_row = workloads[workloads["workload_name"] == selected_use_case].iloc[0]
                base_gpu = workload_row["gpu_type"]
                users_per_unit = workload_row["users_per_gpu"]
                preview_units = max(1, int(num_users / users_per_unit))
                upgrade = upgrade_rules[(upgrade_rules["current_gpu"] == base_gpu) & (num_users >= upgrade_rules["user_threshold"])]
                preview_gpu = upgrade.iloc[0]["upgrade_gpu"] if not upgrade.empty else base_gpu
                matching_configs = configs[configs["gpu_type"] == preview_gpu]
                preview_config = matching_configs.iloc[0]["configuration_name"]

        else:
            preview_config = st.selectbox("Choose Configuration", configs["configuration_name"].unique(), key="manual_select")
            preview_units = st.number_input("Units", min_value=1, step=1, key="manual_qty")
            if not configs[configs["configuration_name"] == preview_config].empty:
                preview_gpu = configs[configs["configuration_name"] == preview_config].iloc[0]["gpu_type"]
            else:
                preview_gpu = "Unknown"

        st.markdown("#### 🔧 Configuration Preview")
        st.write(f"**Mode:** {selected_mode}")
        st.write(f"**Use Case:** {st.session_state.get('welcome_use_case', 'N/A') if 'Auto' in selected_mode else 'N/A'}")
        st.write(f"**GPU Type:** {preview_gpu}")
        st.write(f"**Configuration:** {preview_config}")
        st.write(f"**Units:** {preview_units}")

        st.session_state["preview_config"] = preview_config
        st.session_state["preview_gpu"] = preview_gpu
        st.session_state["preview_units"] = preview_units
        st.session_state["use_case"] = st.session_state.get("welcome_use_case", "Manual")
        st.session_state["quote_mode"] = "Auto" if "Auto" in selected_mode else "Manual"

        st.divider()
        nav1, nav2, nav3, nav4 = st.columns([1,1,1,1])
        with nav1:
            if st.button("🏠 Home", key="home_welcome"):
                st.session_state["page"] = "welcome"
        with nav2:
            if st.button("🔙 Back", key="back_welcome"):
                st.session_state["page"] = "welcome"
        with nav3:
            if st.button("➡️ Generate Quote", key="gen_quote"):
                st.session_state["page"] = "quote_summary"
        with nav4:
            if st.button("🔓 Logout", key="logout_welcome"):
                st.session_state.clear()
                st.experimental_rerun()

    with col_right:
        st.markdown("### 🔍 Compare Configurations")
        compare_configs = st.multiselect("Choose up to 3 configurations to compare", configs["configuration_name"].unique(), key="compare_configs_welcome")
        if compare_configs:
            compare_df = pricing[pricing["configuration_name"].isin(compare_configs)].merge(configs, on="configuration_name", how="left")
            st.dataframe(compare_df.set_index("configuration_name"))

        st.divider()
        st.markdown("### 📚 My Quote History")
        try:
            full_log = pd.read_csv("config_log.csv")
            partner_log = full_log[full_log['partner_code'] == st.session_state['partner_code']]
            if not partner_log.empty:
                st.dataframe(partner_log.sort_values("timestamp", ascending=False))
            else:
                st.info("No previous quotes found.")
        except FileNotFoundError:
            st.info("Quote log file not found.")

# ------------------ QUOTE SUMMARY PAGE ------------------
elif st.session_state["page"] == "quote_summary" and st.session_state.get("logged_in"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader("🧾 Quote Summary")

    use_case = st.session_state.get("use_case", "N/A")
    selected_config = st.session_state.get("preview_config", "N/A")
    final_gpu = st.session_state.get("preview_gpu", "N/A")
    num_units = st.session_state.get("preview_units", 0)
    quote_id = st.session_state["quote_id"]

    price_row = pricing[pricing["configuration_name"] == selected_config]
    if price_row.empty:
        st.error(f"No pricing found for {selected_config}.")
    else:
        price_per_unit = price_row["monthly_price_usd"].values[0]
        monthly = price_per_unit * num_units
        yearly = monthly * 12
        total_3yr = yearly * 3

        config_details = [
            ["Use Case", use_case],
            ["GPU Type", final_gpu],
            ["Configuration", selected_config],
            ["Units", num_units]
        ]

        pricing_details = [
            ["Monthly Cost", f"${monthly:,.0f}"],
            ["Yearly Cost", f"${yearly:,.0f}"],
            ["3-Year Total", f"${total_3yr:,.0f}"]
        ]

        st.markdown("### Configuration Details")
        st.table(config_details)

        st.markdown("### Pricing Details")
        st.table(pricing_details)

        st.markdown("<small><i>Disclaimer: The pricing provided in this summary is indicative only. Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, service-level agreements, hardware availability, and customer-specific requirements. Please contact Redsand at hello@redsand.ai for an official quote or custom configuration.</i></small>", unsafe_allow_html=True)

        filename = f"Redsand_Config_{st.session_state.get('partner_code','')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        summary_data = [["Use Case", use_case],["GPU Type", final_gpu],["Configuration", selected_config],["Units", num_units],["Monthly Cost", f"${monthly:,.0f}"],["Yearly Cost", f"${yearly:,.0f}"],["3-Year Total", f"${total_3yr:,.0f}"]]
        generate_pdf(filename, summary_data, st.session_state.get('partner_name',''), quote_id)

        if os.path.exists(filename):
            with open(filename, "rb") as f:
                if st.download_button("📄 Download PDF", f, file_name=filename):
                    # Log only when PDF is downloaded
                    log_row = {
                        "timestamp": datetime.now().isoformat(),
                        "partner_code": st.session_state.get('partner_code',''),
                        "partner_name": st.session_state.get('partner_name',''),
                        "quote_id": quote_id,
                        "use_case": use_case,
                        "configuration": selected_config,
                        "gpu_type": final_gpu,
                        "units": num_units,
                        "monthly": monthly,
                        "yearly": yearly,
                        "three_year_total": total_3yr,
                        "pdf_file": filename
                    }
                    try:
                        log_df = pd.read_csv("config_log.csv")
                        log_df = pd.concat([log_df, pd.DataFrame([log_row])], ignore_index=True)
                    except FileNotFoundError:
                        log_df = pd.DataFrame([log_row])
                    log_df.to_csv("config_log.csv", index=False)
                    st.success("✅ Quote saved to history")

        nav1, nav2, nav3 = st.columns([1,1,1])
        with nav1:
            if st.button("🏠 Home", key="home_quote"):
                st.session_state["page"] = "welcome"
        with nav2:
            if st.button("🔙 Back", key="back_quote"):
                st.session_state["page"] = "welcome"
        with nav3:
            if st.button("🔓 Logout", key="logout_quote"):
                st.session_state.clear()
                st.experimental_rerun()

# ------------------ ADMIN PANEL ------------------
elif st.session_state["page"] == "welcome" and st.session_state.get("logged_in") and st.session_state.get("admin"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader("🛠️ Admin Panel — All Quotes")
    try:
        full_log = pd.read_csv("config_log.csv")
        st.dataframe(full_log.sort_values("timestamp", ascending=False))
        st.download_button("📥 Download Full Log", full_log.to_csv(index=False), file_name="config_log.csv")
    except FileNotFoundError:
        st.info("No logs found yet.")

    if st.button("🔓 Logout", key="logout_admin"):
        st.session_state.clear()
        st.session_state["page"] = "login"
