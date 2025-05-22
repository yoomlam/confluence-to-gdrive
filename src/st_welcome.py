import streamlit as st

import ui_helper

ss = st.session_state
ui_helper.retain_session_state(ss)

st.header("👋 Welcome to the Confluence-to-GDrive tool!")

st.write(
    """Use this tool to synchronize Confluence pages to Google Drive so that the content is available for Gemini AI.
    Read more at [Guidelines for AI RAG Bot](https://navasage.atlassian.net/wiki/spaces/CB/pages/1852604660/Guidelines+for+AI+RAG+Bot)."""
)

st.write(
    """Use the navigation bar to `Export Pages` and then `Upload to GDrive`.
    Optionally, `Preview Htmls` to examine exported HTML files before uploading.
"""
)

st.write(
    "If you're uncertain about some options, leave the default input fields and checkboxes as is."
)

st.write(
    """Since Confluence pages are being converted to Google documents during the uploading,
    it can take some time depending on the number and size of the pages, as well as Google's servers.
    Start with a small number of pages (around 30)
    by exporting pages with few nested subpages and/or filtering by modification date.
    The tool has been tested with 300+ pages, but it does take many minutes to complete."""
)

st.write(
    """Once this procedure is completed for a batch of Confluence pages, refresh this page to start anew.
    No data is stored on the backend, so refreshing this page will clear any browser session data,
    including the Advanced settings below.
    The one exception to this are exported Confluence pages (i.e., HTML files) that aren't deleted
    because you didn't click the `Delete exported files` button"""
)

st.write(
    """This tool is dependent on an ATLASSIAN_API_KEY to access Confluence.
    Hence, the available Confluence pages may be limited depending on the API key.
    Once uploaded to Google Drive, the files will be accessible according to the file's and folder's sharing permissions.
    Update those permission accordingly. Note that this tool does not delete folders so that permissions are retained."""
)

nondefault_settings = (
    (ss.input_confluence_url != "https://navasage.atlassian.net")
    or ss.input_atl_username
    or ss.input_atl_api_key
    or ss.chkbox_change_gdrive_folder_id
    or not ss.input_profile_name.startswith("profile_")
)
with st.expander("Advanced settings", expanded=nondefault_settings):
    with st.container(border=True):
        st.text_input(
            "Confluence domain URL",
            key="input_confluence_url",
        )
        st.write(
            "To create an API key from your Atlassian profile: https://id.atlassian.com/manage-profile/security/api-tokens"
        )
        st.text_input(
            "Confluence username",
            key="input_atl_username",
            placeholder="username@navapbc.com",
        )
        st.text_input(
            "Confluence API key",
            key="input_atl_api_key",
            type="password",
            placeholder="Paste your Confluence API key here",
        )

    with st.container(border=True):
        st.write(
            "The profile name is used as the export folder name. The default random name is good for single runs of this tool."
            "Using the same profile name across runs allows you to collect and manage exported files before they are uploaded to GDrive."
        )
        profile_name = st.text_input(
            "Profile name",
            key="input_profile_name",
            placeholder="Used as the export folder name",
        )
        if not (profile_name and profile_name[0].isalpha()):
            st.error(f"Profile name `{profile_name}` must start with a letter!")
            ss.export_folder = None
        else:
            ss.export_folder = f"./exports/{profile_name}"

    with st.container(border=True):
        st.write(
            "This refers to the top-level Google Drive folder where the Confluence page hierarchy will be replicated."
        )
        st.checkbox(
            "I want to change this for a special circumstance.",
            key="chkbox_change_gdrive_folder_id",
        )
        st.text_input(
            "ID of the *root* Google Drive folder",
            key="input_gdrive_folder_id",
            disabled=not ss.chkbox_change_gdrive_folder_id,
        )
        # TODO: input GDrive json credential
