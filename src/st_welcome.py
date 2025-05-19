import streamlit as st

st.header("Welcome to the Confluence-to-GDrive tool!")

st.write("""Use this tool to synchronize Confluence pages to Google Drive so that the content is available for Gemini AI.
  Read more at [Guidelines for AI RAG Bot](https://navasage.atlassian.net/wiki/spaces/CB/pages/1852604660/Guidelines+for+AI+RAG+Bot).""")

st.write("""Use the navigation bar to `Export Pages` and then `Upload to GDrive`.
  Optionally, `Preview Htmls` to examine exported HTML files before uploading.
""")

st.write("If you're uncertain about some options, leave the default input fields and checkboxes as is.")

st.write("""Since Confluence pages are being converted to Google documents during the uploading,
 it can take some time depending on the number and length of the pages and Google's servers.
 Start with a small number of pages (up to around 30) by exporting more deeply nested pages and/or filtering by modification date.""")

st.write("""Once this procedure is completed for a batch of Confluence pages, refresh this page to start anew.
  No data is stored on the backend except for any temporary exported Confluence pages that aren't deleted,
  so refreshing this page will clear any browser session data.""")

st.write("""This tool is dependent on an ATLASSIAN_API_KEY to access Confluence.
  Hence, the available Confluence pages may be limited depending on the API key.
  Once uploaded to Google Drive, the files will be accessible according to the file's and folder's sharing permissions.
  Update those permission accordingly. Note that this tool does not delete folders so that permissions are retained.""")
