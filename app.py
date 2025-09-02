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

if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False
if "admin" not in st.session_state:
    st.session_state['admin'] = False
if "show_summary" not in st.session_state:
    st.session_state["show_summary"] = False
if "pdf_ready" not in st.session_state:
    st.session_state["pdf_ready"] = False

# ------------------ PDF GENERATOR ------------------
def generate_pdf(filename, summary_data, partner_name):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    title_style = styles['Title']
    title_style.fontSize = 18
    normal_style.fontSize = 11
    story = []

    logo_path = "Redsand Logo_White.png"
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=2.5*inch, height=0.8*inch))
    else:
        story.append(Paragraph("<b>Redsand.ai</b>", ParagraphStyle('fallbackLogo', fontSize=20, textColor=colors.HexColor("#d71920"))))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Redsand Partner Configuration Summary", title_style))
    story.append(Paragraph(datetime.now().strftime("%A, %d %B %Y — %H:%M:%S"), normal_style))
    story.append(Spacer(1, 18))
    story.append(Paragraph(f"<b>Partner:</b> {partner_name}", normal_style))
    story.append(Spacer(1, 12))

    table_data = [["Field", "Value"]] + summary_data
    table = Table(table_data, hAlign='LEFT', colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d71920")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey)
    ]))
    story.append(table)
    story.append(Spacer(1, 24))

    disclaimer_style = ParagraphStyle('Disclaimer', fontSize=9, textColor=colors.grey, leading=12)
    disclaimer_text = (
        "<b>Disclaimer:</b> The pricing provided in this summary is indicative only. "
        "Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, "
        "service-level agreements, hardware availability, and customer-specific requirements. "
        "Please contact Redsand for an official quote.")
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)

# ------------------ CONFIG LOGGING ------------------
def log_config(partner_code, partner_name, mode, use_case, config, gpu_type, qty, monthly, yearly, total_3yr, pdf_file):
    log_row = {
        "timestamp": datetime.now().isoformat(),
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

# ------------------ LOGIN PAGE ------------------
if st.session_state["page"] == "login":
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
elif st.session_state["page"] == "welcome":
    st.session_state["show_summary"] = False
    st.session_state["pdf_ready"] = False

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
        st.session_state['mode'] = mode
        if mode == "🔍 Use Case Recommendation":
            st.session_state['use_case'] = st.selectbox("Select Use Case", workloads['workload_name'].unique())
            st.session_state['users'] = st.number_input("Number of Concurrent Users", min_value=1, step=1)
        else:
            st.session_state['manual_config'] = st.selectbox("Choose Configuration", configs["configuration_name"].unique())
            st.session_state['manual_qty'] = st.number_input("Quantity", min_value=1, step=1)

        if st.button("Next"):
            st.session_state["page"] = "configure"

    if st.button("Logout"):
        st.session_state.clear()
        st.session_state["page"] = "login"
        st.stop()

# ------------------ CONFIGURATION PAGE ------------------
elif st.session_state["page"] == "configure":
    if not st.session_state["show_summary"]:
        mode = st.session_state['mode']
        if mode == "🔍 Use Case Recommendation":
            use_case = st.session_state['use_case']
            users = st.session_state['users']
            if use_case == "Voicebot":
                selected_config = "RedBox Voice"
                config_row = configs[configs["configuration_name"] == selected_config].iloc[0]
                final_gpu = config_row["gpu_type"]
                workload_row = workloads[workloads["workload_name"] == use_case].iloc[0]
                users_per_box = workload_row["users_per_gpu"]
                num_boxes = max(1, int(users / users_per_box))
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

            st.session_state.update({
                "summary_mode": "Auto",
                "summary_use_case": use_case,
                "summary_gpu": final_gpu,
                "summary_config": selected_config,
                "summary_qty": num_boxes
            })

        elif mode == "✋ Manual Selection":
            selected_config = st.session_state['manual_config']
            quantity = st.session_state['manual_qty']
            st.session_state.update({
                "summary_mode": "Manual",
                "summary_use_case": "Manual",
                "summary_gpu": "",
                "summary_config": selected_config,
                "summary_qty": quantity
            })

        st.session_state["show_summary"] = True

    # Show Summary Section
    st.subheader("📋 Configuration Summary")
    qty = st.session_state["summary_qty"]
    config = st.session_state["summary_config"]
    gpu = st.session_state["summary_gpu"]
    use_case = st.session_state["summary_use_case"]
    price_row = pricing[pricing["configuration_name"] == config]
    price_per_box = price_row["monthly_price_usd"].values[0]
    monthly = price_per_box * qty
    yearly = monthly * 12
    total_3yr = yearly * 3

    summary_data = [
        ["Use Case", use_case],
        ["GPU Type", gpu],
        ["Boxes/Units", qty],
        ["Configuration", config],
        ["Monthly Cost", f"${monthly:,.0f}"],
        ["Yearly Cost", f"${yearly:,.0f}"],
        ["3-Year Total", f"${total_3yr:,.0f}"]
    ]

    for row in summary_data:
        st.write(f"**{row[0]}:** {row[1]}")

    if not st.session_state["pdf_ready"]:
        if st.button("Generate PDF"):
            filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            generate_pdf(filename, summary_data, st.session_state['partner_name'])
            log_config(st.session_state['partner_code'], st.session_state['partner_name'], st.session_state["summary_mode"], use_case, config, gpu, qty, monthly, yearly, total_3yr, filename)
            st.session_state["pdf_file"] = filename
            st.session_state["pdf_ready"] = True

    if st.session_state["pdf_ready"]:
        with open(st.session_state["pdf_file"], "rb") as f:
            st.download_button("📄 Download PDF", f, file_name=st.session_state["pdf_file"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔙 Back"):
            st.session_state["page"] = "welcome"
            st.session_state["show_summary"] = False
            st.session_state["pdf_ready"] = False
    with col2:
        if st.button("Logout"):
            st.session_state.clear()
            st.session_state["page"] = "login"
            st.stop()
