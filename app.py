import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Accuracy Audit", layout="wide")

def process_data(df, master_list):
    # Numeric cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # 1. Aggregation by Work Order (Solves Soumya Chatterjee 2-case issue)
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
    
    # Strict Exclusion (March ENT + Rohit Rungta)
    excluded = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_raw = str(row['Doctor Name']).strip().upper()
        
        # Rohit Rungta or Self = 0 in Doctor Tab
        if "ROHIT RUNGTA" in doc_raw or doc_raw == 'SELF':
            return 0
            
        # Flexible Matching with Sheet 2 List
        is_valid = any(m_doc in doc_raw for m_doc in master_list if len(m_doc) > 5)
        
        # March ENT Block
        is_excluded = any(ex in doc_raw for ex in excluded)
        
        if not is_valid or is_excluded:
            return 0
        
        # 25% Logic
        if row['Actual Disc %'] > 25:
            return 0
        else:
            return row['Net Amount'] * ((25 - row['Actual Disc %']) / 100)

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Precision Referral Dashboard")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') 

        # --- FIX: ROBUST MASTER LIST EXTRACTION ---
        # Taking Column B (index 1), skipping headers, and cleaning
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        # Removing non-doctor headers
        master_docs = [d for d in master_docs if len(d) > 5 and 'DOC LIST' not in d and d != 'MARCH ENT']

        final_df = process_data(raw_df, master_docs)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Lab Report"])

        with tab1:
            st.sidebar.header("Audit Filters")
            valid_dropdown = sorted([d for d in master_docs if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
            selected_doc = st.sidebar.selectbox("Select Doctor", ["All Doctors"] + valid_dropdown)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            st.subheader(f"Summary for: {selected_doc}")
            st.metric("Total Doctor Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report: Specific for Other Lab Refer column + Rohit Rungta
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
            st.subheader("Lab Report (Inc. Rohit Rungta)")
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: Ensure sheet names are 'Doc Ref.' and 'Doc Name'. Details: {e}")
