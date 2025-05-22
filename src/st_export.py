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

import ui_helper
from ui_helper import PageNode

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

ss = st.session_state
ui_helper.retain_session_state(ss)

ui_helper.patch_streamlit_file_browser_html_preview()


@st.cache_data
def _query_confluence_spaces():
    return ui_helper.create_confluence_ops(ss).get_confluence_spaces()


@st.cache_data
def _build_tree(space_key, page_title):
    root_node = ui_helper.create_confluence_ops(ss).query_pages_as_tree(space_key, page_title)
    for n in PreOrderIter(root_node):
        n.include = n.to_export = True
    return root_node


st.header("➡️ Export Confluence pages")

if "confl_base_url" not in ss:
    ss.confl_base_url = ui_helper.create_confluence_ops(ss).confluence_api_url()

with st.expander(
    "List spaces",
    expanded=not (ss.space_name or ss.root_node) or (bool(ss.spaces) and not ss.space_selected),
):

    def query_spaces():
        with st.spinner(f"Querying {ss.confl_base_url}...", show_time=True):
            ss.spaces = _query_confluence_spaces()

    if not ss.spaces:
        st.write(
            "Skip if you know the Confluence space key."
            # "Check out [available communal spaces]({ss.confl_base_url}/spaces?spaceType=communal)."
        )
        st.button(
            "Query Confluence spaces",
            disabled=not ss.confl_base_url or bool(ss.spaces),
            on_click=query_spaces,
        )

    if ss.spaces:
        spaces_df = pd.DataFrame(ss.spaces).set_index("id")
        if spaces_df.empty:
            st.write("No spaces found")
        else:
            # space_selection_placeholder = st.empty()
            # https://docs.streamlit.io/develop/api-reference/data/st.dataframe
            # https://docs.streamlit.io/develop/tutorials/elements/dataframe-row-selections
            event = st.dataframe(
                data=spaces_df,
                on_select="rerun",
                selection_mode="single-row",
                column_order=["space_key", "name"],
                hide_index=True,
            )
            if rows := event.selection.rows:
                selection = spaces_df.iloc[rows[0]].to_dict()
                ss.space_selected = True
                ss.input_space_key = selection["space_key"]
                ss.space_name = selection["name"]
                ss.input_page_title = selection["homepage_title"]
            else:
                ss.space_selected = False
                # Do not set any other ss values since that would override the user's input when the page is rerun
                st.write(
                    f"Click in first column to select a space to use. See [all Confluence spaces]({ss.confl_base_url}/spaces)"
                )


def reset_tree(manual_select_expanded=None):
    # set a new key so that the tree width is rerendered
    ss.tree_key = f"page_tree_{time.time()}"

    if manual_select_expanded is not None:
        ss.manual_select_expanded = manual_select_expanded


def build_tree_for_pages():
    logger.info(f"build_tree_for_pages: {ss.input_space_key} {ss.input_page_title!r}")
    try:
        if ss.input_space_key:
            with st.spinner("Querying Confluence pages...", show_time=True):
                ss.root_node = _build_tree(ss.input_space_key, ss.input_page_title)
                # Reset any previous query error
                ss.query_error = None
    except Exception as e:
        logger.exception(e)
        ss.query_error = e
        ss.root_node = None

    logger.info(ss.root_node)
    reset_tree()
    ss.reset_previous_export = True


with st.expander(
    "**Query page and its subpages**", expanded=bool(ss.query_error) or not ss.root_node
):

    def find_space(space_key):
        try:
            return next(sp for sp in ss.spaces if sp["space_key"] == space_key)
        except StopIteration:
            st.error(f"Space key `{ss.input_space_key}` not found!")
        return None

    space_input_col, space_link_col = st.columns(2, vertical_alignment="bottom")
    space_input_col.text_input(
        "Confluence space key",
        key="input_space_key",
        disabled=ss.space_selected,
    )
    if ss.spaces:
        if found_space := find_space(ss.input_space_key):
            ss.space_name = found_space["name"]
            if not ss.input_page_title:
                ss.input_page_title = found_space["homepage_title"]
    else:
        ss.space_name = ss.input_space_key
    space_link_col.markdown(
        f"[{ss.space_name or 'not found'}]({ss.confl_base_url}/spaces/{ss.input_space_key})"
    )

    st.text_input(
        "Confluence page title",  # TODO: "(leave blank to get all pages)",
        key="input_page_title",
        placeholder="Title of Confluence page",
    )

    # Gotcha: Use the `on_click=` callback (rather than `if st.button(...):`) to disable the button after a click
    # https://discuss.streamlit.io/t/streamlit-button-disable-enable/31293
    # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#use-callbacks-to-update-session-state
    st.button(
        "Query page and its subpages",
        disabled=not ss.confl_base_url or not ss.input_space_key or not ss.input_page_title,
        on_click=build_tree_for_pages,
    )

    if ss.query_error:
        st.error(
            f"Error querying `{ss.input_page_title}` in space **{ss.input_space_key}**: {ss.query_error}"
        )

