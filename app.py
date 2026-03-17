import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম ক্লিন করার ফাংশন
def clean_name(name):
    if pd.isna(name): return ""
    name = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return name.upper()

st.set_page_config(page_title="Doctor Referral System", layout="wide")

st.title("🩺 Doctor Referral & Analytics Dashboard")
st.markdown("Upload the excel file to generate referral reports and visual analytics.")

uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    # ২য় শিট থেকে ডেটা পড়া (index 1)
    df = pd.read_excel(uploaded_file, sheet_name=1)
    
    # ডেটা প্রেপারেশন
    df['Cleaned_Doctor'] = df['Doctor Name'].apply(clean_name)
    
    # ১. রোহিত রুংটাকে বাদ দেওয়া
    df = df[df['Cleaned_Doctor'] != "ROHIT RUNGTA"]
    
    # ২. ক্যালকুলেশন
    df['Net Amount'] = df['Gross Amount'] - df['Discount']
    df['Discount_Pct'] = (df['Discount'] / df['Gross Amount']) * 100
    
    def calculate_referral(row):
        # MARCH ENT কন্ডিশন
        excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
        if str(row['Department']).upper() == "MARCH ENT" and row['Cleaned_Doctor'] in excluded_docs:
            return 0
        
        # ২৫% লজিক
        if row['Discount_Pct'] > 25:
            return 0
        else:
            balance_pct = (25 - row['Discount_Pct']) / 100
            return row['Net Amount'] * balance_pct

    df['Referral Amount'] = df.apply(calculate_referral, axis=1)

    # --- ভিজ্যুয়ালাইজেশন (Plotly) ---
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Doctors by Referral")
        # ডাক্তার অনুযায়ী সামারি
        doc_summary = df.groupby('Doctor Name')['Referral Amount'].sum().reset_index().sort_values(by='Referral Amount', ascending=False).head(10)
        
        fig = px.bar(doc_summary, x='Referral Amount', y='Doctor Name', 
                     orientation='h', 
                     title="Top 10 Referral Earners",
                     color='Referral Amount',
                     color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Referral Distribution by Dept")
        dept_summary = df.groupby('Department')['Referral Amount'].sum().reset_index()
        fig2 = px.pie(dept_summary, values='Referral Amount', names='Department', 
                      title="Department wise Referral %",
                      hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    # ফাইনাল টেবিল
    st.subheader("Detailed Data Table")
    st.dataframe(df[['Doctor Name', 'Department', 'Gross Amount', 'Discount', 'Net Amount', 'Referral Amount']], use_container_width=True)

    # ডাউনলোড
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Full Report", csv, "referral_final_report.csv", "text/csv")
