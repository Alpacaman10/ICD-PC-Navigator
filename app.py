
import streamlit as st
import sqlite3
import pandas as pd

# Load SQLite database
conn = sqlite3.connect("eaton_icd.db")

st.title("Eaton ICD Panel Component Tool")

# Step 1: Select Product Family
product_family = st.selectbox("Select Product Family", [
    "Pilot Devices", "Power Supplies", "Control Relays", "Terminal Blocks"
])

# Step 2: Filter within Pilot Devices
if product_family == "Pilot Devices":
    subtype = st.radio("Select Subtype", ["22mm Pushbuttons", "Emergency Stops", "Selector Switches"])

    if subtype == "22mm Pushbuttons":
        st.markdown("### Search by Competitor SKU or Select Specs")

        method = st.radio("Choose search method", ["Competitor SKU", "Specs"])

        if method == "Competitor SKU":
            sku_input = st.text_input("Enter Competitor Part Number")
            if sku_input:
                st.markdown("**[Placeholder]** Would query competitor SKU cross-reference table here.")

        elif method == "Specs":
            color = st.selectbox("Color", ["Black", "Red", "Green"])
            actuation = st.selectbox("Actuation", ["momentary"])
            illumination = st.selectbox("Illumination", ["no"])
            contact_config = st.selectbox("Contact Configuration", ["NO", "NC", "2NO", "2NC", "1NO-1NC"])
            bezel = st.selectbox("Bezel Type", ["silver", "black", "metal"])

            query = f'''
                SELECT * FROM pushbuttons
                WHERE color="{color}" AND actuation="{actuation}"
                AND illumination="{illumination}" AND contact_config="{contact_config}"
                AND bezel_type="{bezel}"
            '''
            df = pd.read_sql_query(query, conn)

            if not df.empty:
                st.success(f"Found {len(df)} matching Eaton part(s)")
                st.dataframe(df)

                selected_sku = st.selectbox("Select a part to expand", df["eaton_sku"].tolist())
                if st.checkbox("Expand into Component Parts"):
                    component_query = f'''
                        SELECT component_type, component_sku FROM pushbutton_components
                        WHERE assembled_sku="{selected_sku}"
                    '''
                    parts_df = pd.read_sql_query(component_query, conn)
                    st.subheader("Component Breakdown")
                    st.table(parts_df)
            else:
                st.warning("No matching products found.")

conn.close()
