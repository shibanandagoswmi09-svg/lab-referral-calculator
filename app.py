import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম এবং ডিপার্টমেন্ট একদম নিখুঁতভাবে ক্লিন করার ফাংশন
def super_clean(text):
    if pd.isna(text): return ""
    text = re.sub(r'^(dr\.|dr|dr )', '', str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r'[^A-Z]', '', text.upper()) 
    return cleaned

st.set_page_config(page_title="Referral Calculator Pro", layout="wide")
st.title("📊 Advanced Doctor Referral Analytics")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx'", type=["xlsx"])

if uploaded_file:
    try:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            
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

            # ১. রোহিত রুংটা ফিল্টার (সরাসরি বাদ)
            final_df = final_df[final_df['Doctor_ID'] != "ROHITRUNGTA"]

            # ২. ক্যালকুলেশন
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                special_docs = ["ARJUNDASGUPTA", "CHIRAJITDUTTA", "NVKMOHAN"]
                # MARCH ENT logic
                if ("MARCH" in row['Dept_Cleaned'] or "ENT" in row['Dept_Cleaned']) and row['Doctor_ID'] in special_docs:
                    return 0
                
                # 25% Threshold logic
                if row['Discount_Pct'] > 25:
                    return 0
                else:
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # --- ড্যাশবোর্ড অংশ ---
            st.divider()
            
            # ৩. ড্রপডাউন ফিল্টার (ডাক্তারদের লিস্ট)
            doc_list = ["All Doctors"] + sorted(final_df['Original_Name'].dropna().unique().tolist())
            selected_doc = st.selectbox("🔍 Select a Doctor for Detailed Analysis:", doc_list)

            # ফিল্টার অনুযায়ী ডেটা আলাদা করা
            if selected_doc == "All Doctors":
                filtered_df = final_df
            else:
                filtered_df = final_df[final_df['Original_Name'] == selected_doc]

            # ৪. চার্ট এবং মেট্রিক্স
            col1, col2, col3 = st.columns([1, 1, 1])
            col1.metric("Total Gross Amount", f"₹ {filtered_df['Gross'].sum():,.2f}")
            col2.metric("Total Net Amount", f"₹ {filtered_df['Net Amount'].sum():,.2f}")
            col3.metric("Payable Referral", f"₹ {filtered_df['Referral'].sum():,.2f}")

            st.divider()

            # ৫. ভিজ্যুয়ালাইজেশন (Charts)
            c1, c2 = st.columns(2)
            
            with c1:
                # টপ ১০ ডাক্তারের চার্ট (যদি All Doctors সিলেক্ট থাকে)
                if selected_doc == "All Doctors":
                    st.subheader("Top 10 Doctor Referrals")
                    top_10 = filtered_df.groupby('Original_Name')['Referral'].sum().nlargest(10).reset_index()
                    fig1 = px.bar(top_10, x='Referral', y='Original_Name', orientation='h', 
                                  color='Referral', color_continuous_scale='Viridis')
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.subheader(f"Source-wise Referral for {selected_doc}")
                    sheet_data = filtered_df.groupby('Sheet_Source')['Referral'].sum().reset_index()
                    fig1 = px.pie(sheet_data, values='Referral', names='Sheet_Source', hole=0.4)
                    st.plotly_chart(fig1, use_container_width=True)

            with c2:
                st.subheader("Referral vs Discount Distribution")
                fig2 = px.scatter(filtered_df, x='Discount_Pct', y='Referral', 
                                  color='Sheet_Source', size='Gross', hover_name='Original_Name',
                                  title="Higher Discount = Lower Referral")
                st.plotly_chart(fig2, use_container_width=True)

            # ৬. বিস্তারিত ডাটা টেবিল
            st.subheader("📋 Detailed Transaction Logs")
            st.dataframe(filtered_df[['Original_Name', 'Dept_Original', 'Sheet_Source', 'Gross', 'Disc', 'Net Amount', 'Discount_Pct', 'Referral']].style.format(precision=2), use_container_width=True)

            # ৭. ডাউনলোড বাটন
            final_summary = final_df.groupby('Original_Name').agg({
                'Gross': 'sum',
                'Net Amount': 'sum',
                'Referral': 'sum'
            }).reset_index().sort_values(by='Referral', ascending=False)
            
            csv = final_summary.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Summary Report (CSV)", csv, "Final_Referral_Summary.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
