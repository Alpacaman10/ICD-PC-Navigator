
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
    operators_ill = pd.read_csv("operator_illuminated.csv")
    lenses = pd.read_csv("lenses.csv")
    light_units = pd.read_csv("light_units.csv")
    return bezels, operators, colors, contacts, operators_ill, lenses, light_units

bezel_df, operator_df, color_df, contact_df = load_data()

# Mapping from label to code
def get_code(df, label, column):
    if label == "Any":
        return df[f"{column}"].tolist()
    return df[df["label"] == label][f"{column}"].tolist()

# Catalog generation logic
def generate_matching_catalogs(bezel_label, operator_label, color_label, contact_block_label):
    bezel_codes = get_code(bezel_df, bezel_label,"code")
    operator_rows = get_code(operator_df, operator_label,"code")
    buttonless_op_codes = get_code(operator_df,operator_label,"buttonless")
    color_codes = get_code(color_df, color_label,"code")
    contact_block_codes = get_code(contact_df, contact_block_label,"code")
    

    results = []

    for bezel, op_row, op_row_NB, color in product(bezel_codes, operator_rows, buttonless_op_codes, color_codes):
        if op_row in ["DG", "DGH"] and bezel != "M22":
            continue

        style = "flush" if op_row in ["D", "DR", "DG"] else "extended"
        # if op_row.code == "DH":
        #     op_string = f"D-{color}"
        # elif op_row.code == "DRH":
        #     op_string = f"DR-{color}"
        
        op_string = f"{op_row}-{color}"
        op_only_cat = f"{bezel}-{op_string}"
        buttonless_op = f"{bezel}-{op_row_NB}-X"
        if style == "flush":
            button_plate = f"M22-XD-{color}"
        elif style == "extended":
            button_plate = f"M22-XDH-{color}"

        results.append({
            "Type": "Operator Only",
            "Catalog Number": op_only_cat,
            "Sub-Components": [
                f"Buttonless Operator: {buttonless_op}",
                f"Button Plate: {button_plate}"
            ]
        })

        if op_row == "DG":
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
st.title("M22 Product Family")

subtype = st.selectbox("Select Subtype", ["22mm Pushbuttons", "Emergency Stops", "Selector Switches"])

if subtype == "22mm Pushbuttons":
    st.markdown("### Search by Competitor SKU or Select Specs")

    method = st.selectbox("Choose search method", ["Competitor SKU", "Specs"])

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

        elif type_choice == "Illuminated":
            st.info("Illuminated pushbutton configuration is not yet supported.")
