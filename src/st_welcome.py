import streamlit as st

st.header("Welcome to the Confluence-to-GDrive tool!")

st.write("""Use this tool to synchronize Confluence pages to Google Drive so that the content is available for Gemini AI.
  Read more at [Guidelines for AI RAG Bot](https://navasage.atlassian.net/wiki/spaces/CB/pages/1852604660/Guidelines+for+AI+RAG+Bot).""")

st.write("""Use the navigation bar to `Export Pages` and then `Upload to GDrive`.
  Optionally, `Preview Htmls` to examine exported HTML files before uploading.
""")

st.write("If you're uncertain about some options, leave the default input fields and checkboxes as is.")
