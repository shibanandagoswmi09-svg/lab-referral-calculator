import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df, master_doc_list):
    # Standardizing numeric columns
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
    
    # Excluded Doctors List
    excluded_doctors = ['DR. ARJUN DASGUPTA', 'DR. CHIRANJIT DUTTA', 'DR. NVK MOHAN', 'ROHIT RUNGTA']
    
    def calculate_payout(row):
        doc_name_raw = str(row['Doctor Name']).strip().upper()
        
        # 1. Check if Doc Name matches any name in Sheet 2 (Partial Match)
        is_valid = False
        for m_doc in master_doc_list:
            if m_doc in doc_name_raw:
                is_valid = True
                break
        
        # 2. Check for exclusions
        is_excluded = any(ex in doc_name_raw for ex in excluded_doctors)
        
        if not is_valid or is_excluded or doc_name_raw == 'SELF':
            return 0
        
        # 3. Apply 25% Logic
        if row['Disc %'] > 25:
            return 0
        else:
            return row['Net Amount'] * ((25 - row['Disc %']) / 100)

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Final Accuracy Referral Audit")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx'])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)
        
        # Checking for correct sheets
        sheet_list = xls.sheet_names
        ref_sheet = 'Doc Ref.' if 'Doc Ref.' in sheet_list else sheet_list[0]
        name_sheet = 'Doc Name' if 'Doc Name' in sheet_list else None
        
        if not name_sheet:
            st.error("Error: Sheet named 'Doc Name' not found!")
        else:
            raw_df = pd.read_excel(xls, sheet_name=ref_sheet)
            doc_name_df = pd.read_excel(xls, sheet_name=name_sheet)
            
            # Extracting Doctor Names from ALL cells in Sheet 2 (Cleaning headers)
            all_text = doc_name_df.stack().astype(str).str.strip().str.upper().unique().tolist()
            master_docs = [t for t in all_text if len(t) > 5 and 'DOC LIST' not in t and 'MARCH ENT' not in t]

            final_df = process_data(raw_df, master_docs)

            # --- TABS ---
            tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Report", "🔬 Other Lab Report"])

            with tab1:
                # Dropdown with only valid doctors
                dropdown_list = sorted([d for d in master_docs if not any(ex in d for ex in ['ARJUN', 'CHIRANJIT', 'NVK', 'ROHIT'])])
                selected_doc = st.sidebar.selectbox("Choose Doctor", ["All Doctors"] + dropdown_list)
                
                doc_report = final_df.copy()
                if selected_doc != "All Doctors":
                    doc_report = doc_report[doc_report['Doctor Name'].str.upper().str.contains(selected_doc, na=False)]
                
                # Filtering only referral-eligible entries
                doc_report = doc_report[doc_report['Doctor Name'] != 'SELF']
                
                st.subheader(f"Results for: {selected_doc}")
                st.metric("Total Doctor Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
                st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

            with tab2:
                # Lab Report (specifically Other Lab Refer column + Rohit Rungta)
                lab_report = final_df[(final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")) | 
                                      (final_df['Doctor Name'].str.contains('ROHIT RUNGTA', na=False))]
                
                st.subheader("Other Lab Referral (including Rohit Rungta)")
                st.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
                st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Doctor Name', 'Net Amount', 'Disc %', 'Referral Payable']])

    except Exception as e:
        st.error(f"Critical Error: {e}")
