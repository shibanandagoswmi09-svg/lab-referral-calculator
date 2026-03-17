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

st.set_page_config(page_title="Doctor Referral Analytics", layout="wide")
st.title("📊 Official Doctor Referral System (Final)")

uploaded_file = st.file_uploader("Upload your NEW 'Procedure.xlsx' file", type=["xlsx"])

if uploaded_file:
    try:
        # নতুন ফাইলের শিটগুলো রিড করা
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            # কলামের নাম ক্লিন করা
            df.columns = [str(c).strip() for c in df.columns]
            
            # কলাম ম্যাপিং (আপনার নতুন ফাইলের কলাম অনুযায়ী)
            doc_col = next((c for c in df.columns if 'doctor name' in c.lower()), None)
            gross_col = next((c for c in df.columns if 'gross amount' in c.lower()), None)
            disc_col = next((c for c in df.columns if 'discount' in c.lower()), None)
            dept_col = next((c for c in df.columns if 'departmentname' in c.lower()), None)

            if doc_col and gross_col:
                temp_df = pd.DataFrame()
                temp_df['Original_Name'] = df[doc_col]
                temp_df['Doctor_ID'] = df[doc_col].apply(super_clean)
                temp_df['Gross'] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
                temp_df['Disc'] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0) if disc_col else 0
                temp_df['Dept_Original'] = df[dept_col] if dept_col else "General"
                temp_df['Sheet_Source'] = sheet_name
                combined_data.append(temp_df)

        if combined_data:
            final_df = pd.concat(combined_data, ignore_index=True)

            # ১. এক্সক্লুশন ফিল্টার (রোহিত রুংটা ও ঘুটগুটিয়াকে পুরোপুরি বাদ)
            exclude_completely = ["ROHITGHUTGUTIYA", "ROHITRUNGTA", "ROHITRUNQTA"]
            final_df = final_df[~final_df['Doctor_ID'].isin(exclude_completely)]

            # ২. ক্যালকুলেশন লজিক
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                # কন্ডিশন ১: এই ৩ জন ডাক্তার মার্চ এন্ট-এর আন্ডারে, তাই জিরো
                strict_zero_docs = ["NVKMOHAN", "ARJUNDASGUPTA", "CHIRAJITDUTTA"]
                if row['Doctor_ID'] in strict_zero_docs:
                    return 0.0

                # কন্ডিশন ২: ২৫% এর বেশি ডিসকাউন্ট হলে ০
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
                    # কন্ডিশন ৩: ব্যালেন্স পার্সেন্টেজ লজিক
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # --- ৩. ড্রপডাউন এবং ড্যাশবোর্ড UI ---
            st.sidebar.header("Navigation")
            doc_list = ["Show All Doctors"] + sorted(final_df['Original_Name'].dropna().unique().tolist())
            selected_doc = st.sidebar.selectbox("🔍 Select Doctor:", doc_list)

            if selected_doc == "Show All Doctors":
                display_df = final_df
            else:
                display_df = final_df[final_df['Original_Name'] == selected_doc]

            # মেট্রিক্স কার্ড
            c1, c2, c3 = st.columns(3)
            c1.metric("Gross Amount", f"₹ {display_df['Gross'].sum():,.2f}")
            c2.metric("Net Amount", f"₹ {display_df['Net Amount'].sum():,.2f}")
            c3.metric("Final Referral", f"₹ {display_df['Referral'].sum():,.2f}")

            st.divider()

            # ৪. চার্ট
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("Top Referrals Breakdown")
                top_data = final_df.groupby('Original_Name')['Referral'].sum().nlargest(10).reset_index()
                st.plotly_chart(px.bar(top_data, x='Referral', y='Original_Name', orientation='h', color='Referral'), use_container_width=True)
            
            with col_chart2:
                st.subheader("Source Analysis")
                st.plotly_chart(px.pie(display_df, values='Referral', names='Sheet_Source', hole=0.4), use_container_width=True)

            # ৫. বিস্তারিত টেবিল
            st.subheader(f"Detailed Logs: {selected_doc}")
            st.dataframe(
                display_df[['Original_Name', 'Dept_Original', 'Sheet_Source', 'Gross', 'Disc', 'Net Amount', 'Discount_Pct', 'Referral']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # ৬. ডাউনলোড
            summary = final_df.groupby('Original_Name').agg({'Gross':'sum', 'Net Amount':'sum', 'Referral':'sum'}).reset_index().sort_values('Referral', ascending=False)
            st.download_button("📥 Download Final Report (CSV)", summary.to_csv(index=False).encode('utf-8'), "Final_Doctor_Report.csv", "text/csv")

    except Exception as e:
        st.error(f"Error in processing file: {e}")
