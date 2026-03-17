import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম ক্লিন করার ফাংশন
def clean_name(name):
    if pd.isna(name): return ""
    cleaned = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return cleaned.upper()

# কলাম খুঁজে বের করার স্মার্ট ফাংশন
def find_column(df, keywords):
    for col in df.columns:
        if any(key.lower() in str(col).lower() for key in keywords):
            return col
    return None

st.set_page_config(page_title="Referral Calculator Pro", layout="wide")
st.title("📊 Consolidated Doctor Referral Report")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx'", type=["xlsx"])

if uploaded_file:
    try:
        # ১. সব শিট লোড করা
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        
        combined_data = []

        for sheet_name, df in all_sheets.items():
            # কলামের নামের স্পেস ক্লিন করা
            df.columns = [str(c).strip() for c in df.columns]
            
            # স্মার্টলি কলাম খুঁজে বের করা
            doc_col = find_column(df, ["doc", "doctor"])
            gross_col = find_column(df, ["gross", "total amount"])
            disc_col = find_column(df, ["disc", "discount"])
            dept_col = find_column(df, ["dept", "department"])

            if doc_col and gross_col:
                # প্রয়োজনীয় ডাটা রিফরম্যাট করা
                temp_df = pd.DataFrame()
                temp_df['Doctor'] = df[doc_col].apply(clean_name)
                temp_df['Original_Name'] = df[doc_col]
                temp_df['Gross'] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
                temp_df['Disc'] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0) if disc_col else 0
                temp_df['Dept'] = df[dept_col].astype(str).str.upper() if dept_col else "UNKNOWN"
                temp_df['Source_Sheet'] = sheet_name
                combined_data.append(temp_df)

        if not combined_data:
            st.error("কোনো শিটে উপযুক্ত কলাম পাওয়া যায়নি!")
        else:
            # ২. সব শিটকে এক করা
            final_df = pd.concat(combined_data, ignore_index=True)

            # ৩. ফিল্টারিং (রোহিত রুংটাকে বাদ দেওয়া)
            final_df = final_df[final_df['Doctor'] != "ROHIT RUNGTA"]

            # ৪. ক্যালকুলেশন লজিক
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
                if "MARCH ENT" in row['Dept'] and row['Doctor'] in excluded_docs:
                    return 0
                
                if row['Discount_Pct'] > 25:
                    return 0
                else:
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # ৫. সামারি রিপোর্ট (ডাক্তার অনুযায়ী)
            summary = final_df.groupby('Original_Name').agg({
                'Gross': 'sum',
                'Disc': 'sum',
                'Net Amount': 'sum',
                'Referral': 'sum'
            }).reset_index().sort_values(by='Referral', ascending=False)

            # ড্যাশবোর্ড
            st.success(f"সফলভাবে {len(all_sheets)} টি শিট কম্বাইন করা হয়েছে!")
            
            m1, m2 = st.columns(2)
            m1.metric("Total Net Billing", f"₹ {summary['Net Amount'].sum():,.2f}")
            m2.metric("Total Payout", f"₹ {summary['Referral'].sum():,.2f}")

            st.plotly_chart(px.bar(summary.head(10), x='Referral', y='Original_Name', orientation='h', title="Top 10 Doctor Payouts"))

            st.subheader("Detailed Consolidated Report")
            st.dataframe(summary.style.format(precision=2), use_container_width=True)

            # ডাউনলোড
            csv = summary.to_csv(index=False).encode('utf-8')
            st.download_button("📥 ডাউনলোড কম্বাইনড রিপোর্ট", csv, "Consolidated_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"মার্জিং এ সমস্যা হয়েছে: {str(e)}")
