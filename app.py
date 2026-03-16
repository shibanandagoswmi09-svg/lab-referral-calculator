import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df):
    # Standardizing numeric columns
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # --- STEP 1: GROUPING BY WORK ORDER ID ---
    # This fixes the Dr. Soumya Chatterjee (2 cases) issue
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    # --- STEP 2: APPLYING BOSS'S LOGIC ---
    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    grouped['Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    def calculate_payout(row):
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🏥 Final Referral Payout System")
st.markdown("Automated Report for **Doctors** & **Other Labs**")

uploaded_file = st.file_uploader("Upload Procedure.xlsx", type=['xlsx', 'csv'])

if uploaded_file:
    # Read Data
    raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    
    # Process
    final_df = process_data(raw_df)

    # --- STEP 3: SEPARATING REPORTS ---
    # Doctor Report: (Excluding 'SELF' and rows where 'Other Lab Refer' is NOT empty)
    # Lab Report: (Rows where 'Other Lab Refer' has a name)
    
    doc_report = final_df[(final_df['Doctor Name'].notna()) & 
                          (final_df['Doctor Name'] != 'SELF') & 
                          (final_df['Other Lab Refer'].isna() | (final_df['Other Lab Refer'] == ""))].copy()
    
    lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")].copy()

    # --- UI LAYOUT ---
    tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Referral Report", "🔬 Other Lab Referral Report"])

    with tab1:
        st.subheader("Doctor-wise Settlement Summary")
        doc_summary = doc_report.groupby('Doctor Name').agg({
            'Work Order ID': 'count',
            'Referral Payable': 'sum'
        }).rename(columns={'Work Order ID': 'Total Cases'}).reset_index()
        st.dataframe(doc_summary.style.format({'Referral Payable': '₹ {:.2f}'}))
        
        st.markdown("---")
        st.write("### Detailed Audit Trail (Doctor)")
        st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Disc %', 'Referral Payable']])

    with tab2:
        st.subheader("Lab-wise Settlement Summary")
        lab_summary = lab_report.groupby('Other Lab Refer').agg({
            'Work Order ID': 'count',
            'Referral Payable': 'sum'
        }).rename(columns={'Work Order ID': 'Total Cases'}).reset_index()
        st.dataframe(lab_summary.style.format({'Referral Payable': '₹ {:.2f}'}))
        
        st.markdown("---")
        st.write("### Detailed Audit Trail (Other Lab)")
        st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Gross Amount', 'Discount', 'Disc %', 'Referral Payable']])

    # Sidebar Metrics
    st.sidebar.header("Executive Summary")
    st.sidebar.metric("Total Doctor Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
    st.sidebar.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
