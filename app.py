import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df, master_doc_list):
    # Numeric conversion
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # STEP 1: GROUPING BY WORK ORDER ID (Fixes Duplicate Issue)
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
    
    # Excluded Doctors as per your requirement
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name = str(row['Doctor Name']).strip().upper()
        
        # FLEXIBLE MATCH: Check if any part of Sheet 2 list matches the row doctor
        is_valid_doc = any(m_doc in doc_name for m_doc in master_doc_list)
        is_excluded = any(ex_doc in doc_name for ex_doc in excluded_doctors)
        
        # 1. Validation Logic
        if not is_valid_doc or is_excluded:
            return 0
        
        # 2. 25% Threshold Logic
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ 100% Precision Referral Dashboard")

uploaded_file = st.file_uploader("Upload Procedure Excel", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name')
        
        # Clean Master Doctor List from Sheet 2 (Taking names from the 2nd column)
        # Assuming names are in the 2nd column (index 1)
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        # Remove extra words like 'MARCH ENT' or headers if any
        master_docs = [d for d in master_docs if 'DOC LIST' not in d and d != 'MARCH ENT']

        final_df = process_data(raw_df, master_docs)

        # UI LAYOUT
        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Other Lab Report"])

        # Filters
        st.sidebar.header("Filter Results")
        doc_list = ["All Doctors"] + sorted([d for d in master_docs if d not in ['ROHIT RUNGTA', 'DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']])
        selected_doc = st.sidebar.selectbox("Choose Doctor", doc_list)

        with tab1:
            doc_report = final_df.copy()
            if selected_doc != "All Doctors":
                doc_report = doc_report[doc_report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            # Show only relevant referrals
            doc_report = doc_report[(doc_report['Doctor Name'] != 'SELF')]
            
            st.subheader(f"Results for: {selected_doc}")
            st.metric("Total Referral Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
            st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")]
            st.subheader("Other Lab Referral (e.g. Rohit Rungta)")
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Net Amount', 'Disc %', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: {e}")
