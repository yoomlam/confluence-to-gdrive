import logging
import os
import requests
import streamlit as st
from streamlit_tree_select import tree_select
import pandas as pd
from main import get_confluence_pages, recurse_pages
from main import *
from ui_helpers import *

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


if st.button("Query spaces"):
    ss.spaces_response = get_confluence_spaces(space_key, page_title)
if "spaces_response" in ss:
    # st.json(ss.spaces_response)
    st.dataframe(data=ss.spaces_response)

column_order = None  # ["id", "title", "modified", "parent"]
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
    ss.pages_response = [PageNode(n).as_row() for n in flatten_page_tree(ss.root_node)]
    ss.nodes = {node.id: node for node in PreOrderIter(ss.root_node)}

after_date = st.date_input("after date", "2024-08-25", format="YYYY-MM-DD")
after_time = st.time_input("after time", "00:00:00")
date_str = f"{after_date}T{after_time}.000Z"
timestamp = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
st.write(timestamp)

ss.pages_response = [
    {
        "id": "927367268",
        "title": "Product",
        "modified": datetime(2024, 1, 22, 19, 28, 16, 391000),
        "parent": None,
        "include": False,
    },
    {
        "id": "1203175560",
        "title": "Feature Brief: Extensible data sources",
        "modified": datetime(2024, 7, 2, 17, 1, 35, 953000),
        "parent": "Product",
        "include": False,
    },
    {
        "id": "1233616975",
        "title": "Tech spec for ingesting policy PDFs",
        "modified": datetime(2024, 7, 18, 15, 59, 35, 878000),
        "parent": "Feature Brief: Extensible data sources",
        "include": False,
    },
    {
        "id": "1291419695",
        "title": "Evaluation Criteria for PDF-Parsing Tools",
        "modified": datetime(2024, 8, 22, 21, 12, 24, 994000),
        "parent": "Feature Brief: Extensible data sources",
        "include": False,
    },
    {
        "id": "1305083960",
        "title": "Tech Spec for improving PDF parsing",
        "modified": datetime(2024, 8, 28, 19, 26, 44, 862000),
        "parent": "Feature Brief: Extensible data sources",
        "include": True,
    },
    {
        "id": "1307967493",
        "title": "Sample inputs and outputs for test cases",
        "modified": datetime(2024, 8, 22, 17, 27, 47, 775000),
        "parent": "Tech Spec for improving PDF parsing",
        "include": False,
    },
    {
        "id": "1342177290",
        "title": "Tech Spec: Separating Chunks and Citations",
        "modified": datetime(2024, 9, 13, 13, 54, 5, 480000),
        "parent": "Feature Brief: Extensible data sources",
        "include": True,
    },
    {
        "id": "1384448006",
        "title": "Lightweight ingestion script for web sources",
        "modified": datetime(2024, 10, 2, 15, 23, 7, 632000),
        "parent": "Feature Brief: Extensible data sources",
        "include": True,
    },
    {
        "id": "1404895236",
        "title": "Tech Spec for Implementing Conversation History",
        "modified": datetime(2024, 10, 17, 20, 2, 49, 488000),
        "parent": "Product",
        "include": True,
    },
    {
        "id": "1417838624",
        "title": "Chatbot versioning strategy",
        "modified": datetime(2024, 10, 24, 22, 37, 40, 771000),
        "parent": "Product",
        "include": True,
    },
    {
        "id": "1590591516",
        "title": "Tech Spec: Automating QA evaluation pipeline for DST chat",
        "modified": datetime(2025, 1, 28, 18, 32, 43, 385000),
        "parent": "Product",
        "include": True,
    },
    {
        "id": "1549631705",
        "title": "[DRAFT] Tech Spec: Exploration of expert curation for DST evaluation",
        "modified": datetime(2025, 1, 30, 17, 48, 41, 542000),
        "parent": "Product",
        "include": True,
    },
]

if st.button("Filter"):
    exclude_old_nodes(ss.root_node, timestamp)
    ss.pages_response = [PageNode(n).as_row() for n in flatten_page_tree(ss.root_node)]

    ss.excluded_pages = [
        PageNode(n).as_row() for n in flatten_page_tree(ss.root_node) if getattr(n, "include", True)
    ]

    ss.included_pages = [
        PageNode(n).as_row()
        for n in flatten_page_tree(ss.root_node)
        if not getattr(n, "include", True)
    ]


def color_survived(val):
    color = "green" if val else "red"
    return f"background-color: {color}"


def page_included(val):
    color = "gray" if val["include"] else "darkgray"
    return [f"background-color: {color}"] * len(val)


# highlight cells based on condition
# st.dataframe(df.style.applymap(color_survived, subset=['Survived']))

st.subheader("pages_response")
if "pages_response" in ss:
    df = pd.DataFrame(ss.pages_response)
    st.dataframe(
        data=df.style.apply(page_included, axis=1),
        column_order=column_order,
        column_config=column_config,
    )
st.subheader("excluded_pages")
if "excluded_pages" in ss:
    st.dataframe(data=ss.excluded_pages, column_order=column_order, column_config=column_config)
st.subheader("included_pages")
if "included_pages" in ss:
    st.dataframe(data=ss.included_pages, column_order=column_order, column_config=column_config)


nodes = [
    {
        "label": "Product",
        "value": "927367268",
        "children": [
            {
                "label": "Feature Brief: Extensible data sources",
                "value": "1203175560",
                "children": [
                    {"label": "Tech spec for ingesting policy PDFs", "value": "1233616975"},
                    {"label": "Evaluation Criteria for PDF-Parsing Tools", "value": "1291419695"},
                    {
                        "label": "Tech Spec for improving PDF parsing",
                        "value": "1305083960",
                        "children": [
                            {
                                "label": "Sample inputs and outputs for test cases",
                                "value": "1307967493",
                            }
                        ],
                    },
                    {"label": "Tech Spec: Separating Chunks and Citations", "value": "1342177290"},
                    {
                        "label": "Lightweight ingestion script for web sources",
                        "value": "1384448006",
                    },
                ],
            },
            {"label": "Tech Spec for Implementing Conversation History", "value": "1404895236"},
            {"label": "Chatbot versioning strategy", "value": "1417838624"},
            {
                "label": "Tech Spec: Automating QA evaluation pipeline for DST chat",
                "value": "1590591516",
            },
            {
                "label": "[DRAFT] Tech Spec: Exploration of expert curation for DST evaluation",
                "value": "1549631705",
            },
        ],
    }
]
checked = [
    "927367268",
    "1203175560",
    "1233616975",
    "1291419695",
    "1305083960",
    "1404895236",
    "1417838624",
    "1590591516",
    "1549631705",
]
# Create nodes to display
if "root_node" in ss:
    nodes = [generate_dict_from_tree(ss.root_node)]
    nodes

    from anytree import search

    checked = [
        node.id
        for node in search.findall(ss.root_node, filter_=lambda n: getattr(n, "include", True))
    ]
st.subheader("tree")
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
