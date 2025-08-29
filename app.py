
import streamlit as st
import pandas as pd
from datetime import datetime

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

# Logo and login
st.image("Redsand Logo_White.png", width=150)
if "logged_in" not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Redsand Partner Portal Login")
    partner_code = st.text_input("Enter your Partner Access Code", type="password")
    if st.button("Login"):
        if partner_code in partner_codes['code'].values:
            partner_name = partner_codes.loc[partner_codes['code'] == partner_code, 'partner_name'].values[0]
            st.session_state['logged_in'] = True
            st.session_state['partner_name'] = partner_name
        else:
            st.error("Invalid partner code. Please try again.")
else:
    st.title(f"Welcome, {st.session_state['partner_name']} 👋")
    st.subheader("🔧 Configuration Builder")

    tab1, tab2, tab3 = st.tabs(["1️⃣ Use Case", "2️⃣ Optional Add-ons", "3️⃣ Summary & Export"])

    with tab1:
        use_case = st.selectbox("Select Use Case", use_cases['use_case'])
        selected_config = st.selectbox("Choose Prebuilt RedBox Config", prebuilt_configs['redbox_model'])
        volume = st.number_input("Enter Expected Number of Users", min_value=1, step=1)

    with tab2:
        add_redundancy = st.checkbox("Include N+1 Redundancy?")
        dual_power = st.checkbox("Dual Power Supply?")
        support_level = st.selectbox("Support Tier", ["Standard", "Premium", "Enterprise"])
        notes = st.text_area("Additional Notes (Optional)")

    with tab3:
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

            st.markdown(f"### 📦 Recommendation")
            st.write(f"**GPU Model:** {preferred_gpu}")
            st.write(f"**GPUs Needed:** {gpu_needed}")
            st.write(f"**Total Power (kW):** {total_power:.2f}")
            st.write(f"**Estimated Cost:** ${total_cost:,.0f}")

            st.download_button("📄 Download PDF Summary", "PDF content placeholder", file_name="redsand_summary.pdf")

            log_data = {
                "timestamp": datetime.now(),
                "partner": st.session_state['partner_name'],
                "use_case": use_case,
                "volume": volume,
                "gpu_model": preferred_gpu,
                "gpu_needed": gpu_needed,
                "total_power": total_power,
                "total_cost": total_cost,
                "support_level": support_level
            }
            st.session_state['log'] = log_data

            st.success("Configuration generated and logged.")
