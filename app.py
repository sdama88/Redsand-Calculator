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
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    title_style = styles['Title']
    title_style.fontSize = 18
    normal_style.fontSize = 11
    story = []

    # Header with logo in top-right
    logo_path = "Redsand Logo_White.png"
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.5*inch, height=0.5*inch)
    else:
        logo = Paragraph("<b>Redsand.ai</b>", ParagraphStyle('fallbackLogo', fontSize=20, textColor=colors.HexColor("#d71920")))

    header = [[Paragraph("Redsand Partner Configuration Summary", title_style), logo]]
    ht = Table(header, colWidths=[4.5*inch, 1.5*inch])
    ht.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(ht)

    story.append(Spacer(1, 8))
    story.append(Paragraph(datetime.now().strftime("%A, %d %B %Y — %H:%M:%S"), normal_style))
    story.append(Paragraph(f"Quote ID: {quote_id}", normal_style))
    story.append(Paragraph(f"Partner: {partner_name}", normal_style))
    story.append(Spacer(1, 18))

    # Split summary_data into config and pricing sections
    config_rows = [row for row in summary_data if row[0] in ["Use Case", "GPU Type", "Configuration", "Boxes Needed"]]
    pricing_rows = [row for row in summary_data if "Cost" in row[0] or "Total" in row[0]]

    # Config section
    story.append(Paragraph("Configuration Details", ParagraphStyle('Heading', fontSize=12, textColor=colors.black, spaceAfter=6)))
    config_table = Table([["Field", "Value"]] + config_rows, hAlign='LEFT', colWidths=[150, 300])
    config_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey)
    ]))
    story.append(config_table)
    story.append(Spacer(1, 18))

    # Pricing section
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
        "Please contact Redsand at <b>sales@redsand.ai</b> for an official quote or custom configuration."
    )
    story.append(Paragraph(disclaimer, ParagraphStyle('Disclaimer', fontSize=9, textColor=colors.grey, leading=12)))

    doc.build(story)

# ------------------ WELCOME + CONFIG SELECTOR WITH PREVIEW ------------------
if st.session_state.get("page") == "welcome" and st.session_state.get("logged_in"):
    st.subheader(f"🔐 Welcome, {st.session_state['partner_name']}")
    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.markdown("### 🚀 Start a New Quote")
        selected_use_case = st.selectbox("Select Use Case", workloads["workload_name"].unique(), key="welcome_use_case")
        num_users = st.number_input("Number of Concurrent Users", min_value=1, step=1, key="welcome_users")
        selected_mode = st.radio("Choose Mode", ["Auto (Recommended)", "Manual Selection"], key="quote_mode_selection")

        # --- Config preview logic ---
        if selected_use_case == "Voice Bot":
            config_row = configs[configs["configuration_name"] == "RedBox Voice"].iloc[0]
            preview_config = config_row["configuration_name"]
            preview_gpu = config_row["gpu_type"]
            users_per_box = workloads[workloads["workload_name"] == selected_use_case].iloc[0]["users_per_gpu"]
            preview_boxes = max(1, int(num_users / users_per_box))
        elif "Auto" in selected_mode:
            workload_row = workloads[workloads["workload_name"] == selected_use_case].iloc[0]
            base_gpu = workload_row["gpu_type"]
            users_per_box = workload_row["users_per_gpu"]
            preview_boxes = max(1, int(num_users / users_per_box))
            upgrade = upgrade_rules[(upgrade_rules["current_gpu"] == base_gpu) & (num_users >= upgrade_rules["user_threshold"])]
            preview_gpu = upgrade.iloc[0]["upgrade_gpu"] if not upgrade.empty else base_gpu
            matching_configs = configs[configs["gpu_type"] == preview_gpu]
            preview_config = matching_configs.iloc[0]["configuration_name"]
        else:
            preview_config = st.selectbox("Choose Configuration", configs["configuration_name"].unique(), key="manual_select")
            preview_boxes = st.number_input("Quantity", min_value=1, step=1, key="manual_qty")
            preview_gpu = configs[configs["configuration_name"] == preview_config].iloc[0]["gpu_type"]

        # Display config preview in realtime
        st.markdown("#### 🔧 Configuration Preview")
        st.write(f"**Use Case:** {selected_use_case}")
        st.write(f"**GPU Type:** {preview_gpu}")
        st.write(f"**Configuration:** {preview_config}")
        st.write(f"**Boxes Needed:** {preview_boxes}")

        # Save preview to session
        st.session_state["preview_config"] = preview_config
        st.session_state["preview_gpu"] = preview_gpu
        st.session_state["preview_boxes"] = preview_boxes
        st.session_state["use_case"] = selected_use_case
        st.session_state["num_users"] = num_users
        st.session_state["quote_mode"] = "Auto" if "Auto" in selected_mode else "Manual"

        st.divider()
        nav1, nav2, nav3 = st.columns([1,1,1])
        with nav1:
            if st.button("🏠 Home", key="home_welcome"):
                st.session_state["page"] = "welcome"
        with nav2:
            if st.button("🔙 Back", key="back_welcome"):
                st.session_state["page"] = "welcome"
        with nav3:
            if st.button("➡️ Generate Quote", key="gen_quote"):
                st.session_state["page"] = "quote_summary"
                st.stop()

    with col_right:
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

        st.divider()
        st.markdown("### 🔍 Compare Configurations")
        compare_configs = st.multiselect("Choose up to 3 configurations to compare", configs["configuration_name"].unique(), key="compare_configs_welcome")
        if compare_configs:
            compare_df = pricing[pricing["configuration_name"].isin(compare_configs)].merge(configs, on="configuration_name", how="left")
            st.dataframe(compare_df.set_index("configuration_name"))

