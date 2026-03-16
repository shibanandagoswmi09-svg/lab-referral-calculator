import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df, master_doc_list):
    # Standardizing numeric columns
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # STEP 1: GROUPING BY WORK ORDER ID (Treating multiple tests as ONE case)
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
    
    # Specific Exclusion List
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name_raw = str(row['Doctor Name']).strip().upper()
        
        # Validation: Match against Master List (Sheet 2)
        # We check if any name from our master list is present in the Doctor Name column
        is_valid_doc = any(m_doc in doc_name_raw for m_doc in master_doc_list if len(m_doc) > 3)
        
        # Check for Exclusions
        is_excluded = any(ex_doc in doc_name_raw for ex_doc in excluded_doctors)
        
        if not is_valid_doc or is_excluded or doc_name_raw == 'SELF':
            return 0
        
        # 25% Discount Threshold Logic
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Precision Referral Payout Dashboard")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        raw_df = pd.read_excel(xls, sheet_name='Doc Ref.')
        doc_name_df = pd.read_excel(xls, sheet_name='Doc Name') # Sheet 2
        
        # Extracting Doctor Names from Sheet 2 (Column B or C)
        # We flatten all values and clean them to find valid names
        master_docs = doc_name_df.stack().astype(str).str.strip().str.upper().unique().tolist()
        # Cleaning list: removing headers and short strings
        master_docs = [d for d in master_docs if len(d) > 5 and 'DOC LIST' not in d and 'MARCH ENT' not in d]

        final_df = process_data(raw_df, master_docs)

        # UI LAYOUT
        tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Other Lab Report"])

        # Filters
        st.sidebar.header("Filter Results")
        valid_dropdown_list = sorted([d for d in master_docs if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
        selected_doc = st.sidebar.selectbox("Choose Doctor", ["All Doctors"] + valid_dropdown_list)

        with tab1:
            doc_report = final_df.copy()
            if selected_doc != "All Doctors":
                doc_report = doc_report[doc_report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
            
            # Show only rows where Doctor Name is not empty and not SELF
            doc_report = doc_report[(doc_report['Doctor Name'].notna()) & (doc_report['Doctor Name'] != 'SELF')]
            
            st.subheader(f"Results for: {selected_doc}")
            st.metric("Total Doctor Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
            st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            # Lab Report: Specifically for Other Lab Refer column or Rohit Rungta entries
            lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                  (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
            
            st.subheader("Other Lab Referral Report")
            st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
            st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

    except Exception as e:
        st.error(f"Error: {e}")
        
