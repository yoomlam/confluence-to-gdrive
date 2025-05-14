import logging

from dotenv import load_dotenv

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
    return [{"title": p["title"], "id": p["id"]} for p in pages]
