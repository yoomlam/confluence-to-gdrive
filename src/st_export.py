import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from queue import Queue

import pandas as pd
import streamlit as st
from anytree import PreOrderIter
from streamlit_tree_select import tree_select

import main
import ui_helpers
from ui_helpers import PageNode, StreamlitThreader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

st.header("➡️ Export Confluence pages")
ui_helpers.patch_streamlit_file_browser_html_preview()


@st.cache_data
def _query_confluence_spaces():
    return main.get_confluence_spaces()


@st.cache_data
def _build_tree(space_key, page_title):
    root_node = main.query_pages_as_tree(space_key, page_title)
    for n in PreOrderIter(root_node):
        n.include = n.to_export = True
    return root_node


ss = st.session_state
conf_base_url = main.confluence_base_url()
ss.selected_space = None

with st.expander(
    "List spaces", expanded=ss.selected_space is None and not ss.get("root_node", None)
):

    def query_spaces():
        with st.spinner(f"Querying {conf_base_url}...", show_time=True):
            ss.spaces = _query_confluence_spaces()

    if not bool(ss.get("spaces", None)):
        st.write("Skip if you know the Confluence space key")
        st.button(
            "Query Confluence spaces",
            disabled=bool(ss.get("spaces", None)),
            on_click=query_spaces,
        )

    if ss.get("spaces", None):

        spaces_df = pd.DataFrame(ss.spaces).set_index("id")
        if spaces_df.empty:
            st.write("No spaces found")
        else:
            space_selection = st.empty()
            selected_row = {
                "space_key": "Click in first column to select",
                "name": "all Confluence spaces",
                "webui": "/spaces",
            }

            # https://docs.streamlit.io/develop/api-reference/data/st.dataframe
            # https://docs.streamlit.io/develop/tutorials/elements/dataframe-row-selections
            event = st.dataframe(
                data=spaces_df,
                on_select="rerun",
                selection_mode="single-row",
                column_order=["space_key", "name"],
                hide_index=True,
            )
            if event.selection.rows:
                ss.selected_space = spaces_df.iloc[event.selection.rows[0]]
                selected_row = ss.selected_space
            else:
                # Selection unselected
                ss.selected_space = None

            with space_selection.container():
                st.write(
                    f"**{selected_row['space_key']}** ([{selected_row['name']}]({conf_base_url}{selected_row['webui']}))"
                )


def reset_tree(manual_select_expanded=None):
    # set a new key so that the tree width is rerendered
    ss.tree_key = f"page_tree_{time.time()}"

    if manual_select_expanded is not None:
        ss.manual_select_expanded = manual_select_expanded


def build_tree_for_pages():
    logger.info(f"build_tree_for_pages: {space_key} {page_title!r}")
    try:
        with st.spinner("Querying Confluence pages...", show_time=True):
            ss.root_node = _build_tree(space_key, page_title)
            ss.query_error = None
    except Exception as e:
        logger.error("while build_tree_for_pages(): %r", e)
        ss.query_error = e
        ss.root_node = None

    reset_tree()
    ss.reset_previous_export = True


# Use a form to collect input and prevent updates after submission
# When you don't want to rerun your script with each input made by a user
# https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#forms-and-callbacks

with st.expander("Query a page and its subpages", expanded=not bool(ss.get("root_node", None))):
    space_input_col, space_link_col = st.columns(2, vertical_alignment="bottom")
    space_key = space_input_col.text_input(
        "Confluence space key",
        ss.selected_space["space_key"] if ss.selected_space is not None else "NL",
        disabled=ss.selected_space is not None,
    )
    space_name = ss.selected_space["name"] if ss.selected_space is not None else space_key
    space_link_col.markdown(f"[{space_name}]({conf_base_url}/spaces/{space_key})")

    with st.form("query_pages_form"):
        page_title = st.text_input("Confluence page title", "Product")  # "overview"

        # Gotcha: Use the `on_click=` callback (rather than `if st.button(...):`) to disable the button after a click
        # https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
        # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#use-callbacks-to-update-session-state
        st.form_submit_button(
            "Query pages",
            # disabled=bool(ss.get("root_node", None)),
            on_click=build_tree_for_pages,
        )

    if query_error := ss.get("query_error", None):
        st.write(f"Error querying `{page_title}` in space **{space_key}**: {query_error}")

