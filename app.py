import streamlit as st
import pandas as pd
import re

def clean_name(name):
    if pd.isna(name): return ""
    # Remove 'Dr.', 'DR.', dots and extra spaces
    name = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return name.upper()

st.set_page_config(page_title="Doctor Referral Report", layout="wide")
st.title("🩺 Doctor Referral Calculation System")

uploaded_file = st.file_uploader("Upload your Excel file (2nd Sheet will be used)", type=["xlsx"])

if uploaded_file:
    # 2nd sheet লোড করা হচ্ছে
    df = pd.read_excel(uploaded_file, sheet_name=1) 
    
    # কলাম ক্লিনআপ (আপনার এক্সেল অনুযায়ী কলামের নাম মিলিয়ে নেবেন)
    # এখানে আমরা ধরে নিচ্ছি কলাম নাম: 'Doctor Name', 'Department', 'Gross Amount', 'Discount'
    
    # ১. নাম ঠিক করা (Normalization)
    df['Cleaned_Doctor'] = df['Doctor Name'].apply(clean_name)
    
    # ২. নির্দিষ্ট ডাক্তার বাদ দেওয়া (Rohit Rungta)
    df = df[df['Cleaned_Doctor'] != "ROHIT RUNGTA"]
    
    # ৩. ক্যালকুলেশন লজিক
    df['Net Amount'] = df['Gross Amount'] - df['Discount']
    df['Discount_Pct'] = (df['Discount'] / df['Gross Amount']) * 100
    
    def calculate_referral(row):
        # MARCH ENT এর ডাক্তারদের কন্ডিশন
        excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
        if str(row['Department']).upper() == "MARCH ENT" and row['Cleaned_Doctor'] in excluded_docs:
            return 0
        
        # ২৫% ডিসকাউন্ট লজিক
        if row['Discount_Pct'] > 25:
            return 0
        else:
            # ব্যালেন্স পার্সেন্টেজ অন নেট অ্যামাউন্ট
            balance_pct = (25 - row['Discount_Pct']) / 100
            return row['Net Amount'] * balance_pct

    df['Referral Amount'] = df.apply(calculate_referral, axis=1)

    # ফাইনাল রিপোর্ট ডিসপ্লে
    final_report = df[['Doctor Name', 'Department', 'Gross Amount', 'Discount', 'Net Amount', 'Referral Amount']]
    
    st.subheader("Summary Report")
    st.dataframe(final_report)

    # ডাউনলোড অপশন
    csv = final_report.to_csv(index=False).encode('utf-8')
    st.download_button("Download Report as CSV", csv, "referral_report.csv", "text/csv")
