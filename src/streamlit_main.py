import logging
import os
import random
import shutil
import time
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread

import pandas as pd
import requests
import streamlit as st
from anytree import Node, PreOrderIter
from streamlit_file_browser import st_file_browser
from streamlit_tree_select import tree_select

import gdrive_client
import main
import ui_helpers
from ui_helpers import PageNode, StreamlitThreader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

st.set_page_config(layout="wide")
st.write("Welcome")
ui_helpers.patch_streamlit_file_browser_html_preview()

ss = st.session_state

tab_spaces, tab_query, tab_export, tab_preview, tab_gdrive = st.tabs(
    ["Spaces", "Query", "Export", "Preview", "G Drive"]
)


@st.cache_data
def _query_confluence_spaces():
    return main.get_confluence_spaces()


@st.cache_data
def _build_tree(space_key, page_title):
    return main.query_pages_as_tree(space_key, page_title)


conf_base_url = main.confluence_base_url()

with tab_spaces:

    def build_tree_for_pages():
        with ss.query_spaces_status:
            with st.spinner(f"Querying {conf_base_url}...", show_time=True):
                ss.spaces = _query_confluence_spaces()

    st.write("OPTIONAL -- skip if you know the Confluence space key")
    st.button(
        "Query Confluence spaces",
        disabled=bool(ss.get("spaces", None)),
        on_click=build_tree_for_pages,
    )
    if "query_spaces_status" not in ss:
        ss.query_spaces_status = st.container()

    if "spaces" in ss:
        # st.json(ss.spaces)
        df = pd.DataFrame(ss.spaces).set_index("id")
        # https://docs.streamlit.io/develop/api-reference/data/st.dataframe
        # https://docs.streamlit.io/develop/tutorials/elements/dataframe-row-selections
        event = st.dataframe(data=df, on_select="rerun", selection_mode="single-row")
        if event.selection.rows:
            selected_row = event.selection.rows[0]
            df.iloc[selected_row].to_dict()
            selected_space = df.iloc[selected_row]
            st.write(f"Selected space: {conf_base_url}{selected_space['webui']}")
            st.write(selected_space)
            ss.default_space_key = selected_space["space_key"]
        elif "default_space_key" in ss:
            del ss.default_space_key

with tab_query:

    def build_tree_for_pages():
        with ss.query_pages_status:
            with st.spinner("Querying Confluence pages...", show_time=True):
                ss.root_node = _build_tree(space_key, page_title)

    # Use a form to collect input and prevent updates after submission
    # When you don't want to rerun your script with each input made by a user
    # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#forms-and-callbacks

    with st.form("pages_form"):
        if "default_space_key" in ss:
            space_key = st.text_input("Confluence space key", ss.default_space_key, disabled=True)
        else:
            space_key = st.text_input("Confluence space key", "NL")  # "NH"
        page_title = st.text_input("Confluence page title", "Product")  # "overview"

        # Gotcha: Use the `on_click=` callback (rather than `if st.button(...):`) to disable the button after a click
        # https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
        # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#use-callbacks-to-update-session-state
        st.form_submit_button(
            "Query pages",
            disabled=bool(ss.get("root_node", None)),
            on_click=build_tree_for_pages,
        )

        if "query_pages_status" not in ss:
            ss.query_pages_status = st.container()

    filtering_disabled = ss.get("different_tree_selection", False)

    with st.container(border=True):
        date_col, time_col = st.columns(2)
        after_date = date_col.date_input(
            "after date", "2024-08-25", format="YYYY-MM-DD", disabled=filtering_disabled
        )
        after_time = time_col.time_input(
            "after time", "00:00:00", step=timedelta(hours=1), disabled=filtering_disabled
        )
        timestamp = datetime.strptime(f"{after_date}T{after_time}Z", "%Y-%m-%dT%H:%M:%SZ")

    if "root_node" in ss:
        ui_helpers.exclude_old_nodes(ss.root_node, timestamp)
        page_nodes = [PageNode(n).as_row() for n in PreOrderIter(ss.root_node)]
        page_count = len(page_nodes)
        st.subheader(f"{page_count} pages")
        excluded_count = sum(1 for n in PreOrderIter(ss.root_node) if not n.include)
        st.write(f"{excluded_count} pages excluded due to modification date filter: {timestamp}")

        def page_included_style(val: dict) -> list[str]:
            style = "background-color: green" if val["include"] else "color: gray"
            # Use the same style for all val's attributes
            return [style if attr == "include" else "" for attr in val.keys()]

        df = pd.DataFrame(page_nodes).set_index("id")
        if filtering_disabled:
            column_order = ["link", "modified", "parent"]
        else:
            column_order = ["include", "link", "modified", "parent"]
        st.dataframe(
            data=df.style.apply(page_included_style, axis=1),
            hide_index=True,
            column_order=column_order,
            column_config={
                "include": "included",
                "link": st.column_config.LinkColumn(
                    "Link", display_text=f"{conf_base_url}/spaces/{space_key}/pages/[0-9]*/(.*)"
                ),
            },
        )

