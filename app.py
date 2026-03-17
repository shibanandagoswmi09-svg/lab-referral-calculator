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
st.title("📊 Doctor Referral Analytics Dashboard")
st.markdown("---")

uploaded_file = st.file_uploader("Upload your 'Procedure.xlsx' file", type=["xlsx"])

if uploaded_file:
    try:
        # সব শিট লোড করা হচ্ছে
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            # কলামের স্পেস ক্লিন করা
            df.columns = [str(c).strip() for c in df.columns]
            
            # স্মার্ট কলাম ম্যাপিং (আপনার ফাইলের কলাম নামের সাথে মিল রেখে)
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

            # ১. এক্সক্লুশন: রোহিত রুংটাকে বাদ দেওয়া
            final_df = final_df[final_df['Doctor_ID'] != "ROHITRUNGTA"]

            # ২. ক্যালকুলেশন লজিক
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                # MARCH ENT + Specific Doctors Logic
                special_docs = ["ARJUNDASGUPTA", "CHIRAJITDUTTA", "NVKMOHAN"]
                dept_str = row['Dept_Cleaned']
                
                # যদি Dept-এ 'MARCH' অথবা 'ENT' থাকে এবং ডাক্তার যদি ওই ৩ জনের কেউ হয়
                if (("MARCH" in dept_str) or ("ENT" in dept_str)) and (row['Doctor_ID'] in special_docs):
                    return 0.0

                # ২৫% ডিসকাউন্ট থ্রেশহোল্ড লজিক
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # --- 👇 ড্রপডাউন ফিল্টার অংশ 👇 ---
            st.sidebar.header("Filter Options")
            doc_list = ["All Doctors"] + sorted(final_df['Original_Name'].dropna().unique().tolist())
            selected_doc = st.sidebar.selectbox("🔍 Select Doctor:", doc_list)

            # ড্রপডাউন অনুযায়ী ডেটা ফিল্টার
            if selected_doc == "All Doctors":
                display_df = final_df
            else:
                display_df = final_df[final_df['Original_Name'] == selected_doc]

            # ৩. প্রধান মেট্রিক্স (Top Cards)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Gross", f"₹ {display_df['Gross'].sum():,.2f}")
            with c2:
                st.metric("Total Net Billing", f"₹ {display_df['Net Amount'].sum():,.2f}")
            with c3:
                st.metric("Total Payable Referral", f"₹ {display_df['Referral'].sum():,.2f}", delta_color="normal")

            st.markdown("---")

            # ৪. ভিজ্যুয়ালাইজেশন (Charts)
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                if selected_doc == "All Doctors":
                    st.subheader("Top 10 Doctors by Referral")
                    top_10 = final_df.groupby('Original_Name')['Referral'].sum().nlargest(10).reset_index()
                    fig1 = px.bar(top_10, x='Referral', y='Original_Name', orientation='h', color='Referral', color_continuous_scale='Blues')
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.subheader(f"Sheet-wise Split for {selected_doc}")
                    sheet_split = display_df.groupby('Sheet_Source')['Referral'].sum().reset_index()
                    fig1 = px.pie(sheet_split, values='Referral', names='Sheet_Source', hole=0.4)
                    st.plotly_chart(fig1, use_container_width=True)

            with col_chart2:
                st.subheader("Referral Trends")
                fig2 = px.scatter(display_df, x='Discount_Pct', y='Referral', size='Gross', color='Sheet_Source', hover_name='Original_Name')
                st.plotly_chart(fig2, use_container_width=True)

            # ৫. বিস্তারিত রিপোর্ট টেবিল
            st.subheader(f"Detailed Report: {selected_doc}")
            st.dataframe(
                display_df[['Original_Name', 'Dept_Original', 'Sheet_Source', 'Gross', 'Disc', 'Net Amount', 'Discount_Pct', 'Referral']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # ৬. ডাউনলোড বাটন (সামারি)
            summary_csv = final_df.groupby('Original_Name').agg({'Gross':'sum', 'Net Amount':'sum', 'Referral':'sum'}).reset_index()
            st.download_button("📥 Download Summary Report", summary_csv.to_csv(index=False).encode('utf-8'), "Doctor_Summary.csv", "text/csv")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
