import streamlit as st
from streamlit_file_browser import st_file_browser

ss = st.session_state

st.header("🔍 Preview exported pages")

if ss.get("export_folder", None):
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
                st.text_input("Selection", fb_event['target']['path'], disabled=True)
        else:
            st.write(fb_event)
else:
    st.write("Export pages first in order to preview them")
