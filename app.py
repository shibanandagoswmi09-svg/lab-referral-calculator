import streamlit as st
import pandas as pd
import re
import plotly.express as px

def clean_name(name):
    if pd.isna(name): return ""
    cleaned = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return cleaned.upper()

st.set_page_config(page_title="Referral Calculator Pro", layout="wide")
st.title("📊 Integrated Doctor Referral Report")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx'", type=["xlsx"])

if uploaded_file:
    try:
        # ১. সব শিট লোড করা
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        sheet_names = list(all_sheets.keys())
        
        # শিট এসাইন করা (আপনার বর্ণনা অনুযায়ী)
        df_doc_ref = all_sheets[sheet_names[0]]    # ১ম শিট: Doc.Ref
        df_master = all_sheets[sheet_names[1]]     # ২য় শিট: Doc Name (Master)
        df_other_lab = all_sheets[sheet_names[2]]  # ৩য় শিট: Other Lab Ref.

        # কলাম ক্লিনআপ
        for df in [df_master, df_doc_ref, df_other_lab]:
            df.columns = [str(c).strip() for c in df.columns]

        # ২. মাষ্টার শিট প্রসেসিং (২য় শিট)
        doc_col = "Doc. Name"
        df_master['Cleaned_Doctor'] = df_master[doc_col].apply(clean_name)
        
        # রোহিত রুংটাকে বাদ দেওয়া
        df_master = df_master[df_master['Cleaned_Doctor'] != "ROHIT RUNGTA"]

        # ৩. শিটগুলো জোড়া লাগানো (Merging/Combining)
        # আমরা ২য় শিটের ডাক্তারদের সাথে বাকি শিটের ডেটা যোগ করছি
        combined_df = pd.concat([df_master, df_doc_ref, df_other_lab], ignore_index=True)
        
        # আবার ক্লিন করা যাতে মার্জিং এ সমস্যা না হয়
        combined_df['Cleaned_Doctor'] = combined_df[doc_col].apply(clean_name)
        combined_df = combined_df[combined_df['Cleaned_Doctor'] != "ROHIT RUNGTA"]

        # ৪. ক্যালকুলেশন লজিক
        gross_col, disc_col = "GROSS", "DISC."
        combined_df[gross_col] = pd.to_numeric(combined_df[gross_col], errors='coerce').fillna(0)
        combined_df[disc_col] = pd.to_numeric(combined_df[disc_col], errors='coerce').fillna(0)
        
        combined_df['Net Amount'] = combined_df[gross_col] - combined_df[disc_col]
        combined_df['Discount_Pct'] = (combined_df[disc_col] / combined_df[gross_col].replace(0, 1)) * 100

        def calculate_referral(row):
            # MARCH ENT Exclusion logic
            excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
            dept = str(row.get("Department", "")).upper()
            
            if "MARCH ENT" in dept and row['Cleaned_Doctor'] in excluded_docs:
                return 0
            
            # Referral Logic: 25% Threshold
            if row['Discount_Pct'] > 25:
                return 0
            else:
                balance_pct = (25 - row['Discount_Pct']) / 100
                return row['Net Amount'] * balance_pct

        combined_df['Referral Amount'] = combined_df.apply(calculate_referral, axis=1)

        # ৫. ফাইনাল রিপোর্ট (গ্রুপ বাই ডাক্তার)
        final_summary = combined_df.groupby([doc_col, 'Cleaned_Doctor']).agg({
            gross_col: 'sum',
            disc_col: 'sum',
            'Net Amount': 'sum',
            'Referral Amount': 'sum'
        }).reset_index()

        # ড্যাশবোর্ড দেখানো
        st.success("সবগুলো শিট থেকে ডেটা কম্বাইন করা হয়েছে!")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Referral (All Sheets)", f"₹ {final_summary['Referral Amount'].sum():,.2f}")
            fig = px.pie(final_summary.nlargest(5, 'Referral Amount'), values='Referral Amount', names=doc_col, title="Top 5 Contributors")
            st.plotly_chart(fig)
        
        with c2:
            st.subheader("Final Payout Table")
            st.dataframe(final_summary[[doc_col, 'Net Amount', 'Referral Amount']].style.format(precision=2))

        # ডাউনলোড
        csv = final_summary.to_csv(index=False).encode('utf-8')
        st.download_button("📥 ডাউনলোড অল-ইন-ওয়ান রিপোর্ট", csv, "Consolidated_Referral_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error merging sheets: {e}")
