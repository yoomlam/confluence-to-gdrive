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


@dataclass
class ConfluencePage:
    id: str
    title: str
    modified: str
    childs: list[Self] | None = None


def recurse_pages(space_key, page_title):
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    exporter = ConfluenceExporter()
    page_id = exporter.client.get_page_id(space_key, page_title)
    page = exporter.client.get_page_by_id(page_id, expand="body.export_view,history.lastUpdated")
    root_page = ConfluencePage(page_id, page_title, page["history"]["lastUpdated"]["when"])
    recurse_page(exporter, root_page)
    return flatten_page_childs(root_page)


def recurse_page(exporter, page, depth=1):
    logger.info("TODO: export page %r", page)
    child_pages = exporter.get_child_pages(page.id)
    page.childs = [ConfluencePage(p["id"], p["title"], p["history"]["lastUpdated"]["when"]) for p in child_pages]
    if child_pages:
        logger.info("TODO: create folder for page %r", page.title)
        for child in page.childs:
            recurse_page(exporter, child, depth + 1)


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
