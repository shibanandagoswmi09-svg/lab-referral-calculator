import streamlit as st
import pandas as pd
import plotly.express as px

# Page Config
st.set_page_config(page_title="Referral Analytics Dashboard", layout="wide")

def calculate_referral(df):
    # Column matching logic (File check)
    gross_col = 'Gross Amount'
    disc_col = 'Discount'
    
    # Cleaning data
    df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
    df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
    
    # Calculations
    df['Net Amount'] = df[gross_col] - df[disc_col]
    df['Disc %'] = (df[disc_col] / df[gross_col]).fillna(0) * 100
    
    # Referral Logic: Balance % of Net Amount if Disc <= 25%
    def get_ref(row):
        if row['Disc %'] > 25:
            return 0
        else:
            balance_perc = (25 - row['Disc %']) / 100
            return row['Net Amount'] * balance_perc

    df['Referral Payable'] = df.apply(get_ref, axis=1)
    return df

# Sidebar for Header
st.sidebar.image("https://www.gstatic.com/images/branding/product/2x/noto_128dp.png", width=50)
st.sidebar.title("Navigation")
st.sidebar.info("Upload your 'Procedure.xlsx' to generate the report.")

st.title("🏥 Medical Referral Automation Dashboard")
st.markdown("---")

uploaded_file = st.file_uploader("Upload Procedure Excel/CSV File", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # File Loading
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        data = calculate_referral(df)

        # --- 1. Top Level Metrics ---
        total_gross = data['Gross Amount'].sum()
        total_net = data['Net Amount'].sum()
        total_ref = data['Referral Payable'].sum()
        avg_disc = data['Disc %'].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Gross", f"৳{total_gross:,.0f}")
        m2.metric("Total Net", f"৳{total_net:,.0f}")
        m3.metric("Total Referral", f"৳{total_ref:,.0f}", delta="Payable")
        m4.metric("Avg. Discount", f"{avg_disc:.1f}%")

        st.markdown("---")

        # --- 2. Visual Analytics ---
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Top 10 Doctors by Referral")
            # Grouping by Doctor Name
            doc_data = data.groupby('Doctor Name')['Referral Payable'].sum().sort_values(ascending=False).head(10).reset_index()
            fig_doc = px.bar(doc_data, x='Referral Payable', y='Doctor Name', orientation='h', color='Referral Payable', color_continuous_scale='Viridis')
            st.plotly_chart(fig_doc, use_container_width=True)

        with col_right:
            st.subheader("Referral Eligibility Split")
            # Logic for Pie Chart
            data['Status'] = data['Disc %'].apply(lambda x: 'Eligible (<=25%)' if x <= 25 else 'Non-Eligible (>25%)')
            fig_pie = px.pie(data, names='Status', values='Net Amount', hole=0.4, color_discrete_sequence=['#00CC96', '#EF553B'])
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- 3. Detailed Data Table ---
        st.subheader("Detailed Transaction Report")
        st.dataframe(data[['DATE', 'Pt. Name', 'Doctor Name', 'Gross Amount', 'Discount', 'Net Amount', 'Disc %', 'Referral Payable']].style.format({'Disc %': '{:.2f}%', 'Referral Payable': '৳{:.2f}'}))

        # --- 4. Export Feature ---
        st.markdown("---")
        csv = data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📩 Download Final Report for Boss",
            data=csv,
            file_name=f"Referral_Report_{pd.Timestamp.now().strftime('%Y-%m-%d')}.csv",
            mime="text/csv",
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
