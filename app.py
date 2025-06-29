
import streamlit as st
import pandas as pd
import sqlite3
from itertools import product

# Load data from CSV files
@st.cache_data
def load_data():
    bezels = pd.read_csv("bezel.csv")
    operators = pd.read_csv("operator.csv")
    colors = pd.read_csv("button_color.csv")
    contacts = pd.read_csv("contact_blocks.csv")
    return bezels, operators, colors, contacts

bezel_df, operator_df, color_df, contact_df = load_data()

# Mapping from label to code
def get_code(df, label):
    if label == "Any":
        return df["code"].tolist()
    return df[df["label"] == label]["code"].tolist()

# Catalog generation logic
def generate_matching_catalogs(bezel_label, operator_label, color_label, contact_block_label):
    bezel_codes = get_code(bezel_df, bezel_label)
    operator_rows = operator_df if operator_label == "Any" else operator_df[operator_df["label"] == operator_label]
    color_codes = get_code(color_df, color_label)
    contact_block_codes = get_code(contact_df, contact_block_label)

    results = []

    for bezel, op_row, color in product(bezel_codes, operator_rows.itertuples(), color_codes):
        if op_row.code in ["DG", "DGH"] and bezel != "M22":
            continue

        op_string = f"{op_row.code}-{color}"
        op_only_cat = f"{bezel}-{op_string}"
        buttonless_op = f"{bezel}-{op_row.code}-X"
        button_plate = f"M22-XD-{color}"

        results.append({
            "Type": "Operator Only",
            "Catalog Number": op_only_cat,
            "Sub-Components": [
                f"Buttonless Operator: {buttonless_op}",
                f"Button Plate: {button_plate}"
            ]
        })

        if op_row.code == "DG":
            continue

        for cb in contact_block_codes:
            complete_cat = f"{bezel}-{op_string}-{cb}"
            results.append({
                "Type": "Complete Device",
                "Catalog Number": complete_cat,
                "Sub-Components": [
                    f"Operator Only: {op_only_cat}",
                    f"Buttonless Operator: {buttonless_op}",
                    f"Button Plate: {button_plate}",
                    f"Contact Block: M22-{cb}"
                ]
            })

    return pd.DataFrame(results)

# Streamlit UI
st.title("Eaton ICD Panel Component Navigator")

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

            type_choice = st.radio("Pushbutton Type", ["Non-Illuminated", "Illuminated"])

            if type_choice == "Non-Illuminated":
                operator_choice = st.selectbox("Operator", ["Any"] + operator_df["label"].tolist())    
                bezel_choice = st.selectbox("Bezel", ["Any"] + bezel_df["label"].tolist())
                color_choice = st.selectbox("Button Color", ["Any"] + color_df["label"].tolist())

                disable_cb = operator_choice == "Flush with guard (Silver only)"
                contact_choices = ["Any"] + contact_df["label"].tolist()
                contact_block_choice = st.selectbox("Contact Block", contact_choices, disabled=disable_cb)

                show_complete_only = st.checkbox("Only show complete devices (includes contact blocks)")

                if "results_df" not in st.session_state:
                    st.session_state["results_df"] = None

                if st.button("Generate Catalog Numbers"):
                    st.session_state["results_df"] = generate_matching_catalogs(
                        bezel_choice, operator_choice, color_choice, contact_block_choice
                    )

                if st.session_state["results_df"] is not None:
                    results_df = st.session_state["results_df"]

                    if show_complete_only:
                        results_df = results_df[results_df["Type"] == "Complete Device"]

                    st.write(f"Found {len(results_df)} matching configurations:")
                    st.dataframe(results_df[["Type", "Catalog Number"]])

                    selected_sku = st.selectbox("Select a part to expand", results_df["Catalog Number"].tolist())
                    if st.checkbox("Expand into Component Parts"):
                        detailed_df = results_df[results_df["Catalog Number"] == selected_sku]
                        
                        conn = sqlite3.connect("eaton_icd.db")
                        query = f'''
                            SELECT component_type, component_sku FROM pushbutton_components
                            WHERE assembled_sku="{selected_sku}"
                        '''
                        component_df = pd.read_sql_query(query, conn)
                        conn.close()

                        st.write("Sub-components for selected catalog numbers:")
                        for _, row in detailed_df.iterrows():
                            st.markdown(f"**{row['Catalog Number']}**")
                            for part in row['Sub-Components']:
                                st.markdown(f"- {part}")
                        # st.write(f"**Catalog Number: {row['Catalog Number']}**")
                        # st.write("Sub-Components:")
                        # for part in row['Sub-Components'].split(", "):
                        #     st.write(f"• {part}")
                        # st.write("Sub-components from database:")
                        # st.dataframe(component_df)
            else:
                st.info("Illuminated pushbutton configuration is not yet supported.")