with st.expander("Filter pages by date", expanded=False):
    # ss.root_node will be None if query fails
    if ss.get("root_node", None):
        page_count = sum(1 for _ in PreOrderIter(ss.root_node))
        st.subheader(f"{page_count} pages found")

        with st.form(border=True, key="date_filter_form"):
            date_col, time_col, filter_btn_col = st.columns(3, vertical_alignment="bottom")
            after_date = date_col.date_input(
                "after modified date", "2024-08-25", format="YYYY-MM-DD"
            )
            after_time = time_col.time_input(
                "after modified time", "00:00:00", step=timedelta(hours=1)
            )
            ss.timestamp = datetime.strptime(f"{after_date}T{after_time}Z", "%Y-%m-%dT%H:%M:%SZ")

            if filter_btn_col.form_submit_button("Filter"):
                ui_helpers.exclude_old_nodes(ss.root_node, ss.timestamp)
                ss.reset_previous_export = True

        excluded_count = sum(1 for n in PreOrderIter(ss.root_node) if not n.include)

        st.write(f"{excluded_count} pages excluded")

        def page_included_style(val: dict) -> list[str]:
            style = "background-color: green" if val["include"] else "color: gray"
            # Use the same style for all val's attributes
            return [style if attr == "include" else "" for attr in val.keys()]

        page_nodes = [PageNode(n).as_row() for n in PreOrderIter(ss.root_node)]
        st.dataframe(
            data=pd.DataFrame(page_nodes).set_index("id").style.apply(page_included_style, axis=1),
            hide_index=True,
            column_order=["include", "link", "modified", "parent"],
            column_config={
                "include": "included",
                "link": st.column_config.LinkColumn(
                    "Link", display_text=f"{conf_base_url}/spaces/.*/pages/[0-9]*/(.*)"
                ),
                "parent": "Parent page",
            },
        )

if "manual_select_expanded" not in ss:
    ss.manual_select_expanded = False

if "tree_key" not in ss:
    ss.tree_key = "page_tree"

with st.expander("Manually select pages to export", expanded=ss.manual_select_expanded):
    ss.exporting = ss.get("export_btn", False)
    if ss.get("root_node", None):
        # st.subheader("Page hierarchy")
        if st.button(
            "Refresh/reset page hierarchy",
            on_click=reset_tree,
            kwargs={"manual_select_expanded": True},
        ):
            # Reset expanded state
            ss.manual_select_expanded = False
            ss.reset_previous_export = True

        tree_nodes = ui_helpers.generate_dict_from_tree(ss.root_node)
        included_ids = [node.id for node in PreOrderIter(ss.root_node) if node.include]
        tree_state = tree_select(
            tree_nodes,
            checked=included_ids,
            show_expand_all=True,
            key=ss.tree_key,
        )

        # Update nodes based on tree selections
        for n in PreOrderIter(ss.root_node):
            n.to_export = n.id in tree_state["checked"]
        to_export_node_ids = [node.id for node in PreOrderIter(ss.root_node) if node.to_export]

        selections_differ = set(included_ids) != set(to_export_node_ids)

if "default_profile_name" not in ss:
    ss.default_profile_name = f"profile_{time.time()}"

if "reset_previous_export" not in ss:
    ss.reset_previous_export = False

if "uploaded_to_gdrive" not in ss:
    ss.uploaded_to_gdrive = False

if ss.reset_previous_export:
    if "export_threader" in ss:
        del ss.export_threader
    ss.uploaded_to_gdrive = False
    ss.reset_previous_export = False

with st.expander("Export to HTML", expanded=not ss.uploaded_to_gdrive):
    if ss.get("root_node", None):
        st.write(f"{len(to_export_node_ids)} pages selected for exporting")

        st.text_input("Profile name", ss.default_profile_name, key="profile_name")
        if not ss.profile_name or not ss.profile_name[0].isalpha():
            st.error(f"Profile name `{ss.profile_name}` must start with a letter!")
        else:
            ss.export_folder = f"./exports/{ss.profile_name}"
            st.write(f"Export folder: `{ss.export_folder}`")

            if "export_threader" not in ss:
                ss.export_threader = StreamlitThreader("Exporter", ss)

            delete_folder = st.checkbox("Empty/delete folder before exporting", True)

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

                    node_ids = [n.id for n in PreOrderIter(root_node) if n.to_export]
                    if not node_ids:
                        logger.info("Nothing to export")
                        return

                    os.makedirs(export_folder, exist_ok=True)
                    logger.info("node_ids to export: %r", node_ids)
                    # Update original n.include so that a refresh retains selections
                    for n in PreOrderIter(root_node):
                        n.include = n.to_export

                    main.export_html_folder(root_node, export_folder, queue=queue)

                ss.export_threader.start_thread(export_pages)

            st.button(
                "Export checked pages",
                disabled=ss.exporting,
                on_click=start_exporter_thread,
                key="export_btn",
            )

if ss.get("root_node", None) and ss.get("export_threader", None):
    ss.export_threader.create_status_container(st)
