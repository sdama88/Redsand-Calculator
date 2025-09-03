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

import gspread
from google.oauth2.service_account import Credentials

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client

def log_to_sheets(log_row):
    try:
        client = get_gsheet_client()
        sheet = client.open("RedsandQuotes").sheet1  # 👈 make sure the sheet exists
        sheet.append_row(list(log_row.values()))
    except Exception as e:
        st.error(f"Google Sheets logging failed: {e}")



st.set_page_config(page_title="Redsand Partner Portal", layout="wide")
ADMIN_EMAIL = "sdama@redsand.ai"

@st.cache_data
def load_data():
    workloads = pd.read_csv("workloads.csv")
    upgrade_rules = pd.read_csv("gpu_upgrade_rules.csv")
    pricing = pd.read_csv("pricing.csv")
    configs = pd.read_csv("redbox_configs.csv")
    credentials = pd.read_csv("partner_credentials.csv")
    # Ensure margin column is numeric
    if "margin_percent" in credentials.columns:
        credentials["margin_percent"] = pd.to_numeric(credentials["margin_percent"], errors="coerce").fillna(0)
    return workloads, upgrade_rules, pricing, configs, credentials

workloads, upgrade_rules, pricing, configs, credentials = load_data()

# ---------------- SESSION KEYS ----------------
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

# ---------------- SAFE LOGOUT ----------------
def safe_logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["page"] = "login"
    st.session_state["logged_in"] = False
    st.session_state["admin"] = False
    st.session_state["pdf_ready"] = False
    st.session_state["quote_id"] = str(uuid.uuid4())[:8]
    st.rerun()

# ---------------- NAVIGATION ----------------
def go_to(page):
    st.session_state["page"] = page
    st.rerun()

# ---------------- LOGIN PAGE ----------------
if st.session_state["page"] == "login":
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.title("🔐 Redsand Partner Portal")
    login_input = st.text_input("Partner Code or Admin Email")
    password_input = st.text_input("Password", type="password")

    if st.button("Login", key="login_btn" ):
        if login_input == ADMIN_EMAIL:
            st.session_state['admin'] = True
            st.session_state['logged_in'] = True
            go_to("welcome")
        else:
            match = credentials[(credentials['partner_code'] == login_input) & (credentials['password'] == password_input)]
            if not match.empty:
                st.session_state['partner_name'] = match.iloc[0]['partner_name']
                st.session_state['partner_code'] = match.iloc[0]['partner_code']
                st.session_state['partner_margin'] = float(match.iloc[0]['margin_percent']) if 'margin_percent' in match.columns else 0
                st.session_state['admin'] = False
                st.session_state['logged_in'] = True
                go_to("welcome")
            else:
                st.error("Invalid partner code or password.")

