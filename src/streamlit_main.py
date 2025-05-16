import logging
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from anytree import search, PreOrderIter
from streamlit_file_browser import st_file_browser
from streamlit_tree_select import tree_select

import gdrive_client
import main
import ui_helpers
from ui_helpers import PageNode

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

st.set_page_config(layout="wide")
st.write("Welcome")
ui_helpers.patch_streamlit_file_browser_html_preview()

ss = st.session_state

tab_config, tab_pages, tab_gdrive = st.tabs(["Config", "C Pages", "G Drive"])

with tab_config:
    if st.button("Query spaces"):
        ss.spaces_response = main.get_confluence_spaces()
    if "spaces_response" in ss:
        # st.json(ss.spaces_response)
        st.dataframe(data=ss.spaces_response)




def update_tree():
    ss.nodes = ui_helpers.generate_dict_from_tree(ss.root_node)
    ss.checked = [
        node.id
        for node in search.findall(ss.root_node, filter_=lambda n: getattr(n, "include", True))
    ]

with tab_pages:
    # TODO: Use a form to collect input and prevent updates after submission
    # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#forms-and-callbacks

    # Add button to query API
    space_key = st.text_input("space key", "NL")
    # page_title = st.text_input("page title", "Design and Prototyping")
    page_title = st.text_input("page title", "Product")

    column_order = None  
    # ["id", "title", "modified", "parent"]
    column_config = None
    # {
    #     "node": None,
    #     "id": "ID",
    #     "title": "Title",
    #     "modified": "Modified",
    #     "parent": "Parent",
    # }

    if st.button("Query pages"):
        ss.root_node = main.build_tree(space_key, page_title)
        ss.pages_response = [PageNode(n).as_row() for n in PreOrderIter(ss.root_node)]
        update_tree()

    after_date = st.date_input("after date", "2024-08-25", format="YYYY-MM-DD")
    after_time = st.time_input("after time", "00:00:00")
    date_str = f"{after_date}T{after_time}.000Z"
    timestamp = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    st.write(timestamp)

    if "pages_response" not in ss:
        ss.pages_response = ui_helpers.test_pages_response


    if st.button("Filter"):
        ui_helpers.exclude_old_nodes(ss.root_node, timestamp)
        ss.pages_response = [PageNode(n).as_row() for n in PreOrderIter(ss.root_node)]

        ss.excluded_pages = [
            PageNode(n).as_row() for n in PreOrderIter(ss.root_node) if not getattr(n, "include", True)
        ]

        # ss.included_pages = [
        #     PageNode(n).as_row()
        #     for n in PreOrderIter(ss.root_node)
        #     if getattr(n, "include", True)
        # ]

        update_tree()


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
    with st.expander("Detailed exclusions"):
        if "excluded_pages" in ss:
            st.subheader("excluded_pages")
            st.dataframe(data=ss.excluded_pages, column_order=column_order, column_config=column_config)
        if "included_pages" in ss:
            st.subheader("included_pages")
            st.dataframe(data=ss.included_pages, column_order=column_order, column_config=column_config)


    if "nodes" not in ss:
        ss.nodes = ui_helpers.test_nodes
    if "checked" not in ss:
        ss.checked = [
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

    st.subheader("tree")
    # ss.nodes
    # ss.checked
    return_select = tree_select(ss.nodes, checked=ss.checked, show_expand_all=True)
    st.write(return_select["checked"])

import shutil

with tab_gdrive:
    html_folder = "./htmls/"
    if st.button("Reset htmls folder"):
        shutil.rmtree(html_folder)
        os.makedirs(html_folder, exist_ok=True)

    if st.button("Export htmls"):
        main.export_html_folder(ss.root_node, html_folder)

    event = st_file_browser(html_folder)
    st.write(event)

    SERVICE_ACCOUNT_FILE = './gdrive_service_account.json'
    folder_id = st.text_input("GDrive folder ID", "1IMr0v3azM_8yaxTCkv2tQo22cSArk06Q")
    delete_gfiles = st.checkbox("Delete GDrive files", value=False)
    dry_run = st.checkbox("Dry run (creates folders but not files)", value=True)

    if st.button("Sync with GDrive"):
        gclient = gdrive_client.GDriveClient(SERVICE_ACCOUNT_FILE)
        main.sync_folder_to_gdrive(
            gclient, html_folder, folder_id, delete_gfiles=delete_gfiles, dry_run=dry_run
        )

    st.write(f"https://drive.google.com/drive/folders/{folder_id}")

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
