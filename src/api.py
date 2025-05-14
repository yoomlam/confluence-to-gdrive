import logging
import os

from flask import Flask, request

from main import get_confluence_pages, get_confluence_spaces

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)


@app.route("/hello")
def hello_world():
    """Example Hello World route."""
    name = os.environ.get("NAME", "World")
    return f"Hello {name}!"


@app.route("/confluence_spaces")
def confluence_spaces():
    return get_confluence_pages()


@app.route("/confluence_pages")
def confluence_pages():
    space_key = request.args.get("space_key", "NL")
    page_title = request.args.get("page_title", "No page")
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    return get_confluence_spaces(space_key, page_title)


if __name__ == "__main__":
    logger.info("Starting server...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
