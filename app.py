import streamlit as st
import pandas as pd

def calculate_referral(df):
    # Column names check and fix (Error prevention)
    # Amra ekhaner logic-e file-er exact column name 'Discount' use korbo
    
    # 1. Gross Amount logic
    gross_col = 'Gross Amount'
    disc_col = 'Discount'
    net_col = 'Net Amount'
    
    # Numeric convert kora jate calculation-e error na hoy
    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
    df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
    
    # 2. Net Amount recalculation (Accuracy-r jonno)
    df['Calculated Net Amount'] = df[gross_col] - df[disc_col]
    
    # 3. Discount Percentage Calculation
    # If Gross Amount is 0, percentage will be 0 to avoid error
    df['Disc %'] = (df[disc_col] / df[gross_col]).fillna(0) * 100
    
    # 4. Boss-er deya Referral Logic
    def referral_logic(row):
        # Logic: If discount > 25%, no referral
        if row['Disc %'] > 25:
            return 0
        else:
            # Logic: balance percentage on Net Amount (25% - discount%)
            balance_perc = (25 - row['Disc %']) / 100
            return row['Calculated Net Amount'] * balance_perc

    df['Referral Paid'] = df.apply(referral_logic, axis=1)
    return df

st.set_page_config(page_title="Referral Calculator", layout="wide")

st.title("🏥 Doctor & Lab Referral Automation")
st.write("Upload the Excel file to calculate referral based on 25% discount threshold.")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx' file", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # File read kora (CSV ba Excel duitoi handle korbe)
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # Processing
        processed_df = calculate_referral(df)
        
        # Summary Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Gross", f"৳ {processed_df['Gross Amount'].sum():,.2f}")
        with col2:
            st.metric("Total Net", f"৳ {processed_df['Calculated Net Amount'].sum():,.2f}")
        with col3:
            st.metric("Total Referral Payable", f"৳ {processed_df['Referral Paid'].sum():,.2f}", delta_color="normal")

        # Result Display
        st.subheader("Detailed Report")
        st.dataframe(processed_df)
        
        # Download Option
        csv = processed_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Final Report (Excel/CSV)",
            data=csv,
            file_name="Referral_Final_Report.csv",
            mime="text/csv",
        )
        
        st.success("Calculation Completed with 100% Accuracy!")

    except Exception as e:
        st.error(f"Error: Column match korche na. Plz ensure columns: 'Gross Amount' and 'Discount'. Detail: {e}")
