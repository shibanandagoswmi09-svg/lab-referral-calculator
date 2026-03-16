import streamlit as st
import pandas as pd

st.set_page_config(page_title="100% Accurate Referral Audit", layout="wide")

def process_data_with_logic(df):
    # Standardizing numeric columns
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount'] = pd.to_numeric(df['Discount'], errors='coerce').fillna(0)
    
    # IMPORTANT: Grouping by Work Order ID to treat multiple tests as ONE case
    # This prevents duplicate counts for Dr. Soumya Chatterjee or others
    grouped = df.groupby('Work Order ID').agg({
        'DATE': 'first',
        'Pt. Name': 'first',
        'Doctor Name': 'first',
        'Other Lab Refer': 'first',
        'Gross Amount': 'sum',
        'Discount': 'sum'
    }).reset_index()

    # Apply Boss's Logic
    grouped['Net Amount'] = grouped['Gross Amount'] - grouped['Discount']
    
    # Calculate Real Discount Percentage for the whole case
    # If Gross is 0, Disc % is 0
    grouped['Actual Disc %'] = (grouped['Discount'] / grouped['Gross Amount']).fillna(0) * 100
    
    # Condition: If Disc % > 25, No Referral. Else, Balance % on Net.
    def calculate_payout(row):
        if row['Actual Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Actual Disc %']) / 100
            return row['Net Amount'] * balance_perc

    grouped['Referral Payable'] = grouped.apply(calculate_payout, axis=1)
    return grouped

st.title("🛡️ Precision Referral Payout Dashboard")
st.markdown("Condition: **Net Amount Basis | 25% Threshold | Balance Payout**")

uploaded_file = st.file_uploader("Upload Procedure Excel", type=['xlsx'])

if uploaded_file:
    try:
        # Step 1: Read all sheets
        xls = pd.ExcelFile(uploaded_file)
        
        # We focus on sheets that contain data like 'Doc Ref.' or 'Other Lab Ref.'
        # If specific sheets exist, we use them, otherwise use the first sheet
        sheet_names = xls.sheet_names
        main_sheet = 'Doc Ref.' if 'Doc Ref.' in sheet_names else sheet_names[0]
        
        raw_df = pd.read_excel(xls, sheet_name=main_sheet)
        
        # Step 2: Process with logic
        final_df = process_data_with_logic(raw_df)

        # Step 3: Clear Separation for Boss
        # Doctor Report: Exclude 'SELF' and rows where Doctor Name is null
        doc_report = final_df[(final_df['Doctor Name'].notna()) & (final_df['Doctor Name'] != 'SELF')].copy()
        
        # Lab Report: Where 'Other Lab Refer' has data
        lab_report = final_df[final_df['Other Lab Refer'].notna()].copy()

        # UI Layout with Tabs
        tab1, tab2, tab3 = st.tabs(["👨‍⚕️ Doctor Wise Report", "🔬 Other Lab Wise Report", "📊 Summary Audit"])

        with tab1:
            st.subheader("Doctor Payout Details")
            # Grouping by Doctor for the final summary table
            doc_sum = doc_report.groupby('Doctor Name').agg({
                'Work Order ID': 'count',
                'Gross Amount': 'sum',
                'Discount': 'sum',
                'Net Amount': 'sum',
                'Referral Payable': 'sum'
            }).rename(columns={'Work Order ID': 'Total Cases'}).reset_index()
            
            st.dataframe(doc_sum.style.format({'Net Amount': '{:.2f}', 'Referral Payable': '{:.2f}'}))
            
            st.markdown("#### Patient Wise Audit Trail (Doctor)")
            st.write(doc_report[['DATE', 'Work Order ID', 'Pt. Name', 'Doctor Name', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab2:
            st.subheader("Lab Payout Details")
            lab_sum = lab_report.groupby('Other Lab Refer').agg({
                'Work Order ID': 'count',
                'Gross Amount': 'sum',
                'Discount': 'sum',
                'Net Amount': 'sum',
                'Referral Payable': 'sum'
            }).rename(columns={'Work Order ID': 'Total Cases'}).reset_index()
            
            st.dataframe(lab_sum.style.format({'Net Amount': '{:.2f}', 'Referral Payable': '{:.2f}'}))
            
            st.markdown("#### Patient Wise Audit Trail (Lab)")
            st.write(lab_report[['DATE', 'Work Order ID', 'Pt. Name', 'Other Lab Refer', 'Net Amount', 'Actual Disc %', 'Referral Payable']])

        with tab3:
            st.header("Executive Overview")
            c1, c2 = st.columns(2)
            c1.metric("Total Doctor Payout", f"₹ {doc_report['Referral Payable'].sum():,.2f}")
            c2.metric("Total Lab Payout", f"₹ {lab_report['Referral Payable'].sum():,.2f}")

        # Sidebar Download
        st.sidebar.download_button("Download Full Audit CSV", final_df.to_csv(index=False), "Final_Referral_Report.csv")

    except Exception as e:
        st.error(f"Error reading file: {e}")
