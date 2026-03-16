import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Precision Auditor", layout="wide")

def process_data(df, master_list):
    # Numeric cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # STEP 1: Aggregate by Work Order (Correct Case Counting)
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Actual Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Strict Exclusion List
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name_raw = str(row['Doctor Name']).strip().upper()
        
        # Rohit Rungta or Self = 0 in Doctor Tab
        if "ROHIT RUNGTA" in doc_name_raw or doc_name_raw == 'SELF':
            return 0
            
        # Flexible Matching logic: Check if any part of Sheet 2 matches main data
        is_valid = False
        for m_doc in master_list:
            if m_doc in doc_name_raw or doc_name_raw in m_doc:
                is_valid = True
                break
        
        # March ENT Block
        is_excluded = any(ex in doc_name_raw for ex in excluded_doctors)
        
        if not is_valid or is_excluded:
            return 0
        
        # 25% Threshold Logic
        if row['Actual Disc %'] > 25:
            return 0
        else:
            return row['Net Amount'] * ((25 - row['Actual Disc %']) / 100)

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Final Accuracy Audit Dashboard")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') 

        # --- FIX: ROBUST MASTER LIST EXTRACTION ---
        # Explicitly taking all names from the 2nd column (Column B)
        master_docs_raw = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        
        # Cleaning list (Removing headers like 'MARCH ENT' or 'DOC LIST')
        master_list = [d for d in master_docs_raw if len(d) > 5 and 'DOC LIST' not in d and d != 'MARCH ENT']

        final_df = process_data(raw_df, master_list)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Lab Report"])

        with tab1:
            st.sidebar.header("Auditor Filters")
            valid_dropdown = sorted([d for d in master_list if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
            selected_doc = st.sidebar.selectbox("Filter by Doctor", ["All Doctors"] + valid_dropdown)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            st.subheader(f"Results for: {selected_doc}")
            st.metric("Total Doctor Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report: Specifically Rohit Rungta or Other Lab Refer entries
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
            st.subheader("Other Lab & Rohit Rungta Report")
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: {e}")
