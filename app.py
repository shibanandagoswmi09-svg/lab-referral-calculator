import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম একদম নিখুঁতভাবে ক্লিন করার ফাংশন
def super_clean(text):
    if pd.isna(text): return ""
    # Dr, ডট, স্পেস এবং স্পেশাল ক্যারেক্টার সব বাদ দিয়ে শুধু অক্ষর রাখবে
    text = re.sub(r'^(dr\.|dr|dr )', '', str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r'[^A-Z]', '', text.upper()) # শুধু A-Z রাখবে (N V K হবে NVK)
    return cleaned

st.set_page_config(page_title="Referral Calculator Pro", layout="wide")
st.title("📊 Accurate Doctor Referral Report")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx'", type=["xlsx"])

if uploaded_file:
    try:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            
            # কলাম খোঁজা
            doc_col = next((c for c in df.columns if 'doc' in c.lower()), None)
            gross_col = next((c for c in df.columns if 'gross' in c.lower()), None)
            disc_col = next((c for c in df.columns if 'disc' in c.lower()), None)
            dept_col = next((c for c in df.columns if 'dept' in c.lower()), None)

            if doc_col and gross_col:
                temp_df = pd.DataFrame()
                temp_df['Original_Name'] = df[doc_col]
                temp_df['Doctor_ID'] = df[doc_col].apply(super_clean)
                temp_df['Gross'] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
                temp_df['Disc'] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0) if disc_col else 0
                temp_df['Dept'] = df[dept_col].astype(str).apply(super_clean) if dept_col else "UNKNOWN"
                combined_data.append(temp_df)

        if combined_data:
            final_df = pd.concat(combined_data, ignore_index=True)

            # ১. রোহিত রুংটা ফিল্টার (সরাসরি বাদ)
            final_df = final_df[final_df['Doctor_ID'] != "ROHITRUNGTA"]

            # ২. ক্যালকুলেশন
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                # মার্চ এন্ট এর ওই ৩ জন (সুপার ক্লিন নাম)
                # ARJUN DASGUPTA -> ARJUNDASGUPTA
                # CHIRAJIT DUTTA -> CHIRAJITDUTTA
                # N V K MOHAN -> NVKMOHAN
                special_docs = ["ARJUNDASGUPTA", "CHIRAJITDUTTA", "NVKMOHAN"]
                
                # যদি ডিপার্টমেন্টে 'MARCH' বা 'ENT' থাকে এবং ডাক্তার যদি ওই ৩ জনের কেউ হয়
                if ("MARCH" in row['Dept'] or "ENT" in row['Dept']) and row['Doctor_ID'] in special_docs:
                    return 0
                
                # ২৫% লজিক
                if row['Discount_Pct'] > 25:
                    return 0
                else:
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # সামারি
            summary = final_df.groupby('Original_Name').agg({
                'Gross': 'sum',
                'Net Amount': 'sum',
                'Referral': 'sum'
            }).reset_index().sort_values(by='Referral', ascending=False)

            st.success("রিপোর্ট আপডেট করা হয়েছে। NVK Mohan সহ নির্দিষ্ট ডাক্তারদের চেক করা হয়েছে।")
            st.dataframe(summary.style.format(precision=2), use_container_width=True)
            
            csv = summary.to_csv(index=False).encode('utf-8')
            st.download_button("📥 ডাউনলোড রিপোর্ট", csv, "Final_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