# ------------------ QUOTE SUMMARY PAGE ------------------
if st.session_state.get("page") == "quote_summary" and st.session_state.get("logged_in"):
    st.subheader("🧾 Quote Summary")
    use_case = st.session_state["use_case"]
    selected_config = st.session_state["preview_config"]
    final_gpu = st.session_state["preview_gpu"]
    num_boxes = st.session_state["preview_boxes"]
    quote_id = st.session_state["quote_id"]

    price_row = pricing[pricing["configuration_name"] == selected_config]
    if price_row.empty:
        st.error(f"No pricing found for {selected_config}.")
    else:
        price_per_box = price_row["monthly_price_usd"].values[0]
        monthly = price_per_box * num_boxes
        yearly = monthly * 12
        total_3yr = yearly * 3

        config_details = [
            ["Use Case", use_case],
            ["GPU Type", final_gpu],
            ["Configuration", selected_config],
            ["Boxes Needed", num_boxes]
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

        st.markdown("<small><i>Disclaimer: The pricing provided in this summary is indicative only. Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, service-level agreements, hardware availability, and customer-specific requirements. Please contact Redsand at sales@redsand.ai for an official quote or custom configuration.</i></small>", unsafe_allow_html=True)

        filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        summary_data = [["Use Case", use_case],["GPU Type", final_gpu],["Configuration", selected_config],["Boxes Needed", num_boxes],["Monthly Cost", f"${monthly:,.0f}"],["Yearly Cost", f"${yearly:,.0f}"],["3-Year Total", f"${total_3yr:,.0f}"]]
        generate_pdf(filename, summary_data, st.session_state['partner_name'], quote_id)
        with open(filename, "rb") as f:
            st.download_button("📄 Download PDF", f, file_name=filename)

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

# ------------------ LOGIN PAGE ------------------
if st.session_state["page"] == "login":
    st.title("🔐 Redsand Partner Portal")
    col1, col2 = st.columns(2)
    with col1:
        login_input = st.text_input("Partner Code or Admin Email")
    with col2:
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