# ---------------- WELCOME PAGE ----------------
elif st.session_state["page"] == "welcome" and st.session_state.get("logged_in") and not st.session_state.get("admin"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader(f"🔐 Welcome, {st.session_state['partner_name']}")

    if st.button("🔓 Logout", key="logout_welcome"):
        safe_logout()

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
                go_to("welcome")
        with nav2:
            if st.button("🔙 Back", key="back_welcome"):
                go_to("welcome")
        with nav3:
            if st.button("➡️ Generate Quote", key="gen_quote"):
                go_to("quote_summary")
        with nav4:
            if st.button("🔓 Logout", key="logout_welcome2"):
                safe_logout()

    with col_right:
        st.markdown("### 🔍 Compare Configurations")
        compare_configs = st.multiselect("Choose configurations to compare", configs["configuration_name"].unique(), key="compare_configs_welcome")
        if compare_configs:
            compare_df = pricing[pricing["configuration_name"].isin(compare_configs)].merge(configs, on="configuration_name", how="left")
            st.dataframe(compare_df.set_index("configuration_name"))

        st.divider()
        st.markdown("### 📚 My Quote History")
        try:
            full_log = pd.read_csv("config_log.csv")
            partner_code = st.session_state.get('partner_code')
            if partner_code:
                partner_log = full_log[full_log['partner_code'] == partner_code]
                if not partner_log.empty:
                    st.dataframe(partner_log.sort_values("timestamp", ascending=False))
                else:
                    st.info("No previous quotes found.")
            else:
                st.info("No partner code found for this session.")
        except FileNotFoundError:
            st.info("Quote log file not found.")

# ---------------- QUOTE SUMMARY PAGE ----------------
elif st.session_state["page"] == "quote_summary" and st.session_state.get("logged_in"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader("🧾 Quote Summary")

    if st.button("🔓 Logout", key="logout_quote"):
        safe_logout()

    use_case = st.session_state.get("use_case", "N/A")
    selected_config = st.session_state.get("preview_config", "N/A")
    final_gpu = st.session_state.get("preview_gpu", "N/A")
    num_units = st.session_state.get("preview_units", 0)
    quote_id = st.session_state["quote_id"]

    partner_name = st.session_state.get("partner_name", "Partner")
    partner_margin = st.session_state.get("partner_margin", 0)

    price_row = pricing[pricing["configuration_name"] == selected_config]
    if price_row.empty:
        st.error(f"No pricing found for {selected_config}.")
    else:
        price_per_unit = price_row["monthly_price_usd"].values[0]

        # Base and final pricing
        base_monthly = price_per_unit * num_units
        partner_margin_value = base_monthly * (partner_margin / 100)
        final_monthly = base_monthly + partner_margin_value
        final_yearly = final_monthly * 12
        final_3yr = final_yearly * 3

        # ---------------- STREAMLIT TABLE ----------------
        pricing_table = pd.DataFrame({
            "Base Redsand Price": [
                f"${base_monthly:,.0f}",
                f"${base_monthly*12:,.0f}",
                f"${base_monthly*36:,.0f}"
            ],
            f"Partner Margin ({partner_margin}%) – {partner_name}": [
                f"${partner_margin_value:,.0f}",
                f"${partner_margin_value*12:,.0f}",
                f"${partner_margin_value*36:,.0f}"
            ],
            "Final Customer Price": [
                f"${final_monthly:,.0f}",
                f"${final_yearly:,.0f}",
                f"${final_3yr:,.0f}"
            ]
        }, index=["Monthly", "Yearly", "3-Year Total"])

        st.markdown("### Pricing Details")
        st.table(pricing_table)

        st.markdown("<small><i>Disclaimer: The pricing provided in this summary is indicative only. Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, service-level agreements, hardware availability, and customer-specific requirements. Please contact Redsand at hello@redsand.ai for an official quote or custom configuration.</i></small>", unsafe_allow_html=True)

        # ---------------- PDF TABLE ----------------
        filename = f"Redsand_Config_{st.session_state.get('partner_code','')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        try:
            doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=60, bottomMargin=40)
            styles = getSampleStyleSheet()
            story = []

            # Logo and header
            logo_path = "Redsand Logo_White.png"
            if os.path.exists(logo_path):
                logo = Image(logo_path)
                logo._restrictSize(1.8*inch, 0.6*inch)
            else:
                logo = Paragraph("<b>Redsand.ai</b>", ParagraphStyle('fallbackLogo', fontSize=20, textColor=colors.HexColor("#d71920")))

            header = [[Paragraph("Redsand Partner Configuration Summary", styles['Title']), logo]]
            ht = Table(header, colWidths=[4.5*inch, 1.8*inch])
            story.append(ht)
            story.append(Spacer(1, 12))

            # Config table
            config_data = [
                ["Use Case", use_case],
                ["GPU Type", final_gpu],
                ["Configuration", selected_config],
                ["Units", num_units]
            ]
            config_table = Table([["Field", "Value"]] + config_data, hAlign='LEFT')
            config_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.lightgrey), ('GRID', (0,0), (-1,-1), 0.25, colors.grey)]))
            story.append(config_table)
            story.append(Spacer(1, 18))

            # Pricing table with wrapped headers
            wrap_style = ParagraphStyle(name="wrap", fontSize=9, leading=11, alignment=1)
            pdf_pricing = [
                [
                    Paragraph("Period", wrap_style),
                    Paragraph("Base Redsand Price", wrap_style),
                    Paragraph(f"Partner Margin ({partner_margin}%) – {partner_name}", wrap_style),
                    Paragraph("Final Customer Price", wrap_style)
                ],
                ["Monthly", f"${base_monthly:,.0f}", f"${partner_margin_value:,.0f}", f"${final_monthly:,.0f}"],
                ["Yearly", f"${base_monthly*12:,.0f}", f"${partner_margin_value*12:,.0f}", f"${final_yearly:,.0f}"],
                ["3-Year Total", f"${base_monthly*36:,.0f}", f"${partner_margin_value*36:,.0f}", f"${final_3yr:,.0f}"]
            ]
            pricing_table_pdf = Table(pdf_pricing, hAlign='LEFT', colWidths=[80, 120, 170, 150])
            pricing_table_pdf.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
                ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
            ]))
            story.append(pricing_table_pdf)

            disclaimer = ("<b>Disclaimer:</b> The pricing provided in this summary is indicative only. "
                          "Final pricing will vary based on the actual configuration including RAM, storage, special hardware features, "
                          "service-level agreements, hardware availability, and customer-specific requirements. "
                          "Please contact Redsand at <b>hello@redsand.ai</b> for an official quote or custom configuration.")
            story.append(Spacer(1, 18))
            story.append(Paragraph(disclaimer, ParagraphStyle('Disclaimer', fontSize=9, textColor=colors.grey, leading=12)))

            doc.build(story)
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

        # Download + log
        if os.path.exists(filename):
            with open(filename, "rb") as f:
              if st.download_button("📄 Download PDF", f, file_name=filename, key="download_pdf_button"):
                    st.write("📝 Download button clicked — logging now...")  # Debug
                    log_row = {
                        "timestamp": datetime.now().isoformat(),
                        "partner_code": st.session_state.get('partner_code',''),
                        "partner_name": partner_name,
                        "quote_id": quote_id,
                        "use_case": use_case,
                        "configuration": selected_config,
                        "gpu_type": final_gpu,
                        "units": num_units,
                        "price_per_unit": price_per_unit,
                        "redsand_monthly": base_monthly,
                        "redsand_yearly": base_monthly*12,
                        "redsand_3yr": base_monthly*36,
                        "margin_monthly": partner_margin_value,
                        "margin_yearly": partner_margin_value*12,
                        "margin_3yr": partner_margin_value*36,
                        "customer_monthly": final_monthly,
                        "customer_yearly": final_yearly,
                        "customer_3yr": final_3yr,
                        "pdf_file": filename
                    }
                
                    try:
                        log_df = pd.read_csv("config_log.csv")
                        # Align columns safely
                        log_df = pd.concat([log_df, pd.DataFrame([log_row])], ignore_index=True, sort=False)
                    except FileNotFoundError:
                        # First time → let log_row define the schema
                        log_df = pd.DataFrame([log_row])
                    
                    log_df.to_csv("config_log.csv", index=False)
                    st.success("✅ Quote saved to history")
                    log_to_sheets(log_row)                    
                    st.info("Attempting to log to Google Sheets…")

        nav1, nav2, nav3 = st.columns([1,1,1])
        with nav1:
            if st.button("🏠 Home", key="home_quote"):
                go_to("welcome")
        with nav2:
            if st.button("🔙 Back", key="back_quote"):
                go_to("welcome")
        with nav3:
            if st.button("🔓 Logout", key="logout_quote2"):
                safe_logout()

