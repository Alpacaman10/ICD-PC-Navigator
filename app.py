
import streamlit as st
import pandas as pd
import sqlite3
from itertools import product

# Load all CSVs
@st.cache_data
def load_data():
    bezel = pd.read_csv("bezel.csv")
    operator = pd.read_csv("operator.csv")
    button_color = pd.read_csv("button_color.csv")
    contact = pd.read_csv("contact_blocks.csv")
    lens = pd.read_csv("lens color.csv")
    light_units = pd.read_csv("light_units.csv")
    return bezel, operator, button_color, contact, lens, light_units

bezel_df, operator_df, button_color_df, contact_df, lens_df, light_df = load_data()

def get_code(df, label):
    if label == "Any":
        return df["code"].tolist()
    return df[df["label"] == label]["code"].tolist()

# Non-illuminated catalog builder
def generate_non_illuminated_catalogs(bezel_label, operator_label, color_label, contact_block_label):
    bezel_codes = get_code(bezel_df, bezel_label)
    operator_rows = operator_df if operator_label == "Any" else operator_df[operator_df["label"] == operator_label]
    color_codes = get_code(button_color_df, color_label)
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

# Illuminated catalog builder
def generate_illuminated_catalogs(bezel_label, operator_label, lens_color_label, contact_block_label, light_unit_label):
    bezel_codes = get_code(bezel_df, bezel_label)
    operator_rows = operator_df if operator_label == "Any" else operator_df[operator_df["label"] == operator_label]
    lens_codes = get_code(lens_df, lens_color_label)
    contact_block_codes = get_code(contact_df, contact_block_label)

    if light_unit_label == "Any":
        matching_lus = light_df[light_df["color"].isin(lens_codes)]
    else:
        matching_lus = light_df[light_df["color"] == light_unit_label]

    results = []
    for bezel, op_row, lens in product(bezel_codes, operator_rows.itertuples(), lens_codes):
        if op_row.code in ["DG", "DGH"] and bezel != "M22":
            continue

        op_string = f"{op_row.code}-{lens}"
        op_only_cat = f"{bezel}L-{op_string}"
        buttonless_op = f"{bezel}L-{op_row.code}-X"
        button_lens = f"M22-XDL-{lens}"

        for _, lu in matching_lus.iterrows():
            lu_code = lu["code"]
            voltage = lu["lu_voltage"]

            for cb in contact_block_codes:
                cat_number = f"{bezel}L-{op_string}-{cb}-{lu_code}"
                results.append({
                    "Type": "Complete Illuminated Device",
                    "Catalog Number": cat_number,
                    "Voltage": voltage,
                    "Sub-Components": [
                        f"Operator Only: {op_only_cat}",
                        f"Buttonless Operator: {buttonless_op}",
                        f"Lens: {button_lens}",
                        f"Contact Block: M22-{cb}",
                        f"Light Unit: M22-LED-{lu_code}"
                    ]
                })

    return pd.DataFrame(results)

# Streamlit UI
st.set_page_config(page_title="M22 Pushbutton Configurator")
st.title("Eaton M22 Pushbutton Configurator")

tabs = st.tabs(["Non-Illuminated", "Illuminated"])

with tabs[0]:
    st.header("Non-Illuminated Pushbuttons")
    bezel_choice = st.selectbox("Bezel", ["Any"] + bezel_df["label"].tolist())
    operator_choice = st.selectbox("Operator", ["Any"] + operator_df["label"].tolist())
    color_choice = st.selectbox("Button Color", ["Any"] + button_color_df["label"].tolist())
    disable_cb = operator_choice == "Flush with guard (Silver only)"
    contact_block_choice = st.selectbox("Contact Block", ["Any"] + contact_df["label"].tolist(), disabled=disable_cb)
    show_complete_only = st.checkbox("Only show complete devices (includes contact blocks)", key="ni_complete")

    if st.button("Generate Non-Illuminated Catalog Numbers"):
        st.session_state["non_illuminated_df"] = generate_non_illuminated_catalogs(
            bezel_choice, operator_choice, color_choice, contact_block_choice
        )

    if "non_illuminated_df" in st.session_state:
        df = st.session_state["non_illuminated_df"]
        if show_complete_only:
            df = df[df["Type"] == "Complete Device"]
        st.dataframe(df[["Type", "Catalog Number"]])
        selected = st.selectbox("Expand a part", df["Catalog Number"].tolist(), key="ni_select")
        if st.checkbox("Show Sub-Components", key="ni_expand"):
            match = df[df["Catalog Number"] == selected]
            for row in match.itertuples():
                st.markdown(f"**{row._2}**")
                for comp in row._3:
                    st.markdown(f"- {comp}")

with tabs[1]:
    st.header("Illuminated Pushbuttons")
    bezel_choice = st.selectbox("Bezel", ["Any"] + bezel_df["label"].tolist(), key="ibz")
    operator_choice = st.selectbox("Operator", ["Any"] + operator_df["label"].tolist(), key="iop")
    lens_choice = st.selectbox("Lens Color", ["Any"] + lens_df["label"].tolist(), key="lens")
    contact_block_choice = st.selectbox("Contact Block", ["Any"] + contact_df["label"].tolist(), key="ilu_cb")
    light_unit_choice = st.selectbox("Light Unit Color", ["Any"] + light_df["color"].unique().tolist(), key="lu")

    if st.button("Generate Illuminated Catalog Numbers"):
        st.session_state["illuminated_df"] = generate_illuminated_catalogs(
            bezel_choice, operator_choice, lens_choice, contact_block_choice, light_unit_choice
        )

    if "illuminated_df" in st.session_state:
        df = st.session_state["illuminated_df"]
        st.dataframe(df[["Catalog Number", "Voltage"]])
        selected = st.selectbox("Expand a part", df["Catalog Number"].tolist(), key="il_select")
        if st.checkbox("Show Sub-Components", key="il_expand"):
            match = df[df["Catalog Number"] == selected]
            for row in match.itertuples():
                st.markdown(f"**{row._1}**")
                for comp in row._4:
                    st.markdown(f"- {comp}")
