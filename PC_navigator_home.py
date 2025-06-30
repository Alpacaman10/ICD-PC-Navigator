import streamlit as st

pg = st.navigation([st.Page("pages/app_pilot_m22.py"), st.Page("pages/app_pilot_10250T.py")])
pg.run()