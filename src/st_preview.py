import streamlit as st
from streamlit_file_browser import st_file_browser
import ui_helper

ss = st.session_state
ui_helper.retain_session_state(ss)
st.header("🔍 Preview exported pages")

if ss.export_folder:
    st.write(f"Export folder: `{ss.export_folder}`")
    st.write("Click on a file to preview its contents at the bottom of the page")

    if fb_event := st_file_browser(ss.export_folder, show_delete_file=True):
        if "type" in fb_event:
            if fb_event["type"] == "DELETE_FILE":
                for t in fb_event["target"]:
                    st.write(f"Deleted: {t['path']}")
                if st.button("Refresh"):
                    st.rerun()
            if fb_event["type"] in ["SELECT_FOLDER", "SELECT_FILE"]:
                # st.text_input("Path", fb_event['target']['path'], disabled=True)
                st.write(f"Path: `{fb_event['target']['path']}`")
        else:
            st.write(fb_event)
else:
    st.write("Export pages first in order to preview them")
