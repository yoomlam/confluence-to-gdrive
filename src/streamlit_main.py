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
st.write("Export Confluence pages to Google Drive")
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
    root_node = main.query_pages_as_tree(space_key, page_title)
    for n in PreOrderIter(root_node):
        n.include=True
    return root_node
    # try:
    #     return main.query_pages_as_tree(space_key, page_title)
    # except Exception as e:
    #     logger.error("Query error: %r", e)
    # return None

conf_base_url = main.confluence_base_url()

with tab_spaces:

    def query_spaces():
        with st.spinner(f"Querying {conf_base_url}...", show_time=True):
            time.sleep(5)
            ss.spaces = _query_confluence_spaces()

    st.write("OPTIONAL -- skip if you know the Confluence space key")
    st.button(
        "Query Confluence spaces",
        disabled=bool(ss.get("spaces", None)),
        on_click=query_spaces,
    )

    ss.selected_space = None
    if ss.get("spaces", None):

        df = pd.DataFrame(ss.spaces).set_index("id")
        if df.empty:
            st.write("No spaces found")
        else:
            space_selection = st.empty()
            selected_row = {"space_key": "???", "name": "all Confluence spaces", "webui": "/spaces"}

            # https://docs.streamlit.io/develop/api-reference/data/st.dataframe
            # https://docs.streamlit.io/develop/tutorials/elements/dataframe-row-selections
            event = st.dataframe(data=df, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                ss.selected_space = df.iloc[event.selection.rows[0]]
                selected_row = ss.selected_space
            else:
                # Selection unselected
                ss.selected_space = None

            with space_selection.container():
                click_space_reminder = (
                    ""
                    if ss.selected_space is not None
                    else "\n\n(Click in the first column to select a Confluence space)"
                )
                # selected_row
                # if 'webui' in selected_row:
                st.write(
                    f"**{selected_row['space_key']}**: [{selected_row['name']}]({conf_base_url}{selected_row['webui']}) {click_space_reminder}"
                )

with tab_query:
    def reset_tree():
        # set a new key so that the tree width is rerendered
        ss.tree_key=f"page_tree_{time.time()}"

    def build_tree_for_pages():
        logger.info(f"build_tree_for_pages(): {space_key}")
        try:
            with st.spinner("Querying Confluence pages...", show_time=True):
                ss.root_node = _build_tree(space_key, page_title)
                time.sleep(5)
        except Exception as e:
            logger.error("while build_tree_for_pages(): %r", e)
            ss.root_node = e

    # Use a form to collect input and prevent updates after submission
    # When you don't want to rerun your script with each input made by a user
    # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#forms-and-callbacks

    space_input_col, space_link_col = st.columns(2, vertical_alignment="bottom")
    space_key = space_input_col.text_input(
        "Confluence space key",
        ss.selected_space["space_key"] if ss.selected_space is not None else "NL",
        disabled=ss.selected_space is not None,
    )
    space_name = ss.selected_space["name"] if ss.selected_space is not None else space_key
    space_link_col.markdown(f"[{space_name}]({conf_base_url}/spaces/{space_key})")


    with st.form("pages_form"):
        page_title = st.text_input("Confluence page title", "Product")  # "overview"

        # Gotcha: Use the `on_click=` callback (rather than `if st.button(...):`) to disable the button after a click
        # https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
        # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#use-callbacks-to-update-session-state
        st.form_submit_button(
            "Query pages",
            # disabled=bool(ss.get("root_node", None)),
            on_click=build_tree_for_pages,
        )

    if ss.get("root_node", None) and isinstance(ss.root_node, Exception):
        st.write(f"Error querying **{space_key}**: {page_title!r}: {ss.root_node}")
        ss.root_node = None

    # ss.root_node may be None if query fails
    if ss.get("root_node", None):
        page_count = sum(1 for _ in PreOrderIter(ss.root_node))
        st.subheader(f"{page_count} pages")

        pages_panel_mt = st.empty()
        def render_pages_table():
            with pages_panel_mt.container():
                if ss.get("filtering_disabled", False):
                    st.write("Date filtering disabled due to difference")
                    st.button("Reset", on_click=reset_tree)
                else:
                    with st.container(border=True):
                        date_col, time_col = st.columns(2)
                        after_date = date_col.date_input(
                            "after modified date", "2024-08-25", format="YYYY-MM-DD",
                            disabled=ss.get("filtering_disabled", False)
                        )
                        after_time = time_col.time_input(
                            "after modified time", "00:00:00", step=timedelta(hours=1)
                        )
                        ss.timestamp = datetime.strptime(f"{after_date}T{after_time}Z", "%Y-%m-%dT%H:%M:%SZ")

                ui_helpers.exclude_old_nodes(ss.root_node, ss.timestamp)
                excluded_count = sum(1 for n in PreOrderIter(ss.root_node) if not n.include)

                if not ss.get("filtering_disabled", False):
                    st.write(
                        f"{excluded_count} pages excluded due to modification date filter: {ss.timestamp}"
                    )

                def page_included_style(val: dict) -> list[str]:
                    style = "background-color: green" if val["include"] else "color: gray"
                    # Use the same style for all val's attributes
                    return [style if attr == "include" else "" for attr in val.keys()]

                ss.filtering_disabled = ss.get("filtering_disabled", False)
                if ss.get("filtering_disabled", False):
                    column_order = ["link", "modified", "parent"]
                    ss.pages_table_key = "pages_table__no_include_col"
                else:
                    column_order = ["include", "link", "modified", "parent"]
                    ss.pages_table_key = "pages_table"
                page_nodes = [PageNode(n).as_row() for n in PreOrderIter(ss.root_node)]
                st.dataframe(
                    data=pd.DataFrame(page_nodes).set_index("id").style.apply(page_included_style, axis=1),
                    hide_index=True,
                    column_order=column_order,
                    column_config={
                        "include": "included",
                        "link": st.column_config.LinkColumn(
                            "Link", display_text=f"{conf_base_url}/spaces/.*/pages/[0-9]*/(.*)"
                        ),
                        "parent": "Parent page",
                    },
                    key=ss.pages_table_key
                )
        # render_pages_table()
    
with tab_export:
    if ss.get("root_node", None):
        st.subheader("Page hierarchy")
        if not ss.get("tree_key", None):
            ss.tree_key=f"page_tree"
            # ss.tree_key=f"page_tree__{ss.timestamp}"
        plh = st.empty()
        ss.tree_key
        tree_nodes = ui_helpers.generate_dict_from_tree(ss.root_node)
        checked_ids = [node.id for node in PreOrderIter(ss.root_node) if node.include]
        # checked_ids
        tree_state = tree_select(tree_nodes, checked=checked_ids, show_expand_all=True, key=ss.tree_key)

        # Update nodes based on tree selections
        for n in PreOrderIter(ss.root_node):
            n.include = n.id in tree_state["checked"]
        checked_nodes = [n for n in PreOrderIter(ss.root_node) if n.include]
        st.write(f"{len(checked_nodes)} pages selected for exporting")

        tree_state["checked"]
        ss.filtering_disabled = set(checked_ids) != set(tree_state["checked"])
        if ss.filtering_disabled:
            st.write("Different selections than date filtering")
            # ss.tree_key=f"page_tree__{ss.timestamp}_diff"
            with plh:
                st.button("Reset selection to time filtered selections", on_click=reset_tree)
                
        render_pages_table()
            # ss.pages_table_key = "pages_table__no_include_col"

    profile_name = st.text_input("Profile name", "exported_pages")
    ss.export_folder = f"./{profile_name}"

    ss.exporting = ss.get("export_form", False)

    if not ss.get("root_node", False):
        st.write("Query pages in order to export them")
    else:
        if "export_threader" not in ss:
            ss.export_threader = StreamlitThreader("Exporter", ss)

        with st.form("export_form"):
            # profile_name = st.text_input("Profile name", "exported_pages")
            # ss.export_folder = f"./{profile_name}"
            delete_folder = st.checkbox("Delete folder before exporting", True)

            def start_exporter_thread():
                # ss itself cannot be accessed in a different thread,
                # so extract desired variables for export_pages() to use in separate thread
                root_node = ss.root_node
                export_folder = ss.export_folder

                def export_pages(queue: Queue):
                    # check if export_folder exists
                    if delete_folder and os.path.exists(export_folder):
                        queue.put(f"Deleting folder {export_folder}")
                        shutil.rmtree(export_folder)

                    os.makedirs(export_folder, exist_ok=True)
                    # main.export_html_folder(root_node, export_folder, queue=queue)
                    for item in range(5):
                        print(f"exporter_thread: {export_folder} A{item} {root_node.id}")
                        queue.put(f"exporter_thread: {export_folder} A{item} {root_node.id}")
                        time.sleep(2)

                ss.export_threader.start_thread(export_pages)

            st.form_submit_button(
                "Export checked pages",
                # disabled=ss.exporting,
                on_click=start_exporter_thread,
                # key="export_btn",
            )
        ss.export_threader.create_status_container(st)

with tab_preview:
    st.write("Click on a file to preview its contents at the bottom of the page")

    @st.fragment
    def file_browser_fragment():
        if fb_event := st_file_browser(ss.export_folder, show_delete_file=True):
            location = fb_event["target"]["path"]
            st.write(f"Path: {location}")

    file_browser_fragment()

with tab_gdrive:
    SERVICE_ACCOUNT_FILE = "./gdrive_service_account.json"
    folder_id = st.text_input("GDrive folder ID", "1IMr0v3azM_8yaxTCkv2tQo22cSArk06Q")
    st.write(f"Destination folder: https://drive.google.com/drive/folders/{folder_id}")
    if ss.get("root_node", None):
        # TODO: List files that would be deleted
        delete_gfiles = st.checkbox("Delete GDrive files", value=False)
        dry_run = st.checkbox("Dry run (creates folders but not files)", value=True)

        if st.button("Sync with GDrive"):
            gclient = gdrive_client.GDriveClient(SERVICE_ACCOUNT_FILE)
            main.sync_folder_to_gdrive(
                gclient, ss.export_folder, folder_id, delete_gfiles=delete_gfiles, dry_run=dry_run
            )