with st.expander("Filter pages by date", expanded=False):
    # ss.root_node will be None if query fails
    if ss.root_node:
        page_count = sum(1 for _ in PreOrderIter(ss.root_node))
        st.subheader(f"Pages found: `{page_count}`")

        with st.form("date_filter_form", enter_to_submit=False):
            date_col, time_col, filter_btn_col = st.columns(3, vertical_alignment="bottom")
            after_date = date_col.date_input(
                "after modified date", "2025-01-19", format="YYYY-MM-DD"
            )
            after_time = time_col.time_input(
                "after modified time", "00:00:00", step=timedelta(hours=1)
            )
            timestamp = datetime.strptime(f"{after_date}T{after_time}Z", "%Y-%m-%dT%H:%M:%SZ")

            if filter_btn_col.form_submit_button("Filter"):
                ui_helper.exclude_old_nodes(ss.root_node, timestamp)
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
                    "Link", display_text=f"{ss.confl_base_url}/spaces/.*/pages/[0-9]*/(.*)"
                ),
                "parent": "Parent page",
            },
        )

with st.expander("Manually select pages to export", expanded=ss.manual_select_expanded):
    if ss.root_node:
        # st.subheader("Page hierarchy")
        if st.button(
            "Refresh/reset page hierarchy to match included pages above",
            on_click=reset_tree,
            kwargs={"manual_select_expanded": True},
        ):
            # Reset expanded state after the page is rerun
            ss.manual_select_expanded = False
            # Cause previous export to be reset
            ss.reset_previous_export = True

        tree_nodes = ui_helper.generate_dict_from_tree(ss.root_node)
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


if ss.reset_previous_export:
    if "export_threader" in ss:
        del ss.export_threader
    ss.reset_previous_export = False

with st.expander("**Export to HTML**", expanded=True):
    if ss.root_node:
        st.write(f"Pages selected for export: `{len(to_export_node_ids)}`")

        if not ss.export_folder:
            st.error("Export folder is not set correcly in **Advanced settings**.")
        else:
            st.write(f"Export folder: `{ss.export_folder}`")

            delete_folder = st.checkbox(
                "Empty/delete folder before exporting",
                key="chkbox_delete_folder_before_export",
            )

            def start_exporter_thread():
                # ss itself cannot be accessed in a different thread,
                # so extract desired variables for export_pages() to use in separate thread
                _root_node = ss.root_node
                _export_folder = ss.export_folder
                _export_html_folder = ui_helper.create_confluence_ops(ss).export_html_folder

                def export_pages(queue: Queue):
                    # check if export_folder exists
                    if delete_folder and os.path.exists(_export_folder):
                        queue.put(f"Deleting folder {_export_folder}")
                        shutil.rmtree(_export_folder)

                    node_ids = [n.id for n in PreOrderIter(_root_node) if n.to_export]
                    if not node_ids:
                        logger.info("Nothing to export")
                        return

                    os.makedirs(_export_folder, exist_ok=True)
                    logger.info("node_ids to export: %r", node_ids)
                    # Update original n.include so that a refresh retains selections
                    for n in PreOrderIter(_root_node):
                        n.include = n.to_export

                    _export_html_folder(_root_node, _export_folder, queue=queue)

                ss.exporting = True
                ss.export_threader.start_thread(export_pages)
                ss.exporting = False

            st.button(
                "Export checked pages",
                disabled=ss.exporting or not to_export_node_ids,
                on_click=start_exporter_thread,
                # key="export_btn",
            )

if ss.root_node and ss.export_threader:
    ss.export_threader.create_status_container(st)
