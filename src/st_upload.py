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
    dry_run = st.checkbox(
        "Dry run (creates folders but not files)",
        key="chkbox_dry_run_upload",
    )
    skip_existing = st.checkbox(
        "Skip files that already exist in GDrive regardless of differences (used to resume previously failed uploads)",
        key="chkbox_skip_existing_gdrive_files",
    )
    delete_gfiles = st.checkbox(
        "Delete GDrive files that have no corresponding exported file",
        key="chkbox_delete_unmatched_files",
    )
    delete_exports = st.checkbox(
        "After all pages successful uploaded, delete exported files",
        key="chkbox_delete_after_upload",
    )

    def start_uploader_thread():
        # ss itself cannot be accessed in a different thread,
        # so extract desired variables for upload_files() to use in separate thread
        _gclient = gdrive_client.GDriveClient()
        _source_folder = ss.export_folder
        _gdrive_folder_id = ss.input_gdrive_folder_id

        def upload_files(queue: Queue):
            main.sync_folder_to_gdrive(
                _gclient,
                _source_folder,
                _gdrive_folder_id,
                queue,
                skip_existing=skip_existing,
                delete_gfiles=delete_gfiles,
                dry_run=dry_run,
            )
            if delete_exports:
                if not dry_run:
                    shutil.rmtree(_source_folder)
                queue.put(f"Delete exported HTML files: `{_source_folder}`")

        ss.uploading = True
        ss.upload_threader.start_thread(upload_files)
        ss.uploading = False

    label = "Dry-run " if dry_run else ""
    if delete_gfiles:
        label += "Synchronize with GDrive (with deletions)"
    else:
        label += "Upload to GDrive"
    st.button(
        label=label,
        disabled=ss.uploading,
        on_click=start_uploader_thread,
        # key="upload_btn",
    )
    if not dry_run:
        st.write(
            "During upload to GDrive, the files are imported as Google Documents. "
            "This file conversion may take a while, depending on the number of files and their sizes."
        )

    ss.upload_threader.create_status_container(st)
