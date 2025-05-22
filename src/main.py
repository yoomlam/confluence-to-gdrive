import functools
import logging
import os
from datetime import datetime
from queue import Queue

from anytree import Node, PreOrderIter
from dotenv import load_dotenv

from confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
load_dotenv(dotenv_path=".env_local", override=True)


@functools.cache
def create_confluence_client(
    url: str | None, username: str | None, api_key: str | None
) -> ConfluenceClient:
    return ConfluenceClient(url=url, username=username, api_key=api_key)


class ConfluenceOps:
    def __init__(
        self, *, url: str | None = None, username: str | None = None, api_key: str | None = None
    ):
        self.cclient = create_confluence_client(url=url, username=username, api_key=api_key)

    def confluence_api_url(self):
        return self.cclient.api.url

    def get_confluence_spaces(self):
        spaces = self.cclient.get_global_spaces()
        return [
            {
                "space_key": s["key"],
                "name": s["name"],
                "id": s["id"],
                "webui": s["_links"]["webui"],
                "homepage_title": s["homepage"]["title"],
            }
            for s in spaces
        ]

    def get_confluence_pages(self, space_key, page_title):
        logger.info("space_key=%r, page_title=%r", space_key, page_title)
        pages = self.cclient.list_pages(space_key, page_title)
        return [
            {
                "folder": page_title,
                "title": p["title"],
                "id": p["id"],
                "modified": p["history"]["lastUpdated"]["when"],
            }
            for p in pages
        ]

    def query_pages_as_tree(self, space_key, page_title):
        logger.info("space_key=%r, page_title=%r", space_key, page_title)
        cclient = self.cclient
        page_id = cclient.api.get_page_id(space_key, page_title)
        page = cclient.api.get_page_by_id(page_id, expand="body.export_view,history.lastUpdated")
        root_node = self._create_node(page)
        self._recurse_build_tree(root_node)
        for n in PreOrderIter(root_node):
            n.link = f"{cclient.api.url}{n.webui}"
        return root_node

    def _create_node(self, page, parent_node: Node | None = None):
        timestamp_str = page["history"]["lastUpdated"]["when"]
        mod_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return Node(
            page["id"],
            parent=parent_node,
            id=page["id"],
            title=page["title"],
            modified=mod_timestamp,
            webui=page["_links"]["webui"],
        )

    def _recurse_build_tree(self, parent_node, depth=1):
        child_pages = self.cclient.get_child_pages(parent_node.id)
        child_nodes = [self._create_node(p, parent_node) for p in child_pages]
        if child_pages:
            for child in child_nodes:
                self._recurse_build_tree(child, depth + 1)

    def export_html_folder(self, root_node: Node, folder: str, queue: Queue):
        os.makedirs(folder, exist_ok=True)
        self._recurse_export_html(root_node, folder, queue)

    def _recurse_export_html(self, node: Node, folder, queue: Queue, depth=1):
        if node.to_export:
            logger.info("Exporting page %r", node.title)
            filename = self.cclient.export_page_html(node.id, folder, create_ancestor_folders=True)
            queue.put(f"Saved page `{node.title}` to `{filename}`")

        for child in node.children or []:
            self._recurse_export_html(child, folder, queue, depth + 1)


def is_google_folder(gfile: dict) -> bool:
    return gfile["mimeType"] == "application/vnd.google-apps.folder"


def gfile_exists_locally(gfile: dict, local_folder: str, file_suffix: str = ".html") -> bool:
    if is_google_folder(gfile):
        full_path = os.path.join(local_folder, gfile["name"])
        return os.path.isdir(full_path)

    filename = f"{gfile['name']}{file_suffix}"
    full_path = os.path.join(local_folder, filename)
    return os.path.isfile(full_path)


def sync_folder_to_gdrive(
    gclient,
    input_folder,
    folder_id,
    queue: Queue,
    *,
    skip_existing=True,
    delete_gfiles=False,
    dry_run=False,
):
    existing_gfiles = gclient.files_in_folder(folder_id)

    if delete_gfiles:
        # Delete GDrive files that no longer exist locally
        for gfile in existing_gfiles:
            if gfile["name"].startswith("."):
                logger.info("Skipping hidden file %r", gfile["name"])
                continue
            if is_google_folder(gfile):
                continue
            logger.info("Checking %r", gfile)
            if not gfile_exists_locally(gfile, input_folder):
                if not dry_run:
                    logger.info("Deleting %r from GDrive %r", gfile["name"], input_folder)
                    gclient.delete_file(gfile["id"])
                queue.put(f"Delete `{gfile['name']}` from GDrive `{input_folder}`")

    # Upload to GDrive, updating if file with same name exists
    existing_gfilenames = {
        f["name"]: f
        for f in existing_gfiles
        if f["mimeType"] != "application/vnd.google-apps.folder"
    }
    existing_gfolders = {
        f["name"]: f
        for f in existing_gfiles
        if f["mimeType"] == "application/vnd.google-apps.folder"
    }
    # logger.info("Existing gfiles: %r", existing_gfilenames)
    # logger.info("Existing gfolders: %r", existing_gfolders)

    export_files = os.listdir(input_folder)
    # logger.info("Files in folder: %r", export_files)
    for e_file in export_files:
        # Check if e_file is a folder
        subfolder_path = os.path.join(input_folder, e_file)
        if os.path.isdir(subfolder_path):
            if e_file not in existing_gfolders:
                subfolder = gclient.create_drive_folder(e_file, folder_id)
                subfolder_id = subfolder["id"]
            else:
                subfolder_id = existing_gfolders[e_file]["id"]
            logger.info("Recurse into folder %r", e_file)
            sync_folder_to_gdrive(
                gclient,
                subfolder_path,
                subfolder_id,
                queue,
                skip_existing=skip_existing,
                delete_gfiles=delete_gfiles,
                dry_run=dry_run,
            )
            continue

        html_filename = os.path.join(input_folder, e_file)
        title = e_file.removesuffix(".html")
        # logger.info("title %r", title)
        # TODO: check timestamps to determine if update/upload is needed
        if title in existing_gfilenames:
            if skip_existing:
                logger.info("  Skipping existing %r in GDrive", title)
                queue.put(
                    f"Skipping existing `{title}` in GDrive [{folder_id}](https://drive.google.com/drive/folders/{folder_id})"
                )
            else:
                file_id = existing_gfilenames[title]["id"]
                if not dry_run:
                    logger.info("  Updating %r in GDrive", title)
                    response = gclient.upload_to_google_drive(
                        html_filename, folder_id, title, file_id
                    )
                queue.put(
                    f"Update `{title}` in GDrive [{folder_id}](https://drive.google.com/drive/folders/{folder_id})"
                )
        else:
            if not dry_run:
                logger.info("  Uploading %r", title)
                response = gclient.upload_to_google_drive(html_filename, folder_id, title)
            queue.put(
                f"Upload `{title}` in GDrive [{folder_id}](https://drive.google.com/drive/folders/{folder_id})"
            )
