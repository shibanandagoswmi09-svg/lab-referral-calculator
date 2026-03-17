import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম ক্লিন করার ফাংশন (Dr. বা DR. বাদ দিয়ে বড় হাতের করা)
def clean_name(name):
    if pd.isna(name): return ""
    # Dr. / DR. / DR / Dr (স্পেস বা ডট সহ) রিমুভ করবে
    cleaned = re.sub(r'^(dr\.|dr|dr )', '', str(name), flags=re.IGNORECASE).strip()
    return cleaned.upper()

st.set_page_config(page_title="Referral Calculator", layout="wide")
st.title("🩺 Doctor Referral Payout System")

uploaded_file = st.file_uploader("আপনার এক্সেল ফাইলটি আপলোড করুন", type=["xlsx"])

if uploaded_file:
    try:
        # ২য় শিট লোড করা (index 1)
        df = pd.read_excel(uploaded_file, sheet_name=1)
        
        # কলামের নামের স্পেস ক্লিন করা
        df.columns = [str(c).strip() for c in df.columns]

        # আপনার দেওয়া নির্দিষ্ট কলামের নাম
        doc_col = "DOC LIST FOR DOC PAYOUT"
        dept_col = "Department" # যদি অন্য নাম হয়, এখানে বদলে দিন
        gross_col = "Gross Amount"
        disc_col = "Discount"

        # চেক করা কলামগুলো আছে কি না
        if doc_col not in df.columns:
            st.error(f"ভুল: ফাইলে '{doc_col}' নামের কোনো কলাম পাওয়া যায়নি!")
            st.write("ফাইলে এই কলামগুলো আছে:", list(df.columns))
        else:
            # ১. নাম ঠিক করা
            df['Cleaned_Doctor'] = df[doc_col].apply(clean_name)
            
            # ২. রোহিত রুংটাকে বাদ দেওয়া
            df = df[df['Cleaned_Doctor'] != "ROHIT RUNGTA"]
            
            # ৩. ক্যালকুলেশন লজিক
            # ০ দিয়ে ভাগ হওয়া আটকাতে fillna ব্যবহার করা
            df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
            df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
            
            df['Net Amount'] = df[gross_col] - df[disc_col]
            
            # ডিসকাউন্ট পার্সেন্টেজ বের করা
            df['Discount_Pct'] = (df[disc_col] / df[gross_col].replace(0, 1)) * 100
            
            def calculate_referral(row):
                # MARCH ENT এক্সক্লুশন লিস্ট
                excluded_docs = ["ARJUN DASGUPTA", "CHIRAJIT DUTTA", "NVK MOHAN"]
                
                # যদি Department কলাম থাকে তবেই চেক করবে
                current_dept = str(row.get(dept_col, "")).upper()
                
                if current_dept == "MARCH ENT" and row['Cleaned_Doctor'] in excluded_docs:
                    return 0
                
                # ২৫% ডিসকাউন্ট লজিক
                if row['Discount_Pct'] > 25:
                    return 0
                else:
                    # ব্যালেন্স পার্সেন্টেজ অন নেট অ্যামাউন্ট
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            df['Referral Amount'] = df.apply(calculate_referral, axis=1)

            # --- ভিজ্যুয়ালাইজেশন ---
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Top 10 Referral Earners")
                top_docs = df.groupby(doc_col)['Referral Amount'].sum().reset_index().sort_values(by='Referral Amount', ascending=False).head(10)
                fig = px.bar(top_docs, x='Referral Amount', y=doc_col, orientation='h', color='Referral Amount')
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("Summary Table")
                total_referral = df['Referral Amount'].sum()
                st.metric("Total Payout", f"₹ {total_referral:,.2f}")
                st.write(f"Total Entries: {len(df)}")

            # ডেটা ডিসপ্লে
            st.subheader("Final Processed Report")
            display_cols = [doc_col, gross_col, disc_col, 'Net Amount', 'Referral Amount']
            if dept_col in df.columns: display_cols.insert(1, dept_col)
            
            st.dataframe(df[display_cols].style.format({'Referral Amount': '{:.2f}', 'Net Amount': '{:.2f}'}), use_container_width=True)

            # ডাউনলোড বাটন
            csv = df[display_cols].to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Excel/CSV Report", csv, "doctor_payout_report.csv", "text/csv")

    except Exception as e:
        st.error(f"ফাইল প্রসেস করতে সমস্যা হয়েছে: {e}")
