import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Referral Audit", layout="wide")

def process_data(df, master_list):
    # Numeric cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # STEP 1: Aggregate by Work Order ID (Arup Kumar Saha logic)
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
    
    # Exclusion List (March ENT)
    march_ent = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']
    
    def calculate_payout(row):
        doc_raw = str(row['Doctor Name']).strip().upper()
        
        # Rohit Rungta or Self = 0 in Doctor Tab
        if "ROHIT RUNGTA" in doc_raw or doc_raw == 'SELF':
            return 0
            
        # Flexible match with Sheet 2
        is_valid = any(m_doc in doc_raw for m_doc in master_list if len(m_doc) > 5)
        is_march_ent = any(ex in doc_raw for ex in march_ent)
        
        if not is_valid or is_march_ent:
            return 0
        
        # 25% Logic
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

        # --- FIX: ROBUST DOCTOR LIST EXTRACTION ---
        # Doc Name sheet-e Column B (index 1) theke data nile result paka
        master_list = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        master_list = [d for d in master_list if len(d) > 5 and 'DOC LIST' not in d and d != 'MARCH ENT']

        final_df = process_data(raw_df, master_list)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Lab Report (Rohit Rungta)"])

        with tab1:
            # Sidebar Filter logic
            st.sidebar.header("Filter Results")
            valid_dropdown = sorted([d for d in master_list if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK'])])
            selected_doc = st.sidebar.selectbox("Select Doctor", ["All Doctors"] + valid_dropdown)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            st.metric("Total Doctor Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report: ROHIT RUNGTA logic
            # File-e ROHIT RUNGTA 'Doctor Name' column-e ache
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))].copy()
            
            # For Lab, calculating flat 25% on Net Amount
            lab_report['Lab Payout'] = lab_report['Net Amount'] * 0.25
            
            st.metric("Total Lab Payout", f"₹ {lab_report['Lab Payout'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Other Lab Refer', 'Net Amount', 'Lab Payout']])

    except Exception as e:
        st.error(f"Error: {e}")
