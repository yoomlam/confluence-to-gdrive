import logging
import os
import re

from atlassian import Confluence
from bs4 import BeautifulSoup

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


class ConfluenceClient:
    def __init__(self, url: str | None = None):
        self.api = create_client(url)

    def get_global_spaces(self, limit: int = 30):
        return get_all_entities(
            lambda start: self.api.get_all_spaces(
                start=start, limit=limit, space_type="global"
            )
        )

    def get_child_pages(self, page_id: str):
        # TODO: use pagination
        return list(
            self.api.get_page_child_by_type(
                page_id, start=None, limit=None, expand="history.lastUpdated"
            )
        )

    def list_pages(self, space: str, title: str):
        page_id = self.api.get_page_id(space, title)
        child_pages = self.get_child_pages(page_id)
        return child_pages

    def export_page_html(self, page_id, folder):
        # Use export_view -- https://stackoverflow.com/a/50959315/23458508
        page = self.api.get_page_by_id(page_id, expand="body.export_view")
        html_value=page['body']['export_view']['value']

        tree = BeautifulSoup(html_value, "html.parser")
        base_filename = page['title']
        html_filename = os.path.join(folder, f"{base_filename}.html")
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(tree.prettify())

        return html_filename