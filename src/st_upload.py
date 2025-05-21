import os
import shutil
from queue import Queue

import streamlit as st

import gdrive_client
import main
from ui_helpers import StreamlitThreader

# Configuration
GDRIVE_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID")

ss = st.session_state
st.header("🚀 Upload to Google Drive")
st.write(
    f"This will upload the HTML files and convert them to Google Documents under [this Google Drive folder](https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID})"
)

if "uploading" not in ss:
    ss.uploading = False

if ss.get("export_threader", None) and ss.export_threader.state == "complete":
    if "upload_threader" not in ss:
        ss.upload_threader = StreamlitThreader("Uploader", ss)

    dry_run = st.checkbox("Dry run (creates folders but not files)", value=True)
    skip_existing = st.checkbox(
        "Skip files that already exist in GDrive regardless of differences (used to resume previously failed uploads)",
        False,
    )
    delete_gfiles = st.checkbox(
        "Delete GDrive files that have no corresponding exported file", value=False
    )
    delete_exports = st.checkbox("After all pages successful uploaded, delete exported files", True)

    def start_uploader_thread():
        # ss itself cannot be accessed in a different thread,
        # so extract desired variables for upload_files() to use in separate thread
        export_folder = ss.export_folder
        gclient = gdrive_client.GDriveClient()

        def upload_files(queue: Queue):
            main.sync_folder_to_gdrive(
                gclient,
                export_folder,
                GDRIVE_FOLDER_ID,
                queue,
                skip_existing=skip_existing,
                delete_gfiles=delete_gfiles,
                dry_run=dry_run,
            )
            if delete_exports:
                if not dry_run:
                    shutil.rmtree(export_folder)
                queue.put(f"Delete exported HTML files: `{export_folder}`")

        ss.uploading = True
        ss.upload_threader.start_thread(upload_files)
        ss.uploading = False

    label = "Dry-run " if dry_run else ""
    if delete_gfiles:
        label += "Synchronize with GDrive (with deletions)"
    else:
        label += "Upload to GDrive"
    if st.button(
        label=label,
        disabled=ss.uploading,
        on_click=start_uploader_thread,
        key="upload_btn",
    ):
        ss.uploaded_to_gdrive = True
    if not dry_run:
        st.write(
            "During upload to GDrive, the files are imported as Google Documents. "
            "This file conversion may take a while, depending on the number of files and their sizes."
        )

    if ss.get("upload_threader", None):
        ss.upload_threader.create_status_container(st)
else:
    st.write("Export pages to HTML before uploading to GDrive")
