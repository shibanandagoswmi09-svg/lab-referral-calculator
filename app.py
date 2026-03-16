import streamlit as st
import pandas as pd

st.set_page_config(page_title="Final Audit System", layout="wide")

def process_data(df, master_list):
    # Numeric values cleanup
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # STEP 1: Aggregate by Work Order ID (Fixes Dr. Soumya 2-case issue)
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    # Actual Discount Percentage calculation
    grouped['Actual Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Exclusion List (March ENT and Rohit Rungta)
    excluded = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_raw = str(row['Doctor Name']).strip().upper()
        
        # Validation: Is the doctor in Sheet 2 master list?
        is_valid = any(m_doc in doc_raw for m_doc in master_list if len(m_doc) > 5)
        
        # Check for March ENT and Rohit Rungta
        is_excluded = any(ex in doc_raw for ex in excluded)
        
        if not is_valid or is_excluded or doc_raw == 'SELF':
            return 0
        
        # Boss's Condition: If Disc % > 25, No Referral
        if row['Actual Disc %'] > 25:
            return 0
        else:
            # Balance Percentage Payout
            balance_perc = (25 - row['Actual Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🏥 Final Referral Audit Dashboard")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') 

        # Extract Master List from Sheet 2 (Column B)
        # Using a safer way to get names even if there are empty rows
        master_docs = doc_name_df.iloc[:, 1].dropna().astype(str).str.strip().str.upper().unique().tolist()
        master_docs = [d for d in master_docs if len(d) > 5 and 'DOC LIST' not in d and 'MARCH ENT' not in d]

        final_df = process_data(raw_df, master_docs)

        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Settlement", "🔬 Other Lab Settlement"])

        with tab1:
            # Dropdown with only valid doctors
            clean_dropdown = sorted([d for d in master_docs if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
            selected_doc = st.sidebar.selectbox("Filter by Doctor", ["All Doctors"] + clean_dropdown)
            
            report = final_df.copy()
            if selected_doc != "All Doctors":
                report = report[report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            st.metric("Total Doctor Payout", f"₹ {report['Referral Payable'].sum():,.2f}")
            st.dataframe(report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report (Rohit Rungta entries or Other Lab Refer column)
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: Ensure sheet names 'Doc Ref.' and 'Doc Name' are correct. {e}")
