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

    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Excluded Doctors for March ENT and Rohit Rungta (as per your request)
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name = str(row['Doctor Name']).strip().upper()
        
        # 1. Validation: Must be in Sheet 2 (Doc Name) list AND not excluded
        if doc_name not in master_doc_list or doc_name in excluded_doctors:
            return 0
        
        # 2. Condition: 25% Threshold on Net Amount
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
        # Using exact sheet names provided
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name')
        
        # Cleaning Master Doctor List from Sheet 2
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()

        # Step 2: Process Data
        final_df = process_data(raw_df, master_docs)

        # --- FILTERS IN SIDEBAR ---
        st.sidebar.header("Filter Reports")
        
        # Doctor Filter (Filtered to exclude those not in master list or excluded)
        valid_docs = sorted([d for d in master_docs if d not in ['ROHIT RUNGTA', 'DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']])
        doc_options = ["All Doctors"] + valid_docs
        selected_doc = st.sidebar.selectbox("Select Doctor Name", doc_options)
        
        # Lab Filter
        lab_options = ["All Labs"] + sorted([str(l) for l in final_df['Other Lab Refer'].unique() if pd.notna(l) and l != ""])
        selected_lab = st.sidebar.selectbox("Select Lab Refer", lab_options)

        # --- UI LAYOUT ---
        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Payout Audit", "🔬 Lab Referral Audit"])

        with tab1:
            # Filter the report based on dropdown
            doc_report = final_df.copy()
            if selected_doc != "All Doctors":
                doc_report = doc_report[doc_report['Doctor Name'].str.upper() == selected_doc]
            
            # Filtering out non-payout rows for doctor view
            doc_report = doc_report[(doc_report['Doctor Name'] != 'SELF')]
            
            st.subheader(f"Doctor Settlement: {selected_doc}")
            st.metric("Total Payable (Filtered)", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
            st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")].copy()
            if selected_lab != "All Labs":
                lab_report = lab_report[lab_report['Other Lab Refer'] == selected_lab]
                
            st.subheader(f"Lab Settlement: {selected_lab}")
            st.metric("Total Payable (Filtered)", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

        # Sidebar Download
        st.sidebar.markdown("---")
        st.sidebar.download_button("📥 Download Final Audit Report", final_df.to_csv(index=False), "Referral_Audit_Final.csv")

    except Exception as e:
        st.error(f"Error Details: {e}")
        st.info("Ensure Excel has 'Doc Ref.' and 'Doc Name' sheets.")
