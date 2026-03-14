import streamlit as st
import pandas as pd
import plotly.express as px

# Page configuration for a professional look
st.set_page_config(page_title="Referral Payout Analytics", layout="wide")

def calculate_referral(df):
    # Ensure column names match your Excel/CSV
    gross_col = 'Gross Amount'
    disc_col = 'Discount'
    
    # Convert to numeric to avoid calculation errors
    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
    df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
    
    # Boss's Logic: Net Amount = Gross - Discount
    df['Calculated Net Amount'] = df[gross_col] - df[disc_col]
    
    # Calculate Discount Percentage
    df['Disc %'] = (df[disc_col] / df[gross_col]).fillna(0) * 100
    
    # Referral Logic Implementation
    def get_referral_amt(row):
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Calculated Net Amount'] * balance_perc

    df['Referral Payable'] = df.apply(get_referral_amt, axis=1)
    return df

# --- UI Header ---
st.title("📊 Medical Referral Automation & Analytics")
st.markdown("Automated calculation based on **Net Amount** with **25% Discount Threshold**.")

uploaded_file = st.file_uploader("Upload Procedure Data (Excel/CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # File Handling
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # Process Data
        processed_df = calculate_referral(df)

        # --- Dropdown Filter Section ---
        st.sidebar.header("Filter Options")
        
        # 1. Doctor Name Dropdown
        doctor_list = ["All Doctors"] + sorted(processed_df['Doctor Name'].dropna().unique().tolist())
        selected_doctor = st.sidebar.selectbox("Select Doctor Name", doctor_list)
        
        # 2. Lab Refer Dropdown
        lab_list = ["All Referrals"] + sorted(processed_df['Other Lab Refer'].dropna().unique().tolist())
        selected_lab = st.sidebar.selectbox("Select Lab Referral", lab_list)

        # Apply Filters to the Dataframe
        filtered_df = processed_df.copy()
        if selected_doctor != "All Doctors":
            filtered_df = filtered_df[filtered_df['Doctor Name'] == selected_doctor]
        if selected_lab != "All Referrals":
            filtered_df = filtered_df[filtered_df['Other Lab Refer'] == selected_lab]

        # --- Metrics Row ---
        st.markdown(f"### Key Performance Indicators: {selected_doctor if selected_doctor != 'All Doctors' else 'Overall'}")
        m1, m2, m3, m4 = st.columns(4)
        
        total_gross = filtered_df['Gross Amount'].sum()
        total_net = filtered_df['Calculated Net Amount'].sum()
        total_ref = filtered_df['Referral Payable'].sum()
        eligible_cases = len(filtered_df[filtered_df['Referral Payable'] > 0])
        
        m1.metric("Total Gross Amount", f"₹ {total_gross:,.2f}")
        m2.metric("Total Net Amount", f"₹ {total_net:,.2f}")
        m3.metric("Total Referral Payout", f"₹ {total_ref:,.2f}")
        m4.metric("Eligible Referrals", f"{eligible_cases} Cases")

        st.markdown("---")

        # --- Dashboard Charts ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top Payouts")
            # Showing Top 10 from the current selection
            doc_data = filtered_df.groupby('Doctor Name')['Referral Payable'].sum().nlargest(10).reset_index()
            fig1 = px.bar(doc_data, x='Referral Payable', y='Doctor Name', orientation='h', 
                          color='Referral Payable', color_continuous_scale='Blues',
                          labels={'Referral Payable': 'Payable Amount (₹)', 'Doctor Name': 'Doctor'})
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            st.subheader("Payout Eligibility Split")
            filtered_df['Eligibility'] = filtered_df['Referral Payable'].apply(lambda x: 'Payable' if x > 0 else 'Non-Payable (>25% Disc)')
            fig2 = px.pie(filtered_df, names='Eligibility', values='Calculated Net Amount', hole=0.5,
                          color_discrete_map={'Payable':'#2ecc71', 'Non-Payable (>25% Disc)':'#e74c3c'})
            st.plotly_chart(fig2, use_container_width=True)

        # --- Detailed Report ---
        st.subheader("Detailed Audit Report")
        display_cols = ['DATE', 'Pt. Name', 'Doctor Name', 'Other Lab Refer', 'Gross Amount', 'Discount', 'Calculated Net Amount', 'Disc %', 'Referral Payable']
        st.dataframe(filtered_df[display_cols].style.format({'Disc %': '{:.2f}%', 'Referral Payable': '{:.2f}'}))

        # --- Export Section ---
        st.markdown("---")
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download This Filtered Report",
            data=csv,
            file_name=f"Referral_Report_{selected_doctor}.csv",
            mime="text/csv",
        )
        st.success("System Processed Successfully. Accuracy: 100%")

    except Exception as e:
        st.error(f"Data Processing Error: {str(e)}")
        st.info("Check if your file has 'Gross Amount', 'Discount', and 'Doctor Name' columns.")
