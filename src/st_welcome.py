import streamlit as st

import ui_helper

ss = st.session_state
ui_helper.retain_session_state(ss)

st.header("👋 Welcome to the Confluence-to-GDrive tool!")
st.write(
    """Use this tool to synchronize Confluence pages to Google Drive so that the content is available for Gemini AI.
Read more at [Guidelines for AI RAG Bot](https://navasage.atlassian.net/wiki/spaces/CB/pages/1852604660/Guidelines+for+AI+RAG+Bot).

This tool is used to select particular Confluence pages and synchronize them with a Google Drive folder.

#### Quickstart
* Use the navigation bar to `Export Pages` and then `Upload to GDrive`.
* Leave the default input fields and checkboxes as is, if uncertain.
* Use the `Dry run` checkbox when uploading to GDrive to test without actually uploading files.
  Folders will still be created so you can check in GDrive.
* Once complete for a batch of Confluence pages, refresh the browser to start anew.
* Optionally, filter the pages to be exported by modification date or
  hand-pick specific pages to include/exclude.
* Optionally, use `Preview Htmls` to examine exported HTML files before uploading.
  Deleting a file will exclude it from the upload.

#### Tips
* Be certain that the content in Confluence pages selected for export are appropriate for storing
  outside of Confluence. Confluence has built-in access permissions and security features.
  The top-level Google Drive folder is shared with all of Nava. Permissions can be set for subfolders.
  See FAQ for details.
* Start small: Since Confluence pages are being converted to Google documents during the uploading,
  it can take some time depending on the number and size of the pages, as well as Google's servers.
  Start with a small number of pages (around 30)
  by exporting pages with few nested subpages and/or by filtering based on modification date.
  The tool has been tested with 300+ pages at a time.
* Data persistence: No data is stored on the backend, so refreshing this page will
  clear any browser session data, including the Advanced settings below.
  The one exception to this are exported Confluence pages (i.e., HTML files) that aren't deleted
  because you didn't click the `Delete exported files` button.

#### FAQ
* By default, all files are uploaded to the same shared Google Drive folder named
  [Confluence pages (imported)](https://drive.google.com/drive/folders/1IMr0v3azM_8yaxTCkv2tQo22cSArk06Q).
  It is shared with all of Nava so that folks can use Gemini AI on the files without
  having to export their own copy of Confluence pages, which is possible using the Advanced Settings below.
* Why the deep folder structure? The folder structure in Google Drive mirrors the Confluence page hierarchy,
  where first level of subfolders correspond to the Confluence spaces.
* Access permissions? Once uploaded to Google Drive, the files will be accessible according to the file's and folder's sharing permissions.
  Update permission on newly created folders and files accordingly.
  This tool does not delete folders so that permissions are retained.
    * TBD: For automated setting of access permissions, this tool can be updated to look for
      [page labels](https://support.atlassian.com/confluence-cloud/docs/use-labels-to-organize-your-content/)
      or some consistent phrase or syntax like `NOT FOR SHARING`.
* What if I modify the Google Documents? Any changes made to the Google documents will be overridden
  the next time this tool uploads the corresponding file. To retain the changes, modify the original Confluence page.
* When a file is uploaded to Google Drive and an existing file with the same name exists,
  the file is updated as a new version of the Google doc.
* Not seeing certain pages? This tool is dependent on an ATLASSIAN_API_KEY to access Confluence.
  Hence, the set of available Confluence pages may be limited, depending on the API key.
  To address this, API credentials can be modified in the Advanced Settings below.
"""
)

st.divider()

nondefault_settings = bool(
    (ss.input_confluence_url != "https://navasage.atlassian.net")
    or ss.input_atl_username
    or ss.input_atl_api_key
    or ss.chkbox_change_gdrive_folder_id
    or ss.input_gdrive_credentials
    or not ss.input_profile_name.startswith("profile_")
)
with st.expander("Advanced Settings", expanded=nondefault_settings):
    with st.container(border=True):
        st.write(
            "Use alternative Confluence site and/or credentials to access pages unavailable to the default credentials."
        )
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
            "The profile name is used as the export folder name. The default random name is appropriate for typical single runs of this tool."
            " Using the same profile name across runs allows you to collect and manage exported files before they are uploaded to GDrive."
            " In this use case, the `Skip files that already exist in GDrive` upload option may be used to resume previous uploads."
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
            "I want to change this for a special circumstance",
            key="chkbox_change_gdrive_folder_id",
        )
        st.text_input(
            "ID of the *root* Google Drive folder",
            key="input_gdrive_folder_id",
            disabled=not ss.chkbox_change_gdrive_folder_id,
        )

    with st.container(border=True):
        st.warning(
            "This is only needed if the default credentials are not working or a different Google account is desired."
        )
        st.write(
            "Create a [Google service account](https://support.google.com/a/answer/7378726?hl=en) and download the credentials JSON file."
        )
        st.text_area(
            label="Google API credentials JSON",
            key="input_gdrive_credentials",
            placeholder="Paste credentials from your Google service account here",
            height=300,
        )
