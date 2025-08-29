
import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import smtplib
from email.message import EmailMessage

st.set_page_config(page_title="Redsand Partner Portal", layout="wide")

ADMIN_EMAIL = "sdama@redsand.ai"

@st.cache_data
def load_data():
    workloads = pd.read_csv("workloads.csv")
    upgrade_rules = pd.read_csv("gpu_upgrade_rules.csv")
    pricing = pd.read_csv("pricing.csv")
    gpu_configs = pd.read_csv("gpu_configs.csv")
    return workloads, upgrade_rules, pricing, gpu_configs

gpu_specs, prebuilt_configs, use_cases, partner_codes = load_data()

st.image("Redsand Logo_White.png", width=150)

# Login screen for admin and partners
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
        elif login_email in partner_codes['code'].values:
            st.session_state['partner_name'] = partner_codes.loc[partner_codes['code'] == login_email, 'partner_name'].values[0]
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
        tab1, tab2 = st.tabs(["📦 Configure", "📄 My History"])
        with tab1:
            use_case = st.selectbox("Select Use Case", use_cases['use_case'])
            selected_config = st.selectbox("Choose Prebuilt RedBox Config", prebuilt_configs['redbox_model'])
            volume = st.number_input("Enter Expected Number of Users", min_value=1, step=1)
            redundancy = st.checkbox("N+1 Redundancy")
            dual_power = st.checkbox("Dual Power Supply")
            support_level = st.selectbox("Support Tier", ["Standard", "Premium", "Enterprise"])
            notes = st.text_area("Additional Notes (Optional)")

            if st.button("🔍 Generate Recommendation"):
                preferred_gpu = use_cases.loc[use_cases['use_case'] == use_case, 'preferred_gpu'].values[0]
                qps_per_user = use_cases.loc[use_cases['use_case'] == use_case, 'qps_target_per_user'].values[0]
                qps_total = volume * qps_per_user
                gpu_qps = gpu_specs.loc[gpu_specs['gpu_model'] == preferred_gpu, 'qps_per_gpu'].values[0]
                gpu_needed = int((qps_total / gpu_qps) + 0.999)
                gpu_power = gpu_specs.loc[gpu_specs['gpu_model'] == preferred_gpu, 'power_kw'].values[0]
                gpu_cost = gpu_specs.loc[gpu_specs['gpu_model'] == preferred_gpu, 'cost_usd'].values[0]
                total_power = gpu_power * gpu_needed
                total_cost = gpu_cost * gpu_needed

                st.success("Configuration calculated!")
                st.write(f"**GPU Model:** {preferred_gpu}")
                st.write(f"**GPUs Needed:** {gpu_needed}")
                st.write(f"**Total Power (kW):** {total_power:.2f}")
                st.write(f"**Estimated Cost:** ${total_cost:,.0f}")

                # Save to PDF
                pdf_filename = f"Redsand_Config_{st.session_state['partner_code']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
                styles = getSampleStyleSheet()
                story = [Paragraph("Redsand Partner Configuration Summary", styles['Title']), Spacer(1, 12)]

                table_data = [
                    ["Partner", st.session_state['partner_name']],
                    ["Use Case", use_case],
                    ["GPU", preferred_gpu],
                    ["GPUs Needed", gpu_needed],
                    ["Power (kW)", f"{total_power:.2f}"],
                    ["Cost", f"${total_cost:,.0f}"],
                    ["Redundancy", "Yes" if redundancy else "No"],
                    ["Dual Power", "Yes" if dual_power else "No"],
                    ["Support", support_level],
                    ["Notes", notes]
                ]
                table = Table(table_data, hAlign="LEFT")
                table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black)]))
                story.append(table)
                doc.build(story)

                # Log entry
                log_row = {
                    "timestamp": datetime.now(),
                    "partner": st.session_state['partner_name'],
                    "code": st.session_state['partner_code'],
                    "use_case": use_case,
                    "gpu_model": preferred_gpu,
                    "gpu_count": gpu_needed,
                    "power_kw": total_power,
                    "cost_usd": total_cost,
                    "support_level": support_level,
                    "redundancy": redundancy,
                    "dual_power": dual_power,
                    "notes": notes,
                    "pdf_file": pdf_filename
                }

                df = pd.DataFrame([log_row])
                try:
                    existing = pd.read_csv("config_log.csv")
                    df = pd.concat([existing, df], ignore_index=True)
                except FileNotFoundError:
                    pass
                df.to_csv("config_log.csv", index=False)

                # Email alert (placeholder only)
                try:
                    msg = EmailMessage()
                    msg["Subject"] = "New Redsand Config Submission"
                    msg["From"] = "noreply@redsand.ai"
                    msg["To"] = ADMIN_EMAIL
                    msg.set_content(f"New config submitted by {st.session_state['partner_name']} ({st.session_state['partner_code']})\nUse case: {use_case}, GPUs: {gpu_needed}, Cost: ${total_cost:,.0f}")
                    with smtplib.SMTP("localhost") as server:
                        server.send_message(msg)
                except Exception as e:
                    st.warning("Email could not be sent (test mode).")

                with open(pdf_filename, "rb") as f:
                    st.download_button("📄 Download PDF", f, file_name=pdf_filename)

        with tab2:
            try:
                logs = pd.read_csv("config_log.csv")
                my_logs = logs[logs["code"] == st.session_state['partner_code']]
                st.dataframe(my_logs.drop(columns=["pdf_file"]), use_container_width=True)
            except FileNotFoundError:
                st.info("No configuration history found.")