# ------------------ ADMIN PANEL ------------------
elif st.session_state["page"] == "welcome" and st.session_state.get("logged_in") and st.session_state.get("admin"):
    if os.path.exists("Redsand Logo_White.png"):
        st.image("Redsand Logo_White.png", width=200)
    st.subheader("🛠️ Admin Panel — All Quotes")

    if st.button("🔓 Logout", key="logout_admin"):
        safe_logout()

    try:
        full_log = pd.read_csv("config_log.csv")
        full_log["timestamp"] = pd.to_datetime(full_log["timestamp"], errors="coerce")

        # 🔹 Metrics bar
        total_quotes = len(full_log)
        total_partners = full_log["partner_name"].nunique()
        latest_quote_date = full_log["timestamp"].max().strftime("%d %b %Y %H:%M") if not full_log.empty else "N/A"

        col1, col2, col3 = st.columns(3)
        col1.metric("📄 Total Quotes", total_quotes)
        col2.metric("👥 Total Partners", total_partners)
        col3.metric("🕒 Latest Quote", latest_quote_date)

        # Partner filter
        partner_options = ["All"] + sorted(full_log["partner_name"].dropna().unique().tolist())
        selected_partner = st.selectbox("Filter by Partner", partner_options, key="admin_partner_filter")

        # Date range filter
        min_date = full_log["timestamp"].min().date() if not full_log.empty else datetime.today().date()
        max_date = full_log["timestamp"].max().date() if not full_log.empty else datetime.today().date()
        start_date, end_date = st.date_input(
            "Filter by Date Range",
            [min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="admin_date_filter"
        )

        # Quote ID search
        search_quote_id = st.text_input("Search by Quote ID", key="admin_quote_search")

        # Apply filters
        filtered_log = full_log
        if selected_partner != "All":
            filtered_log = filtered_log[filtered_log["partner_name"] == selected_partner]

        if len([start_date, end_date]) == 2:
            filtered_log = filtered_log[
                (filtered_log["timestamp"].dt.date >= start_date) &
                (filtered_log["timestamp"].dt.date <= end_date)
            ]

        if search_quote_id.strip():
            filtered_log = filtered_log[filtered_log["quote_id"].astype(str).str.contains(search_quote_id.strip(), case=False, na=False)]

        st.dataframe(filtered_log.sort_values("timestamp", ascending=False))
        st.download_button(
            "📥 Download Filtered Log",
            filtered_log.to_csv(index=False),
            file_name="config_log.csv"
        )
    except FileNotFoundError:
        st.info("No logs found yet.")

    nav1, nav2 = st.columns([1, 1])
    with nav1:
        if st.button("🏠 Home", key="home_admin"):
            go_to("welcome")
    with nav2:
        if st.button("🔙 Back", key="back_admin"):
            go_to("welcome")
