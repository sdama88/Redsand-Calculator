import pandas as pd

# Create an empty DataFrame with all expected columns
cols = [
    "timestamp", "partner_code", "partner_name", "quote_id",
    "use_case", "configuration", "gpu_type", "units",
    "redsand_monthly", "redsand_yearly", "redsand_3yr",
    "margin_monthly", "margin_yearly", "margin_3yr",
    "customer_monthly", "customer_yearly", "customer_3yr",
    "pdf_file"
]
pd.DataFrame(columns=cols).to_csv("config_log.csv", index=False)
print("✅ Log has been reset") where do i run this
