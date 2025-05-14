import logging
import os

from flask import Flask, request
from dotenv import load_dotenv

import confluence_exporter as confl

from confluence_exporter import ConfluenceExporter

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
load_dotenv(dotenv_path=".env_local", override=True)

app = Flask(__name__)


@app.route("/hello")
def hello_world():
    """Example Hello World route."""
    name = os.environ.get("NAME", "World")
    return f"Hello {name}!"


@app.route("/confluence_spaces")
def confluence_spaces():
    exporter = ConfluenceExporter()
    # logger.debug("Connected to Confluence: %r", exporter)
    spaces = confl.get_global_spaces(exporter)
    # logger.debug(f"{len(spaces)} spaces: %r", [(s['key'], s['name'], s['id']) for s in spaces])
    return [{"key": s["key"], "name": s["name"], "id": s["id"]} for s in spaces]


@app.route("/confluence_pages")
def confluence_pages():
    space_key = request.args.get("space_key", "NL")
    page_title = request.args.get("page_title", "No page")
    logger.debug("space_key=%r, page_title=%r", space_key, page_title)
    exporter = ConfluenceExporter()
    pages = exporter.list_pages(space_key, page_title)
    return [{"title": p["title"], "id": p["id"]} for p in pages]


if __name__ == "__main__":
    logger.info("Starting server...")
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
