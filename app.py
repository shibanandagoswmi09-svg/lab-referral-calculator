import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম এবং ডাটা ক্লিন করার জন্য শক্তিশালী ফাংশন
def super_clean(text):
    if pd.isna(text): return ""
    # Dr. ডট, স্পেস সব বাদ দিয়ে শুধু ক্যাপিটাল লেটার রাখবে
    text = re.sub(r'^(dr\.|dr|dr )', '', str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r'[^A-Z]', '', text.upper()) 
    return cleaned

st.set_page_config(page_title="Referral Calculator Pro", layout="wide")
st.title("📊 Doctor Referral Analytics (Strict Logic)")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx'", type=["xlsx"])

if uploaded_file:
    try:
        # সব শিট লোড করা হচ্ছে
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            
            # স্মার্ট কলাম ম্যাপিং
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
                temp_df['Dept_Original'] = df[dept_col] if dept_col else "Unknown"
                temp_df['Dept_Cleaned'] = temp_df['Dept_Original'].astype(str).apply(super_clean)
                temp_df['Sheet_Source'] = sheet_name
                combined_data.append(temp_df)

        if combined_data:
            final_df = pd.concat(combined_data, ignore_index=True)

            # ১. রোহিত রুংটাকে সম্পূর্ণ বাদ দেওয়া
            final_df = final_df[final_df['Doctor_ID'] != "ROHITRUNGTA"]

            # ২. মূল ক্যালকুলেশন লজিক
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                # কন্ডিশন ১: নির্দিষ্ট ৩ জন ডাক্তার এবং MARCH ENT লজিক
                special_docs = ["ARJUNDASGUPTA", "CHIRAJITDUTTA", "NVKMOHAN"]
                
                # যদি ডিপার্টমেন্টের মধ্যে MARCH অথবা ENT যেকোনো একটি শব্দ থাকে
                dept_str = row['Dept_Cleaned']
                is_excluded_dept = ("MARCH" in dept_str) or ("ENT" in dept_str)
                
                if is_excluded_dept and (row['Doctor_ID'] in special_docs):
                    return 0.0  # কোনো রেফারাল পাবে না

                # কন্ডিশন ২: ২৫% এর বেশি ডিসকাউন্ট হলে ০
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
                    # কন্ডিশন ৩: ২৫% এর কম হলে ব্যালেন্স পার্সেন্টেজ
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # --- ড্রপডাউন এবং ড্যাশবোর্ড ---
            st.divider()
            doc_list = ["Show All"] + sorted(final_df['Original_Name'].dropna().unique().tolist())
            selected_doc = st.selectbox("🎯 নির্দিষ্ট ডাক্তার বেছে নিন:", doc_list)

            if selected_doc == "Show All":
                display_df = final_df
            else:
                display_df = final_df[final_df['Original_Name'] == selected_doc]

            # মেট্রিক্স
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Gross", f"₹ {display_df['Gross'].sum():,.2f}")
            m2.metric("Total Net", f"₹ {display_df['Net Amount'].sum():,.2f}")
            m3.metric("Payable Referral", f"₹ {display_df['Referral'].sum():,.2f}")

            # --- ভিজ্যুয়ালাইজেশন (Charts) ---
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Top 10 Doctor Wise Payout")
                chart_data = final_df.groupby('Original_Name')['Referral'].sum().nlargest(10).reset_index()
                fig1 = px.bar(chart_data, x='Referral', y='Original_Name', orientation='h', 
                             color='Referral', color_continuous_scale='Reds')
                st.plotly_chart(fig1, use_container_width=True)

            with c2:
                st.subheader("Payout Contribution by Sheet")
                pie_data = display_df.groupby('Sheet_Source')['Referral'].sum().reset_index()
                fig2 = px.pie(pie_data, values='Referral', names='Sheet_Source', hole=0.5)
                st.plotly_chart(fig2, use_container_width=True)

            # বিস্তারিত টেবিল (সবার জন্য বা নির্দিষ্ট ডাক্তারের জন্য)
            st.subheader("📄 Detailed Transaction Report")
            st.dataframe(
                display_df[['Original_Name', 'Dept_Original', 'Sheet_Source', 'Gross', 'Disc', 'Net Amount', 'Discount_Pct', 'Referral']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # এক্সেল ডাউনলোড
            summary_to_download = final_df.groupby('Original_Name').agg({
                'Gross': 'sum',
                'Net Amount': 'sum',
                'Referral': 'sum'
            }).reset_index().sort_values(by='Referral', ascending=False)
            
            st.download_button(
                label="📥 Download Summary CSV",
                data=summary_to_download.to_csv(index=False).encode('utf-8'),
                file_name="Referral_Summary.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Error: {e}")
