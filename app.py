import streamlit as st
import pandas as pd
import re
import plotly.express as px

# নাম এবং ডাটা ক্লিন করার জন্য শক্তিশালী ফাংশন
def super_clean(text):
    if pd.isna(text): return ""
    # Dr. ডট, স্পেস সব বাদ দিয়ে শুধু ক্যাপিটাল লেটার রাখবে
    # যেমন: "N.V.K. MOHAN" হয়ে যাবে "NVKMOHAN"
    text = re.sub(r'^(dr\.|dr|dr )', '', str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r'[^A-Z]', '', text.upper()) 
    return cleaned

st.set_page_config(page_title="Doctor Referral Analytics", layout="wide")
st.title("📊 Accurate Doctor Referral System")
st.markdown("---")

uploaded_file = st.file_uploader("Upload 'Procedure.xlsx' (3 Sheets)", type=["xlsx"])

if uploaded_file:
    try:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
        combined_data = []

        for sheet_name, df in all_sheets.items():
            df.columns = [str(c).strip() for c in df.columns]
            
            # কলাম ম্যাপিং
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

            # --- ১. এক্সক্লুশন ফিল্টার (নাম বাদ দেওয়া) ---
            # Rohit Ghutgutiya এবং Rohit Rungta (বানান যাই হোক ক্লিন করে চেক করবে)
            exclude_ids = ["ROHITGHUTGUTIYA", "ROHITRUNGTA", "ROHITRUNQTA"]
            final_df = final_df[~final_df['Doctor_ID'].isin(exclude_ids)]

            # ২. ক্যালকুলেশন লজিক
            final_df['Net Amount'] = final_df['Gross'] - final_df['Disc']
            final_df['Discount_Pct'] = (final_df['Disc'] / final_df['Gross'].replace(0, 1)) * 100

            def calculate_referral(row):
                # MARCH ENT এর আন্ডারে থাকা ৩ জন স্পেশাল ডাক্তার
                special_docs = ["ARJUNDASGUPTA", "CHIRAJITDUTTA", "NVKMOHAN"]
                dept_str = row['Dept_Cleaned']
                
                # N V K Mohan বা N.V.K. Mohan যাই হোক, 'NVKMOHAN' হিসেবে চেক হবে
                is_special_doc = row['Doctor_ID'] in special_docs
                is_excluded_dept = ("MARCH" in dept_str) or ("ENT" in dept_str)
                
                if is_excluded_dept and is_special_doc:
                    return 0.0

                # সাধারণ লজিক: ২৫% ডিসকাউন্ট থ্রেশহোল্ড
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
                    # ব্যালেন্স পার্সেন্টেজ ক্যালকুলেশন
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            final_df['Referral'] = final_df.apply(calculate_referral, axis=1)

            # --- ৩. ড্রপডাউন এবং ড্যাশবোর্ড UI ---
            st.sidebar.header("Navigation")
            doc_list = ["Show All Summary"] + sorted(final_df['Original_Name'].dropna().unique().tolist())
            selected_doc = st.sidebar.selectbox("🔍 Select Doctor to View Details:", doc_list)

            if selected_doc == "Show All Summary":
                display_df = final_df
            else:
                display_df = final_df[final_df['Original_Name'] == selected_doc]

            # মেট্রিক্স কার্ড
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Gross Billing", f"₹ {display_df['Gross'].sum():,.2f}")
            c2.metric("Total Net Billing", f"₹ {display_df['Net Amount'].sum():,.2f}")
            c3.metric("Final Payable Referral", f"₹ {display_df['Referral'].sum():,.2f}")

            st.divider()

            # ৪. ভিজ্যুয়ালাইজেশন (Charts)
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("Top Referrals Breakdown")
                if selected_doc == "Show All Summary":
                    top_docs = final_df.groupby('Original_Name')['Referral'].sum().nlargest(10).reset_index()
                    fig = px.bar(top_docs, x='Referral', y='Original_Name', orientation='h', color='Referral', color_continuous_scale='Reds')
                else:
                    sheet_dist = display_df.groupby('Sheet_Source')['Referral'].sum().reset_index()
                    fig = px.pie(sheet_dist, values='Referral', names='Sheet_Source', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

            with col_chart2:
                st.subheader("Referral vs Discount Analysis")
                fig2 = px.scatter(display_df, x='Discount_Pct', y='Referral', size='Gross', color='Sheet_Source', hover_name='Original_Name')
                st.plotly_chart(fig2, use_container_width=True)

            # ৫. বিস্তারিত ডাটা টেবিল
            st.subheader(f"Detailed Transaction Logs: {selected_doc}")
            st.dataframe(
                display_df[['Original_Name', 'Dept_Original', 'Sheet_Source', 'Gross', 'Disc', 'Net Amount', 'Discount_Pct', 'Referral']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # ৬. ডাউনলোড বাটন
            summary_final = final_df.groupby('Original_Name').agg({'Gross':'sum', 'Net Amount':'sum', 'Referral':'sum'}).reset_index().sort_values('Referral', ascending=False)
            st.download_button("📥 Download Summary CSV", summary_final.to_csv(index=False).encode('utf-8'), "Doctor_Payout_Final.csv", "text/csv")

    except Exception as e:
        st.error(f"Error occurred: {e}")
