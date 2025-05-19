import streamlit as st
from streamlit_file_browser import st_file_browser

ss = st.session_state

if ss.get("export_folder", None):
    st.write("Click on a file to preview its contents at the bottom of the page")

    @st.fragment
    def file_browser_fragment():
        if fb_event := st_file_browser(ss.export_folder, show_delete_file=True):
            location = fb_event["target"]["path"]
            st.write(f"Path: {location}")

    file_browser_fragment()

