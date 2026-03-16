import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Audit System", layout="wide")

def process_data(df, master_list):
    # Numeric cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # 1. Grouping by Work Order ID (Arup Kumar Saha-r 2-ti case-er fix)
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
    
    # Excluded Doctors (March ENT list)
    excluded = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN']
    
    def calculate_payout(row):
        doc_raw = str(row['Doctor Name']).strip().upper()
        
        # Rohit Rungta or Self = 0 in Doctor Tab (Boss's Logic)
        if "ROHIT RUNGTA" in doc_raw or doc_raw == 'SELF':
            return 0
            
        # Flexible match with Sheet 2
        is_valid = any(m_doc in doc_raw for m_doc in master_list if len(m_doc) > 5)
        is_excluded = any(ex in doc_raw for ex in excluded)
        
        if not is_valid or is_excluded:
            return 0
        
        # 25% Threshold Condition
        if row['Disc %'] > 25:
            return 0
        else:
            return row['Net Amount'] * ((25 - row['Disc %']) / 100)

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Final Audit-Ready Dashboard")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') 

        # --- SMART DOCTOR LIST (Sheet 2) ---
        # Taking Column B (index 1), cleanup non-doctor text
        master_list = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().tolist()
        master_list = [d for d in master_list if len(d) > 5 and 'DOC LIST' not in d and 'MARCH ENT' not in d]

        final_df = process_data(raw_df, master_list)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Lab Report (Rohit Rungta)"])

        with tab1:
            st.sidebar.header("Filter Results")
            valid_dropdown = sorted([d for d in master_list if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK'])])
            selected_doc = st.sidebar.selectbox("Select Doctor", ["All Doctors"] + valid_dropdown)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            # Show verified Doctor payouts
            st.metric("Total Doctor Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            # LAB LOGIC: Rohit Rungta thakle referral count hobe (as it has 0 discount)
            # Other Lab Refer column OR Doctor Name containing ROHIT RUNGTA
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))].copy()
            
            # Re-calculating for Lab specifically (since they usually have 0% discount)
            lab_report['Lab Payout'] = lab_report['Net Amount'] * 0.25 # Direct 25% as they have 0 disc
            
            st.metric("Total Lab Payout", f"₹ {lab_report['Lab Payout'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Other Lab Refer', 'Net Amount', 'Lab Payout']])

    except Exception as e:
        st.error(f"Error: {e}")
