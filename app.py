import streamlit as st
import pandas as pd
import plotly.express as px

# Professional Page Config
st.set_page_config(page_title="Referral Audit Dashboard", layout="wide")

def process_referral_data(df):
    # Standardizing Columns
    gross_col, disc_col = 'Gross Amount', 'Discount'
    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
    df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
    
    # 100% Accuracy Logic: Gross - Discount = Net
    df['Calculated Net Amount'] = df[gross_col] - df[disc_col]
    df['Disc %'] = (df[disc_col] / df[gross_col]).fillna(0) * 100
    
    # Boss's Logic: 25% Threshold
    def calc_payout(row):
        if row['Disc %'] > 25: return 0
        return row['Calculated Net Amount'] * ((25 - row['Disc %']) / 100)

    df['Referral Payable'] = df.apply(calc_payout, axis=1)
    return df

st.title("🏥 Precision Referral Audit Dashboard")
st.markdown("Automated System for **Doctor** and **Other Lab** Referral Reports.")

uploaded_file = st.file_uploader("Upload Procedure Excel File", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # Loading and Processing
        raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df = process_referral_data(raw_df)

        # SEPARATION LOGIC: Creating two distinct reports
        # 1. Doctor Referral: Where Doctor Name exists and NOT 'SELF'
        doc_df = df[(df['Doctor Name'].notna()) & (df['Doctor Name'] != 'SELF')].copy()
        
        # 2. Other Lab Referral: Where 'Other Lab Refer' is not empty
        lab_df = df[df['Other Lab Refer'].notna() & (df['Other Lab Refer'] != "")].copy()

        # Tabs for clear separation as requested by Boss
        tab1, tab2, tab3 = st.tabs(["👨‍⚕️ Doctor Referral Report", "🔬 Other Lab Referral", "📊 Consolidated Summary"])

        with tab1:
            st.header("Doctor Payout Audit")
            doc_list = ["All Doctors"] + sorted(doc_df['Doctor Name'].unique().tolist())
            sel_doc = st.selectbox("Filter by Doctor", doc_list)
            
            final_doc_df = doc_df if sel_doc == "All Doctors" else doc_df[doc_df['Doctor Name'] == sel_doc]
            
            # Metric for Doctor
            st.metric("Total Payable (Doctor)", f"₹ {final_doc_df['Referral Payable'].sum():,.2f}")
            st.dataframe(final_doc_df[['DATE', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Calculated Net Amount', 'Disc %', 'Referral Payable']])

        with tab2:
            st.header("Other Lab Referral Audit")
            lab_list = ["All Labs"] + sorted(lab_df['Other Lab Refer'].unique().tolist())
            sel_lab = st.selectbox("Filter by Lab", lab_list)
            
            final_lab_df = lab_df if sel_lab == "All Labs" else lab_df[lab_df['Other Lab Refer'] == sel_lab]
            
            st.metric("Total Payable (Lab)", f"₹ {final_lab_df['Referral Payable'].sum():,.2f}")
            st.dataframe(final_lab_df[['DATE', 'Pt. Name', 'Other Lab Refer', 'Gross Amount', 'Discount', 'Calculated Net Amount', 'Disc %', 'Referral Payable']])

        with tab3:
            st.header("Executive Summary")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Top 10 Doctors by Payout")
                fig = px.bar(doc_df.groupby('Doctor Name')['Referral Payable'].sum().nlargest(10).reset_index(), 
                             x='Referral Payable', y='Doctor Name', orientation='h', color_continuous_scale='Blues')
                st.plotly_chart(fig)
            with c2:
                st.subheader("Payout Distribution")
                pie_data = pd.DataFrame({
                    'Category': ['Doctor Referral', 'Other Lab Referral'],
                    'Amount': [doc_df['Referral Payable'].sum(), lab_df['Referral Payable'].sum()]
                })
                st.plotly_chart(px.pie(pie_data, names='Category', values='Amount', hole=0.4))

        # Download Buttons
        st.sidebar.markdown("### Export Reports")
        st.sidebar.download_button("Download Doctor Report", doc_df.to_csv(index=False).encode('utf-8'), "Doctor_Referral.csv")
        st.sidebar.download_button("Download Lab Report", lab_df.to_csv(index=False).encode('utf-8'), "Lab_Referral.csv")

    except Exception as e:
        st.error(f"Error: {e}")
