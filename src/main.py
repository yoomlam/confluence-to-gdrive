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
def confluence_client():
    return ConfluenceClient()

def confluence_base_url():
    return confluence_client().api.url

def get_confluence_spaces():
    spaces = confluence_client().get_global_spaces()
    # logger.debug(f"{len(spaces)} spaces: %r", [(s['key'], s['name'], s['id']) for s in spaces])
    return [{"space_key": s["key"], "name": s["name"], "id": s["id"], "webui": s["_links"]["webui"]} for s in spaces]


def get_confluence_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    pages = confluence_client().list_pages(space_key, page_title)
    return [
        {
            "folder": page_title,
            "title": p["title"],
            "id": p["id"],
            "modified": p["history"]["lastUpdated"]["when"],
        }
        for p in pages
    ]


def query_pages_as_tree(space_key, page_title):
    logger.info("space_key=%r, page_title=%r", space_key, page_title)
    cclient = ConfluenceClient()
    page_id = cclient.api.get_page_id(space_key, page_title)
    page = cclient.api.get_page_by_id(page_id, expand="body.export_view,history.lastUpdated")
    root_node = _create_node(page)
    _recurse_build_tree(cclient, root_node)
    for n in PreOrderIter(root_node):
        n.link = f"{cclient.api.url}{n.webui}"
    return root_node


def _create_node(page, parent_node: Node | None = None):
    timestamp_str = page["history"]["lastUpdated"]["when"]
    mod_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return Node(
        page["id"],
        parent=parent_node,
        id=page["id"],
        title=page["title"],
        modified=mod_timestamp,
        webui = page['_links']['webui']
    )


def _recurse_build_tree(cclient, parent_node, depth=1):
    child_pages = cclient.get_child_pages(parent_node.id)
    child_nodes = [_create_node(p, parent_node) for p in child_pages]
    if child_pages:
        for child in child_nodes:
            _recurse_build_tree(cclient, child, depth + 1)

class LoggerQueue:
    def put(self, obj):
        logger.info(obj)

def export_html_folder(root_node: Node, folder: str, queue: Queue | LoggerQueue):
    cclient = ConfluenceClient()
    os.makedirs(folder, exist_ok=True)
    _recurse_export_html(cclient, root_node, folder, queue)


def _recurse_export_html(cclient, node: Node, folder, queue: Queue, depth=1):
    if node.to_export:
        logger.info("Exporting page %r", node.title)
        filename = cclient.export_page_html(node.id, folder, create_ancestor_folders=True)
        queue.put(f"Saved page {node.title!r} to `{filename}`")

    for child in node.children or []:
        _recurse_export_html(cclient, child, folder, queue, depth + 1)


def is_google_folder(gfile: dict) -> bool:
    return gfile["mimeType"] == "application/vnd.google-apps.folder"


def gfile_exists_locally(gfile: dict, local_folder: str, file_suffix: str = ".html") -> bool:
    if is_google_folder(gfile):
        full_path = os.path.join(local_folder, gfile["name"])
        return os.path.isdir(full_path)

    filename = f"{gfile['name']}{file_suffix}"
    full_path = os.path.join(local_folder, filename)
    return os.path.isfile(full_path)


def sync_folder_to_gdrive(gclient, export_folder, folder_id, *, delete_gfiles=False, dry_run=False):
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
            if not gfile_exists_locally(gfile, export_folder):
                logger.info("Deleting %r from GDrive %r", gfile["name"], export_folder)
                if not dry_run:
                    gclient.delete_file(gfile["id"])

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
    logger.info("Existing gfiles: %r", existing_gfilenames)
    logger.info("Existing gfolders: %r", existing_gfolders)

    export_files = os.listdir(export_folder)
    logger.info("Files in folder: %r", export_files)
    for e_file in export_files:
        # Check if e_file is a folder
        subfolder_path = os.path.join(export_folder, e_file)
        if os.path.isdir(subfolder_path):
            if e_file not in existing_gfolders:
                subfolder = gclient.create_drive_folder(e_file, folder_id)
                subfolder_id = subfolder["id"]
            else:
                subfolder_id = existing_gfolders[e_file]["id"]
            logger.info("Recurse into folder %r", e_file)
            sync_folder_to_gdrive(gclient, subfolder_path, subfolder_id, delete_gfiles=delete_gfiles, dry_run=dry_run)
            continue

        html_filename = os.path.join(export_folder, e_file)
        title = e_file.removesuffix(".html")
        logger.info("title %r", title)
        # TODO: check timestamps and config to determine if update/upload is done
        if title in existing_gfilenames:
            file_id = existing_gfilenames[title]['id']
            logger.info("  Updating %r in GDrive", title)
            if not dry_run:
                gclient.upload_to_google_drive(html_filename, folder_id, title, file_id)
        else:
            logger.info("  Uploading %r to GDrive", title)
            if not dry_run:
                gclient.upload_to_google_drive(html_filename, folder_id, title)

    # for cp in export_files:
    #     subchild_pages = get_child_pages(cp['id'])
    #     logger.info("Subchild pages of %r", cp['title'])
    #     logger.info([(scp['title'], scp['id']) for scp in subchild_pages])
