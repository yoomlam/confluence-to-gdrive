import os
import shutil
from queue import Queue

import streamlit as st

import gdrive_client
import main
import ui_helper

ss = st.session_state
ui_helper.retain_session_state(ss)

st.header("🚀 Upload to Google Drive")
st.write(
    f"This will upload the HTML files and convert them to Google Documents under [this Google Drive folder](https://drive.google.com/drive/folders/{ss.input_gdrive_folder_id})."
)


if not os.path.exists(ss.export_folder):
    st.write("Export pages to HTML before uploading to GDrive.")
else:

    def start_uploader_thread():
        # ss itself cannot be accessed in a different thread,
        # so extract desired variables for upload_files() to use in separate thread
        _gclient = gdrive_client.GDriveClient()
        _source_folder = ss.export_folder
        _gdrive_folder_id = ss.input_gdrive_folder_id
        _dry_run = ss.chkbox_dry_run_upload
        _skip_existing = ss.chkbox_skip_existing_gdrive_files
        _delete_gfiles = ss.chkbox_delete_unmatched_files

        def upload_files(queue: Queue):
            main.sync_folder_to_gdrive(
                _gclient,
                _source_folder,
                _gdrive_folder_id,
                queue,
                skip_existing=_skip_existing,
                delete_gfiles=_delete_gfiles,
                dry_run=_dry_run,
            )

        ss.upload_threader.start_thread(upload_files)

    with st.container(border=True):
        st.checkbox(
            "Dry run (creates folders but not files)",
            key="chkbox_dry_run_upload",
        )
        st.checkbox(
            "Skip files that already exist in GDrive regardless of differences (used to resume failed/incomplete uploads)",
            key="chkbox_skip_existing_gdrive_files",
        )
        st.checkbox(
            "Delete GDrive files that have no corresponding exported file",
            key="chkbox_delete_unmatched_files",
        )

        label = "Dry-run " if ss.chkbox_dry_run_upload else ""
        if ss.chkbox_delete_unmatched_files:
            label += "Synchronize with GDrive (with deletions)"
        else:
            label += "Upload to GDrive"
        st.button(
            label=label,
            disabled=ss.upload_threader.is_alive(),
            on_click=start_uploader_thread,
        )
        if not ss.chkbox_dry_run_upload:
            st.write(
                "During upload to GDrive, the files are imported as Google Documents. "
                "This file conversion may take a while, depending on the number of files and their sizes."
            )

    ss.upload_threader.create_status_container(st)

    if st.button(f"Delete exported files in `{ss.export_folder}`"):
        shutil.rmtree(ss.export_folder)
        st.write(f"Delete exported HTML files: `{ss.export_folder}`")
