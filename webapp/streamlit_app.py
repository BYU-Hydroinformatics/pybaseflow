import streamlit as st
import baseflowx

st.set_page_config(page_title="Baseflow Explorer")

st.title("Baseflow Explorer")

st.write(
    "An interactive web app for comparing baseflow separation methods on "
    "USGS streamflow data. Powered by "
    f"[`baseflowx`](https://pypi.org/project/baseflowx/) v{baseflowx.__version__}."
)

st.info("Under construction — full UI coming soon.")

st.markdown(
    "Source: [BYU-Hydroinformatics/baseflowx]"
    "(https://github.com/BYU-Hydroinformatics/baseflowx)"
)
