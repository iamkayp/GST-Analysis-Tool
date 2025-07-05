import pandas as pd
import streamlit as st
import io

# === Helper Functions ===

def find_column(df, suffix):
    """Find column ending with suffix, ignoring prefix and backticks."""
    for col in df.columns:
        cleaned = col.split('.')[-1].replace('`', '').strip()
        if cleaned == suffix:
            return col
    raise KeyError(f"No column ends with suffix: {suffix}")

def process_gst_data(df):
    col = lambda sfx: find_column(df, sfx)

    df[col('$Vendor_Inv_Date')] = pd.to_datetime(df[col('$Vendor_Inv_Date')], errors='coerce').dt.strftime('%d/%m/%Y')
    df[col('$Date')] = pd.to_datetime(df[col('$Date')], errors='coerce').dt.strftime('%d/%m/%Y')

    filtered_df = df[df[col('$Led_Parent')].isin(['IGST', 'CGST', 'SGST'])]
    unique_keys = filtered_df[col('$Key')].unique()

    output_data = []

    for key in unique_keys:
        key_df = df[df[col('$Key')] == key]

        led_gstin_col = col('$Led_GSTIN')
        vch_gstin_col = col('$Vch_GSTIN')
        gstin = key_df[led_gstin_col].combine_first(key_df[vch_gstin_col]).iloc[0]

        supplier_name = key_df[col('$Party_LedName')].iloc[0]
        invoice_no = key_df[col('$Vendor_Inv_Number')].iloc[0]
        invoice_date = key_df[col('$Vendor_Inv_Date')].iloc[0]
        voucher_no = key_df[col('$VoucherNumber')].iloc[0]
        voucher_date = key_df[col('$Date')].iloc[0]
        vch_type = key_df[col('$VoucherTypeName')].iloc[0]

        revenue_df = key_df[key_df[col('$Nature_Led')] == "PL"]

        for idx, row in revenue_df.iterrows():
            value = row[col('$Amount')] * -1
            particular = row[col('$Particulars')]

            match_row = key_df[key_df[col('$Particulars')] == particular]
            led_group = match_row[col('$Led_Group')].iloc[0] if not match_row.empty else ''
            led_parent = match_row[col('$Led_Parent')].iloc[0] if not match_row.empty else ''

            if idx == revenue_df.index[0]:
                igst = key_df[key_df[col('$Led_Parent')] == 'IGST'][col('$Amount')].sum() * -1
                cgst = key_df[key_df[col('$Led_Parent')] == 'CGST'][col('$Amount')].sum() * -1
                sgst = key_df[key_df[col('$Led_Parent')] == 'SGST'][col('$Amount')].sum() * -1
            else:
                igst = cgst = sgst = 0

            output_data.append({
                'Key': key,
                'Voucher No': voucher_no,
                'Voucher Date': voucher_date,
                'Voucher Type': vch_type,
                'GSTIN': gstin,
                'Name of Supplier': supplier_name,
                'Invoice No.': invoice_no,
                'Invoice Date': invoice_date,
                'Value': value,
                'IGST': igst,
                'CGST': cgst,
                'SGST': sgst,
                'Nature of Transaction': particular,
                'Led Group': led_group,
                'Led Parent': led_parent
            })

    return pd.DataFrame(output_data)

# === Streamlit Interface ===

st.title("GST Analysis Tool")

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        output_df = process_gst_data(df)
        st.success("✅ GST Analysis completed successfully!")

        st.dataframe(output_df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            label="📥 Download GST Analysis Report",
            data=output,
            file_name="GST_analysis_output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ An error occurred: {e}")
