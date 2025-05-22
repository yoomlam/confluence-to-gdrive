import streamlit as st

# Useful for testing streamlit: https://edit.share.stlite.net/

# Define the pages
# page_2 = st.Page("streamlit_page2.py", title="Page 2")
welcome_page = st.Page("st_welcome.py", title="Welcome")
export_page = st.Page("st_export.py", title="Export Pages", icon="➡️")
preview_page = st.Page("st_preview.py", title="Preview Htmls", icon="🔍")
upload_page = st.Page("st_upload.py", title="Upload to GDrive", icon="🚀")

# Set up navigation
# Caution: session state is not entirely preserved when navigating pages
# https://discuss.streamlit.io/t/session-state-is-not-preserved-when-navigating-pages/48787/2
# "Session State is preserved between pages, but there is a caveat when you specifically mean
#  a key-value pair associated to a widget. Streamlit deletes key-value pairs for widgets when
#  they are not rendered on an app run. In particular, it gets deleted at the end of the app run."
# TLDR: To retain a value in session state, call the widget function.
pg = st.navigation([welcome_page, export_page, preview_page, upload_page])

st.set_page_config(layout="wide")

# Run the selected page
pg.run()
