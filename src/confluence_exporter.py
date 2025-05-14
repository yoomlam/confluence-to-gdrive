import os
import logging
import re
from atlassian import Confluence

logger = logging.getLogger(__name__)


def create_client(url: str | None = None):
    if url is None:
        url = os.environ.get("CONFLUENCE_URL")
    assert url
    pat = os.environ.get("ATLASSIAN_API_KEY")
    username = os.environ.get("ATLASSIAN_USERNAME")
    logger.debug("Keys %r: %r for %r", url, pat, username)

    return Confluence(
        url=url,
        username=username,
        password=pat,
    )


def get_all_entities(api_call) -> list:
    entities = []
    start = 0
    while True:
        response = api_call(start)
        entities += response["results"]
        logger.info("Got %r total entities", len(entities))
        if not response["_links"].get("next"):
            return entities
        limit = response["limit"]
        start += limit


class ConfluenceExporter:
    def __init__(self, url: str | None = None):
        self.client = create_client(url)

    def get_global_spaces(self, limit: int = 30):
        return get_all_entities(
            lambda start: self.client.get_all_spaces(
                start=start, limit=limit, space_type="global"
            )
        )

    def get_child_pages(self, page_id: str):
        return list(
            self.client.get_page_child_by_type(
                page_id, start=None, limit=None, expand=None
            )
        )

    def list_pages(self, space: str, title: str):
        page_id = self.client.get_page_id(space, title)
        child_pages = self.get_child_pages(page_id)
        return child_pages

    def new_funct():
        pass
