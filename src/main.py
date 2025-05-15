import logging

from dotenv import load_dotenv
from typing import NamedTuple

import confluence_exporter as confl

from confluence_exporter import ConfluenceExporter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
load_dotenv(dotenv_path=".env_local", override=True)


def get_confluence_spaces():
    exporter = ConfluenceExporter()
    # logger.debug("Connected to Confluence: %r", exporter)
    spaces = confl.get_global_spaces(exporter)
    # logger.debug(f"{len(spaces)} spaces: %r", [(s['key'], s['name'], s['id']) for s in spaces])
    return [{"key": s["key"], "name": s["name"], "id": s["id"]} for s in spaces]


def get_confluence_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    exporter = ConfluenceExporter()
    pages = exporter.list_pages(space_key, page_title)
    return [
        {
            "folder": page_title,
            "title": p["title"],
            "id": p["id"],
            "modified": p["history"]["lastUpdated"]["when"],
        }
        for p in pages
    ]


# Given a Confluence space key and page title and GDrive root folder ID, create GDrive doc.
# If page has subpages, create a GDrive folder with the same name and populate it with the subpages.
# Recurse for each subpage.

from typing import Self
from dataclasses import dataclass
from anytree import Node, PreOrderIter, RenderTree

# @dataclass
# class ConfluencePage:
#     id: str
#     title: str
#     modified: str
#     childs: list[Self] | None = None

from datetime import datetime

def create_node(page, parent_node: Node | None = None):
    timestamp_str = page["history"]["lastUpdated"]["when"]
    mod_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return Node(
        page["id"],
        parent=parent_node,
        id=page["id"],
        title=page["title"],
        modified=mod_timestamp,
    )


def recurse_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    exporter = ConfluenceExporter()
    page_id = exporter.client.get_page_id(space_key, page_title)
    page = exporter.client.get_page_by_id(page_id, expand="body.export_view,history.lastUpdated")
    root_node = create_node(page)
    # root_node.
    recurse_page(exporter, root_node)
    return root_node


def recurse_page(exporter, parent_node, depth=1):
    logger.info("TODO: export page %r", parent_node.title)
    child_pages = exporter.get_child_pages(parent_node.id)
    child_nodes = [create_node(p, parent_node) for p in child_pages]
    if child_pages:
        logger.info("TODO: create folder for page %r", parent_node.title)
        for child in child_nodes:
            recurse_page(exporter, child, depth + 1)


def flatten_page_tree(root_node):
    return [node for node in PreOrderIter(root_node)]


def flatten_page_childs(page):
    return [page] + [p for child in page.childs for p in flatten_page_childs(child)]


# def old(root_page, exporter):
#     queue = [root_page]
#     pages = []
#     while queue:
#         page = queue.pop(0)
#         logger.info("TODO: export page %r", page)
#         pages.append(page)
#         child_pages = exporter.get_child_pages(page.id)
#         page.childs = [ConfluencePage(p["id"], p["title"]) for p in child_pages]
#         if child_pages:
#             logger.info("TODO: create folder for page %r", page.title)
#             queue += [ConfluencePage(p["id"], p["title"], page) for p in child_pages]
#             # return queue
#     return pages
