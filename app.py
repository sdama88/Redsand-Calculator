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
        match = credentials[credentials['partner_code'] == login_input]
        if not match.empty:
            stored_password = match.iloc[0]['password']
            if password_input == stored_password:
                st.session_state['partner_name'] = match.iloc[0]['partner_name']
                st.session_state['partner_code'] = match.iloc[0]['partner_code']
                st.session_state['admin'] = False
                st.session_state['logged_in'] = True
            else:
                st.error("Incorrect password for partner.")
        else:
            st.error("Invalid partner code.")



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

# Your main app logic would continue here...
