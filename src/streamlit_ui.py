import streamlit as st

# Useful for testing streamlit: https://edit.share.stlite.net/

# Define the pages
# page_2 = st.Page("streamlit_page2.py", title="Page 2")
welcome_page = st.Page("st_welcome.py", title="Welcome")
export_page = st.Page("st_export.py", title="Export Pages", icon="➡️")
preview_page = st.Page("st_preview.py", title="Preview Htmls", icon="🔍")
upload_page = st.Page("st_upload.py", title="Upload to GDrive", icon="🚀")

# Set up navigation
pg = st.navigation([welcome_page, export_page, preview_page, upload_page])

st.set_page_config(layout="wide")

# Run the selected page
pg.run()
