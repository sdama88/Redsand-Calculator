
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
    gpu_configs = pd.read_csv("gpu_configs.csv")
    return workloads, upgrade_rules, pricing, gpu_configs

workloads, upgrade_rules, pricing, gpu_configs = load_data()

st.image("Redsand Logo_White.png", width=150)

if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False
if "admin" not in st.session_state:
    st.session_state['admin'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Redsand Login")
    login_email = st.text_input("Enter your Partner or Admin Email", type="password")
    if st.button("Login"):
        if login_email == ADMIN_EMAIL:
            st.session_state['admin'] = True
            st.session_state['logged_in'] = True
        elif login_email in gpu_configs['partner_code'].values:
            st.session_state['partner_name'] = gpu_configs.loc[gpu_configs['partner_code'] == login_email, 'partner_name'].values[0]
            st.session_state['partner_code'] = login_email
            st.session_state['admin'] = False
            st.session_state['logged_in'] = True
        else:
            st.error("Invalid login. Try again.")

if st.session_state['logged_in']:
    if st.session_state['admin']:
        st.title("🔧 Admin Panel - Redsand")
        try:
            logs = pd.read_csv("config_log.csv")
            st.dataframe(logs, use_container_width=True)
            st.download_button("Download All Logs", logs.to_csv(index=False), file_name="config_log.csv")
            st.info("You are logged in as admin.")
        except FileNotFoundError:
            st.warning("No logs found yet.")
    else:
        st.title(f"Welcome, {st.session_state['partner_name']} 👋")
        st.subheader("📦 Build Configuration")
        use_case = st.selectbox("Select Use Case", workloads['workload_name'].unique())
        volume = st.number_input("Expected Concurrent Users", min_value=1, step=1)
        support_level = st.selectbox("Support Tier", ["Standard", "Premium", "Enterprise"])
        redundancy = st.checkbox("N+1 Redundancy")
        dual_power = st.checkbox("Dual Power Supply")
        notes = st.text_area("Additional Notes")

        if st.button("Generate Recommendation"):
            selected_row = workloads[workloads['workload_name'] == use_case].iloc[0]
            gpu_type = selected_row['gpu_type']
            users_per_gpu = selected_row['users_per_gpu']

            upgrade_match = upgrade_rules[(upgrade_rules['current_gpu'] == gpu_type) &
                                          (volume >= upgrade_rules['user_threshold'])]
            if not upgrade_match.empty:
                gpu_type = upgrade_match.iloc[0]['upgrade_gpu']

            gpu_needed = max(1, int(volume / users_per_gpu))
            pricing_row = pricing[pricing['gpu_type'] == gpu_type].iloc[0]
            monthly_cost = pricing_row['monthly_price_usd']
            power_kw = pricing_row['power_kw_per_gpu']

            total_cost = gpu_needed * monthly_cost
            total_power = gpu_needed * power_kw

            if gpu_needed <= 8:
                redbox_model = "RedBox One"
            elif gpu_needed <= 64:
                redbox_model = "RedBox Max"
            else:
                redbox_model = "RedBox Ultra"

            st.success("Configuration calculated!")
            st.write(f"**GPU Type:** {gpu_type}")
            st.write(f"**GPUs Needed:** {gpu_needed}")
            st.write(f"**RedBox Recommendation:** {redbox_model}")
            st.write(f"**Total Monthly Cost:** ${total_cost:,.0f}")
            st.write(f"**Total Power Requirement (kW):** {total_power:.2f}")

            pdf_filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [Paragraph("Redsand Partner Configuration Summary", styles['Title']), Spacer(1, 12)]

            data = [
                ["Partner", st.session_state['partner_name']],
                ["Use Case", use_case],
                ["GPU Type", gpu_type],
                ["GPUs Needed", gpu_needed],
                ["RedBox Model", redbox_model],
                ["Monthly Cost", f"${total_cost:,.0f}"],
                ["Power (kW)", f"{total_power:.2f}"],
                ["Support", support_level],
                ["N+1 Redundancy", "Yes" if redundancy else "No"],
                ["Dual Power", "Yes" if dual_power else "No"],
                ["Notes", notes]
            ]

            table = Table(data, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ]))
            story.append(table)
            doc.build(story)

            with open(pdf_filename, "rb") as f:
                st.download_button("📄 Download PDF", f, file_name=pdf_filename)
