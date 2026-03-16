import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df, master_doc_list):
    # Standardizing numeric columns
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # --- STEP 1: GROUPING BY WORK ORDER ID ---
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    # --- STEP 2: APPLYING BOSS'S LOGIC ---
    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Exclude logic for MARCH ENT Doctors
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']
    
    def calculate_payout(row):
        doc_name = str(row['Doctor Name']).strip().upper()
        # Condition 1: Must be in Master List (Sheet 2)
        # Condition 2: Must NOT be in March ENT excluded list
        # Condition 3: Not Rohit Rungta
        if doc_name not in master_doc_list or doc_name in excluded_doctors or "ROHIT RUNGTA" in doc_name:
            return 0
        
        # Condition 4: 25% Discount Threshold
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Final Precision Referral Dashboard")

uploaded_file = st.file_uploader("Upload Procedure Excel", type=['xlsx'])

if uploaded_file:
    try:
        # Load all sheets
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') # Sheet 2
        
        # Prepare Master Doctor List from Sheet 2 (Cleaning names)
        # Assuming names are in the second column or specific header
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        
        # Remove Rohit Rungta from the master list calculation as requested
        if "ROHIT RUNGTA" in master_docs: master_docs.remove("ROHIT RUNGTA")

        # Process
        final_df = process_data(raw_df, master_docs)

        # --- SEPARATING REPORTS ---
        doc_report = final_df[(final_df['Doctor Name'].notna()) & (final_df['Doctor Name'] != 'SELF')].copy()
        lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")].copy()

        # UI TABS
        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Payout Audit", "🔬 Lab Referral Audit"])

        with tab1:
            st.subheader("Verified Doctor Referrals (Based on Sheet 2 List)")
            st.metric("Total Payable", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
            st.dataframe(doc_report)

        with tab2:
            st.subheader("Other Lab Referrals")
            st.metric("Total Payable", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report)

    except Exception as e:
        st.error(f"Error: Ensure sheet names 'Doc Ref.' and 'Doc Name' are correct. {e}")
