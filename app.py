import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Referral Auditor", layout="wide")

def process_data(df, master_doc_list):
    # Numeric cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # 1. Aggregation by Work Order (Correct Case Counting)
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
    
    # Strict Exclusion List
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name_raw = str(row['Doctor Name']).strip().upper()
        
        # Validation: Partial matching logic to fix "Dr." or "Prof." issues
        is_valid = any(m_doc in doc_name_raw for m_doc in master_doc_list if len(m_doc) > 3)
        is_excluded = any(ex in doc_name_raw for ex in excluded_doctors)
        
        if not is_valid or is_excluded or doc_name_raw == 'SELF':
            return 0
        
        # 25% Logic
        if row['Disc %'] > 25:
            return 0
        else:
            return row['Net Amount'] * ((25 - row['Disc %']) / 100)

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ 100% Precision Referral System")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        # Using exact sheet names from your file
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') 

        # --- FIX: SMART DOCTOR NAME EXTRACTION ---
        # Taking Column B (index 1) and cleaning it
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        # Clean master_docs (Removing headers/sections like 'MARCH ENT')
        master_docs = [d for d in master_docs if len(d) > 5 and 'DOC LIST' not in d and d != 'MARCH ENT']

        final_df = process_data(raw_df, master_docs)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Other Lab Report"])

        with tab1:
            # Dropdown Filter
            valid_list = sorted([d for d in master_docs if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
            selected_doc = st.sidebar.selectbox("Filter by Doctor", ["All Doctors"] + valid_list)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            # Show final verified cases
            st.subheader(f"Results for: {selected_doc}")
            st.metric("Total Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report (Specifically for Other Lab Refer and Rohit Rungta)
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
            st.subheader("Other Lab Report (Including Rohit Rungta)")
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Referral Payable']])

    except Exception as e:
        st.error(f"Critical Error: {e}")
