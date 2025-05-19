import os
import logging

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service(service_account_file: str | None = None):
    if service_account_file is None:
        service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE")

    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    # https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.html
    return build("drive", "v3", credentials=creds)


def get_all_pages_using_next_page_token(api_call) -> list:
    files = []
    next_page_token = None
    while True:
        # https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list
        response = api_call(next_page_token)
        files += response.get("files", [])
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            return files


SUPPORTED_MIME_TYPES = {
    'txt': 'text/plain',
    'html': 'text/html',
    'md': 'text/markdown',
    'csv': 'text/csv',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'rtf': 'application/rtf',
    'odt': 'application/vnd.oasis.opendocument.text',
    'json': 'application/json',
    'pdf': 'application/pdf',
}

TYPES_TO_CONVERT = ['txt', 'html', 'docx', 'xlsx', 'pptx', 'rtf', 'odt']


class GDriveClient:
    def __init__(self, service_account_file: str | None = None):
        self.service = get_service(service_account_file)
        self.files_svc = self.service.files()

    def files_in_folder(self, folder_id) -> list[dict]:
        # https://stackoverflow.com/questions/24720075/how-to-get-list-of-files-by-folder-on-google-drive-api
        # https://stackoverflow.com/questions/69533918/how-do-i-search-google-drive-api-by-date
        return get_all_pages_using_next_page_token(
            lambda next_page_token: self.files_svc.list(
                q=f"'{folder_id}' in parents and trashed=false",
                pageToken=next_page_token,
            ).execute()
        )

    def create_drive_folder(self, folder_name: str, parent_id: str):
        request_body = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        return self.files_svc.create(body=request_body).execute()

    def upload_to_google_drive(self, src_file, folder_id, target_filename, file_id=None):
        """
        Uploads and imports a file to Google Drive.
        Google's document file import/conversion is better than Python libraries.
        If file_id is not None, the file will be updated; otherwise, a new file will be created.
        """
        # TODO: check if target_filename exists with different file_id

        file_extension = os.path.splitext(src_file)[1][1:]
        if file_extension not in SUPPORTED_MIME_TYPES:
            raise ValueError(f"Unsupported file type: {file_extension}")
        file_size = os.path.getsize(src_file)
        if file_size > 10 * 1024 * 1024:  # 10 MB
            raise ValueError("File size exceeds the limit of 10 MB")
        media = MediaIoBaseUpload(
            open(src_file, mode="rb"),
            mimetype=SUPPORTED_MIME_TYPES[file_extension],
            # https://developers.google.com/workspace/drive/api/guides/manage-uploads
            resumable=file_size > 5 * 1024 * 1024,  # if larger than 5 MB
        )
        logger.info("src_file=%r: %r", src_file, media.__dict__)
        target_mime_type = (
            "application/vnd.google-apps.document"
            if file_extension in TYPES_TO_CONVERT
            else media.mimetype
        )
        request_body = {
            "name": target_filename,
            "parents": [folder_id],
            # Cause Google Drive to convert the file to Google Docs format
            "mimeType": target_mime_type,
        }

        # https://github.com/googleapis/google-api-python-client/blob/main/docs/start.md
        # https://googleapis.github.io/google-api-python-client/docs/dyn/drive_v3.files.html
        # https://developers.google.com/workspace/drive/api/reference/rest/v3/files/create

        # from IPython.core.debugger import set_trace; set_trace()

        if file_id:
            if media.resumable():
                request = self.files_svc.update(
                    fileId=file_id,
                    media_body=media,
                    useContentAsIndexableText=True,
                    uploadType="resumable",
                )
            else:
                request = self.files_svc.update(
                    fileId=file_id, media_body=media, useContentAsIndexableText=True
                )
        else:
            request = self.files_svc.create(
                body=request_body, media_body=media, useContentAsIndexableText=True
            )
        logger.info("file_id: %r", file_id)

        if media.resumable():
            logger.info("Resumable upload for %r", src_file)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info("Uploaded %i.", int(status.progress() * 100))
            logger.info("Upload Complete!")
            return response
        else:
            response = request.execute()
            return response

    def delete_file(self, file_id):
        try:
            self.files_svc.delete(fileId=file_id).execute()
            logger.info("Deleted %r from GDrive", file_id)
            return True
        except googleapiclient.errors.HttpError as e:
            logger.warning("Error deleting (%s) from GDrive: %s", file_id, e)
            return False
