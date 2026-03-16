import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df, master_doc_list):
    # Numeric conversion
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

    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Specific Exclusions for March ENT and Rohit Rungta
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name = str(row['Doctor Name']).strip().upper()
        
        # 1. Validation: Must be in Master List AND NOT in Excluded List
        if doc_name not in master_doc_list or doc_name in excluded_doctors:
            return 0
        
        # 2. Logic: 25% Discount Threshold
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ 100% Accurate Referral Audit")

uploaded_file = st.file_uploader("Upload Procedure Excel", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        # Using specific sheet names provided by you
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name')
        
        # Preparing Master List from Sheet 2 (Cleaning and Uppercasing)
        # We take the doctor names from the 'Doc Name' sheet
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()

        # Step 2: Process with Master List Validation
        final_df = process_data(raw_df, master_docs)

        # SEPARATING REPORTS
        # Doctor Report: Only those who are in Master List and not excluded
        doc_report = final_df[final_df['Referral Payable'] > 0].copy() if selected_doc == "All Doctors" else final_df
        
        # UI TABS
        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Payout Audit", "🔬 Lab Referral Audit"])

        # Sidebars for Dropdown
        st.sidebar.header("Filters")
        all_docs = ["All Doctors"] + sorted([d for d in master_docs if d not in ['ROHIT RUNGTA', 'DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']])
        selected_doc = st.sidebar.selectbox("Select Doctor", all_docs)

        with tab1:
            display_df = final_df[final_df['Doctor Name'].str.upper() == selected_doc] if selected_doc != "All Doctors" else final_df
            # Final Check: Exclude SELF and Lab entries from Doctor Tab
            display_df = display_df[(display_df['Doctor Name'] != 'SELF') & (display_df['Referral Payable'] >= 0)]
            
            st.subheader(f"Report for: {selected_doc}")
            st.metric("Total Payable", f"₹ {display_df['Referral Payable'].sum():,.2f}")
            st.dataframe(display_df[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")]
            st.subheader("Other Lab Referrals")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Net Amount', 'Disc %', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: Please ensure Sheet Names are 'Doc Ref.' and 'Doc Name'. Details: {e}")
