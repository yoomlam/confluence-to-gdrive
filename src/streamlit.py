import logging
import os
import requests
import streamlit as st
from streamlit_tree_select import tree_select

from main import get_confluence_pages, recurse_pages
from main import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

if False and not hasattr(st, "already_started_server"):
    # https://discuss.streamlit.io/t/streamlit-restful-app/409/2
    # Hack the fact that Python modules (like st) only load once to
    # keep track of whether this file already ran.
    st.already_started_server = True

    st.write(
        """
        The first time this script executes it will run forever because it's
        running a Flask server.

        Just close this browser tab and open a new one to see your Streamlit
        app.
    """
    )

    logger.info("Starting server...")
    from api import app

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))


st.write("Hello world")

ss = st.session_state

from datetime import datetime

# Add button to query API
space_key = st.text_input("space key", "NL")
# page_title = st.text_input("page title", "Design and Prototyping")
page_title = st.text_input("page title", "Product")

from typing import NamedTuple
from anytree import search
from anytree import Node
from dataclasses import dataclass

class ConfPage(NamedTuple):
    node: Node
    id: str
    title: str
    modified: str
    parent: str | None

class PageNode:
    # node: Node
    def __init__(self, node: Node):
        self.node = node
        self.id = node.id
        self.title = node.title
        self.modified = node.modified
        self.parent = node.parent.title if node.parent else None

    # @property
    # def id(self):
    #     return self.node.id

    # @property
    # def title(self):
    #     return self.node.title

    # @property
    # def modified(self):
    #     return self.node.modified

    # @property
    # def parent(self):
    #     return self.node.parent.title if self.node.parent else None

    def as_row(self):
        return {
            "id": self.id,
            "title": self.title,
            "modified": self.modified,
            "parent": self.parent,
            "exclude": getattr(self.node, "exclude", False)
        }


# class ConfPage(NamedTuple):
#     node: Node
#     id: str
#     title: str
#     modified: str
#     parent: str | None


if st.button("Query spaces"):
    ss.spaces_response = get_confluence_pages(space_key, page_title)
if "spaces_response" in ss:
    # st.json(ss.spaces_response)
    st.dataframe(data=ss.spaces_response)

column_order = None # ["id", "title", "modified", "parent"]
column_config = None
{
    "node": None,
    "id": "ID",
    "title": "Title",
    "modified": "Modified",
    "parent": "Parent",
}
if st.button("Query pages"):
    ss.root_node = recurse_pages(space_key, page_title)
    ss.pages_response = [
        PageNode(n).as_row()
        for n in flatten_page_tree(ss.root_node)
    ]

after_date = st.date_input("after date", format="YYYY-MM-DD")
after_time = st.time_input("after time")
date_str = f"{after_date}T{after_time}.000Z"
timestamp = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
st.write(timestamp)


# def exclude_old_nodes(root_node, timestamp):
#     old_nodes = search.findall(root_node, filter_=lambda n: n.modified < timestamp)
#     for node in old_nodes:
#         node.exclude = True


if st.button("Filter"):
    excluded_nodes = [n for n in flatten_page_tree(ss.root_node) if n.modified < timestamp]
    for n in excluded_nodes:
        n.exclude = True

    ss.pages_response = [
        PageNode(n).as_row()
        for n in flatten_page_tree(ss.root_node)
    ]

    ss.excluded_pages = [
        PageNode(n).as_row()
        for n in flatten_page_tree(ss.root_node)
        if getattr(n, "exclude", False)
    ]        

    ss.filtered_pages = [
        PageNode(n).as_row()
        for n in flatten_page_tree(ss.root_node)
        if not getattr(n, "exclude", False)
    ]        
    # exclude_old_nodes(ss.root_node, timestamp)

st.header("pages_response")
if "pages_response" in ss:
    st.dataframe(data=ss.pages_response, column_order=column_order, column_config=column_config)
st.header("excluded_pages")
if "excluded_pages" in ss:
    st.dataframe(data=ss.excluded_pages, column_order=column_order, column_config=column_config)
st.header("filtered_pages")
if "filtered_pages" in ss:
    st.dataframe(data=ss.filtered_pages, column_order=column_order, column_config=column_config)


# page = ConfluencePage("id", "title", "")

# Create nodes to display
nodes = [
    {"label": "Folder A", "value": "folder_a"},
    {
        "label": "Folder B",
        "value": "folder_b",
        "children": [
            {"label": "Sub-folder A", "value": "page.id"},
            {"label": "Sub-folder B", "value": "sub_b"},
            {"label": "Sub-folder C", "value": "sub_c"},
        ],
    },
    {
        "label": ("Folder C", 123),
        "value": "folder_c",
        "children": [
            {"label": "Sub-folder D", "value": "sub_d"},
            {
                "label": "Sub-folder E",
                "value": "sub_e",
                "children": [
                    {"label": "Sub-sub-folder A", "value": "sub_sub_a"},
                    {"label": "Sub-sub-folder B", "value": "sub_sub_b"},
                ],
            },
            {"label": "Sub-folder F", "value": "sub_f"},
        ],
    },
]

checked = ["folder_a", "id", "sub_b"]
return_select = tree_select(nodes, checked=checked, show_expand_all=True)
st.write(return_select)

# Test code that calls API instead of using main.py

if hasattr(st, "already_started_server"):
    ss.api_response = ""
    if st.button("Call API"):
        response = "response2 placeholder"
        url = "http://127.0.0.1:3000/confluence_pages?page_title=Design%20and%20Prototyping"
        response = requests.get(url)
        print(response.json())
        ss.api_response = str(response.json())
    st.write(ss.api_response)
