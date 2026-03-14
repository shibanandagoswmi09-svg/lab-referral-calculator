import streamlit as st
import pandas as pd

def calculate_referral(df):
    # Data cleaning: Ensuring numeric values
    df['Gross Amount'] = pd.to_numeric(df['Gross Amount'], errors='coerce').fillna(0)
    df['Discount Amount'] = pd.to_numeric(df['Discount Amount'], errors='coerce').fillna(0)
    
    # 1. Net Amount Logic
    df['Net Amount'] = df['Gross Amount'] - df['Discount Amount']
    
    # 2. Discount Percentage
    # Using 0 to avoid division by zero error
    df['Disc %'] = (df['Discount Amount'] / df['Gross Amount']).fillna(0) * 100
    
    # 3. Referral Logic
    def referral_logic(row):
        if row['Disc %'] > 25:
            return 0
        else:
            # Paying the balance percentage on Net Amount
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    df['Referral Paid'] = df.apply(referral_logic, axis=1)
    return df

st.title("Referral Calculation Dashboard")

uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx'])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # Process Data
    processed_df = calculate_referral(df)
    
    # Detailed Report
    st.write("### Detailed Report")
    st.dataframe(processed_df)
    
    # Summary for Boss
    total_referral = processed_df['Referral Paid'].sum()
    st.metric("Total Referral to be Paid", f"৳ {total_referral:,.2f}")
    
    # Download Button
    csv = processed_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download Processed Report", csv, "referral_report.csv", "text/csv")