with tab_export:
    if "root_node" in ss:
        st.subheader("Page hierarchy")
        tree_nodes = ui_helpers.generate_dict_from_tree(ss.root_node)
        checked = [node.id for node in PreOrderIter(ss.root_node) if node.include]
        # checked
        return_select = tree_select(tree_nodes, checked=checked, show_expand_all=True)

        # Update nodes based on tree selections
        for n in PreOrderIter(ss.root_node):
            n.include = n.id in return_select["checked"]
        checked_nodes = [n for n in PreOrderIter(ss.root_node) if n.include]
        st.write(f"{len(checked_nodes)} pages selected for exporting")

        ss.different_tree_selection = set(checked) != set(return_select["checked"])
        if ss.different_tree_selection:
            st.write("Different selections than date filtering")
            # return_select["checked"]

    export_folder = "./exported_pages"

    ss.deleting = ss.get("delete_btn", False)
    ss.exporting = ss.get("export_btn", False)

    if st.button(
        "Delete exported html folder", disabled=ss.deleting or ss.exporting, key="delete_btn"
    ):
        # TODO: Add confirmation dialog
        shutil.rmtree(export_folder)
        os.makedirs(export_folder, exist_ok=True)
        st.rerun()

    if "root_node" not in ss:
        st.write("Query pages in order to export them")
    else:
        if "export_threader" not in ss:
            ss.export_threader = StreamlitThreader("Exporter", ss)

        def start_exporter_thread():
            root_node = ss.root_node
            def export_pages(queue: Queue):
                # main.export_html_folder(root_node, export_folder, queue=queue)
                for item in range(5):
                    # print(f"{export_folder} produced item A{item}")
                    queue.put(f"exporter_thread: {export_folder} A{item} {root_node.id}")
                    time.sleep(2)

            ss.export_threader.start_thread(export_pages)

        st.button(
            "Export checked pages",
            disabled=ss.deleting or ss.exporting,
            on_click=start_exporter_thread,
            key="export_btn",
        )
        ss.export_threader.create_status_container(st)

with tab_preview:
    # st.session_state

    @st.fragment
    def file_browser_fragment():
        if fb_event := st_file_browser(export_folder):
            location = fb_event["target"]["path"]
            st.write(f"Path: {location}")

    file_browser_fragment()

with tab_gdrive:
    SERVICE_ACCOUNT_FILE = "./gdrive_service_account.json"
    folder_id = st.text_input("GDrive folder ID", "1IMr0v3azM_8yaxTCkv2tQo22cSArk06Q")
    st.write(f"Destination folder: https://drive.google.com/drive/folders/{folder_id}")
    if "root_node" in ss:
        # TODO: List files that would be deleted
        delete_gfiles = st.checkbox("Delete GDrive files", value=False)
        dry_run = st.checkbox("Dry run (creates folders but not files)", value=True)

        if st.button("Sync with GDrive"):
            gclient = gdrive_client.GDriveClient(SERVICE_ACCOUNT_FILE)
            main.sync_folder_to_gdrive(
                gclient, export_folder, folder_id, delete_gfiles=delete_gfiles, dry_run=dry_run
            )
