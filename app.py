import streamlit as st
import pandas as pd

st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_data(df):
    # Standardizing numeric columns
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # --- STEP 1: GROUPING BY WORK ORDER ID ---
    # Treats multiple tests as ONE case (Solves Dr. Soumya 2-case issue)
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

st.title("🛡️ Precision Referral Payout Dashboard")
st.markdown("Automated Logic: **Net Amount Basis | 25% Threshold**")

uploaded_file = st.file_uploader("Upload Procedure Excel", type=['xlsx', 'csv'])

if uploaded_file:
    # Read Data
    raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
    
    # Process
    final_df = process_data(raw_df)

    # --- DROPDOWN FILTERS IN SIDEBAR ---
    st.sidebar.header("Filter Reports")
    
    # Doctor Dropdown
    all_docs = ["All Doctors"] + sorted([str(d) for d in final_df['Doctor Name'].unique() if d and d != 'SELF'])
    selected_doc = st.sidebar.selectbox("Select Doctor Name", all_docs)
    
    # Lab Dropdown
    all_labs = ["All Labs"] + sorted([str(l) for l in final_df['Other Lab Refer'].unique() if pd.notna(l) and l != ""])
    selected_lab = st.sidebar.selectbox("Select Lab Refer", all_labs)

    # --- SEPARATING REPORTS ---
    doc_report = final_df[(final_df['Doctor Name'].notna()) & (final_df['Doctor Name'] != 'SELF')].copy()
    lab_report = final_df[final_df['Other Lab Refer'].notna() & (final_df['Other Lab Refer'] != "")].copy()

    # Apply Filters
    if selected_doc != "All Doctors":
        doc_report = doc_report[doc_report['Doctor Name'] == selected_doc]
    
    if selected_lab != "All Labs":
        lab_report = lab_report[lab_report['Other Lab Refer'] == selected_lab]

    # --- UI LAYOUT WITH TABS ---
    tab1, tab2 = st.tabs(["👨‍⚕️ Doctor Referral Report", "🔬 Other Lab Referral Report"])

    with tab1:
        st.subheader(f"Results for: {selected_doc}")
        st.metric("Total Payable (Filtered)", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
        st.dataframe(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

    with tab2:
        st.subheader(f"Results for: {selected_lab}")
        st.metric("Total Payable (Filtered)", f"₹ {lab_report['Referral Payable'].sum():,.2f}")
        st.dataframe(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']])

    # Final Export Button
    st.sidebar.markdown("---")
    st.sidebar.download_button("📥 Download Full Report", final_df.to_csv(index=False), "Referral_Payout_Final.csv")
