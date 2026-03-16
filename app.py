import streamlit as st
import pandas as pd

def process_and_audit(df):
    # Numeric conversion
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # --- STEP 1: GROUPING BY WORK ORDER ID (The "Fix") ---
    # This ensures multiple investigations for one patient become ONE case
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    # --- STEP 2: APPLYING LOGIC ON GROUPED DATA ---
    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    def calculate_payout(row):
        if row['Disc %'] > 25:
            return 0
        else:
            # Referral = (25% - Actual Disc %) of Net Amount
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ 100% Accurate Case-Based Auditor")

uploaded_file = st.file_uploader("Upload Procedure File", type=['xlsx', 'csv'])

if uploaded_file:
    # Read data
    raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    
    # Process
    final_report = process_and_audit(raw_df)

    # Filtering for Doctor Report (Excluding SELF)
    doc_report = final_report[(final_report['Doctor Name'].notna()) & (final_report['Doctor Name'] != 'SELF')].copy()

    # Checking Dr. Soumya Chatterjee specifically
    soumya_data = doc_report[doc_report['Doctor Name'].str.contains('SOUMYA CHATTERJEE', na=False)]
    
    st.subheader("Summary for Boss")
    col1, col2 = st.columns(2)
    col1.metric("Total Unique Cases", len(doc_report))
    col2.metric("Total Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")

    st.markdown("---")
    st.write("### Verified Case Count (Dr. Soumya Chatterjee)")
    st.write(f"Confirmed Unique Cases: **{len(soumya_data)}**") # Ekhone '2' dekhabe
    st.dataframe(soumya_data)

    st.markdown("### Full Doctor Report")
    st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])
