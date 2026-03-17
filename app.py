import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম ক্লিন করার ফাংশন
def clean_name(name):
    if pd.isna(name): return ""
    # Dr. বা DR. বা ডট/স্পেস বাদ দিয়ে শুধু নাম রাখবে
    cleaned = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return cleaned.upper()

st.set_page_config(page_title="Referral Calculator", layout="wide")
st.title("🩺 Clinical Referral Payout Dashboard")
st.info("এই অ্যাপটি 'Doc Name' (২য় শিট) এর ওপর ভিত্তি করে রিপোর্ট তৈরি করবে।")

uploaded_file = st.file_uploader("আপনার 'Procedure.xlsx' ফাইলটি আপলোড করুন", type=["xlsx"])

if uploaded_file:
    try:
        # ২য় শিট লোড করা (শিট ইনডেক্স ১ মানে ২য় শিট)
        # শিটের নাম 'Doc Name' হলেও এটি কাজ করবে
        df = pd.read_excel(uploaded_file, sheet_name=1) 

        # কলামের নামের স্পেস ক্লিন করা
        df.columns = [str(c).strip() for c in df.columns]

        # আপনার ফাইলের আসল কলাম ম্যাপ
        doc_col = "Doc. Name"
        dept_col = "Department" 
        gross_col = "GROSS"
        disc_col = "DISC."

        # প্রয়োজনীয় কলামগুলো আছে কি না চেক
        if doc_col not in df.columns or gross_col not in df.columns:
            st.error(f"ভুল: ২য় শিটে '{doc_col}' বা '{gross_col}' কলাম খুঁজে পাওয়া যায়নি।")
            st.write("বর্তমান কলামগুলো:", list(df.columns))
        else:
            # ডাটা প্রসেসিং
            df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
            df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
            
            df['Cleaned_Doctor'] = df[doc_col].apply(clean_name)
            
            # ১. রোহিত রুংটাকে বাদ দেওয়া
            df = df[df['Cleaned_Doctor'] != "ROHIT RUNGTA"]
            
            # ২. ক্যালকুলেশন লজিক
            df['Net Amount'] = df[gross_col] - df[disc_col]
            df['Discount_Pct'] = (df[disc_col] / df[gross_col].replace(0, 1)) * 100
            
            def calculate_referral(row):
                # MARCH ENT এক্সক্লুশন লিস্ট
                excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
                current_dept = str(row.get(dept_col, "")).upper().strip()
                
                # কন্ডিশন: MARCH ENT এর আন্ডারে ওই ৩ জন হলে ০
                if "MARCH ENT" in current_dept and row['Cleaned_Doctor'] in excluded_docs:
                    return 0
                
                # কন্ডিশন: ২৫% এর বেশি ডিসকাউন্ট হলে ০
                if row['Discount_Pct'] > 25:
                    return 0
                else:
                    # ২৫% এর বাকি অংশ রেফারাল
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            df['Referral Amount'] = df.apply(calculate_referral, axis=1)

            # --- ড্যাশবোর্ড ডিসপ্লে ---
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Gross", f"₹ {df[gross_col].sum():,.2f}")
            m2.metric("Total Net", f"₹ {df['Net Amount'].sum():,.2f}")
            m3.metric("Total Payout", f"₹ {df['Referral Amount'].sum():,.2f}", delta_color="normal")

            # চার্ট: ডাক্তার ভিত্তিক পে-আউট
            st.subheader("Doctor-wise Payout Analysis")
            doc_chart_data = df.groupby(doc_col)['Referral Amount'].sum().reset_index()
            fig = px.bar(doc_chart_data.nlargest(15, 'Referral Amount'), 
                         x='Referral Amount', y=doc_col, orientation='h', 
                         color='Referral Amount', color_continuous_scale='Greens')
            st.plotly_chart(fig, use_container_width=True)

            # মেইন টেবিল
            st.subheader("Final Processed Data")
            final_df = df[[doc_col, dept_col, gross_col, disc_col, 'Net Amount', 'Referral Amount']]
            st.dataframe(final_df.style.format(precision=2), use_container_width=True)

            # ডাউনলোড
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 ডাউনলোড কমপ্লিট রিপোর্ট (CSV)", csv, "Referral_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"ফাইলটি পড়তে সমস্যা হয়েছে। নিশ্চিত করুন এটি সঠিক Excel ফাইল। এরর: {e}")
