import logging
import os
import requests
import streamlit as st
from streamlit_tree_select import tree_select

from main import ConfluencePage, get_confluence_pages, recurse_pages

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

# Add button to query API
space_key = st.text_input("space key", "NL")
# page_title = st.text_input("page title", "Design and Prototyping")
page_title = st.text_input("page title", "Product")

ss.spaces_response = {}
if st.button("Run direct"):
    response = "response1 placeholder"
    # ss.spaces_response = get_confluence_pages(space_key, page_title)
    ss.spaces_response = recurse_pages(space_key, page_title)

# st.json(ss.spaces_response)
st.dataframe(data=ss.spaces_response)


page = ConfluencePage("id", "title", "")

# Create nodes to display
nodes = [
    {"label": "Folder A", "value": "folder_a"},
    {
        "label": "Folder B",
        "value": "folder_b",
        "children": [
            {"label": "Sub-folder A", "value": page.id},
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
