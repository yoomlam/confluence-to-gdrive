import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Self

from anytree import Node, PreOrderIter, RenderTree
from dotenv import load_dotenv

import confluence_client
from confluence_client import ConfluenceClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
load_dotenv(dotenv_path=".env_local", override=True)


def get_confluence_spaces():
    cclient = ConfluenceClient()
    # logger.debug("Connected to Confluence: %r", cclient)
    spaces = confluence_client.get_global_spaces(cclient)
    # logger.debug(f"{len(spaces)} spaces: %r", [(s['key'], s['name'], s['id']) for s in spaces])
    return [{"key": s["key"], "name": s["name"], "id": s["id"]} for s in spaces]


def get_confluence_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    cclient = ConfluenceClient()
    pages = cclient.list_pages(space_key, page_title)
    return [
        {
            "folder": page_title,
            "title": p["title"],
            "id": p["id"],
            "modified": p["history"]["lastUpdated"]["when"],
        }
        for p in pages
    ]


def build_tree(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    cclient = ConfluenceClient()
    page_id = cclient.api.get_page_id(space_key, page_title)
    page = cclient.api.get_page_by_id(page_id, expand="body.export_view,history.lastUpdated")
    root_node = _create_node(page)
    _recurse_build_tree(cclient, root_node)
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
    )


def _recurse_build_tree(cclient, parent_node, depth=1):
    child_pages = cclient.get_child_pages(parent_node.id)
    child_nodes = [_create_node(p, parent_node) for p in child_pages]
    if child_pages:
        for child in child_nodes:
            _recurse_build_tree(cclient, child, depth + 1)


def export_html_folder(root_node: Node, folder: str):
    cclient = ConfluenceClient()
    os.makedirs(folder, exist_ok=True)
    _recurse_export_html(cclient, root_node, folder)


def _recurse_export_html(cclient, parent_node: Node, path, depth=1):
    if parent_node.include:
        logger.info("Exporting page %r", parent_node.title)
        filename = cclient.export_page_html(parent_node.id, path)
        logger.info("Exported page %r", filename)
    child_nodes = parent_node.children
    if child_nodes:
        logger.info("Creating folder for page %r", parent_node.title)
        subpath = os.path.join(path, parent_node.title)
        os.makedirs(subpath, exist_ok=True)
        for child in child_nodes:
            _recurse_export_html(exporter, child, subpath, depth + 1)
