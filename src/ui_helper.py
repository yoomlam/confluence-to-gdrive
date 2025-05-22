import logging
import os
import time
from queue import Queue
from threading import Thread

from anytree import Node, PreOrderIter
from main import ConfluenceOps
from streamlit_embeded import st_embeded

logger = logging.getLogger(__name__)


def retain_session_state(ss):
    # Set session state variables that we want to retain between pages,
    # i.e., variables that are shared across pages and variables used to set UI state
    # https://docs.streamlit.io/develop/concepts/architecture/widget-behavior#interrupting-the-widget-clean-up-process
    # https://docs.streamlit.io/develop/concepts/architecture/widget-behavior#save-widget-values-in-session-state-to-preserve-them-between-pages
    for var in ss.keys():
        if var in ss and not var.startswith("FormSubmitter"):
            ss[var] = ss[var]
    set_missing_initial_state(ss)


def set_missing_initial_state(ss):
    initial_vals = {
        # The following are set here for convenience
        # Every editable input widget should use one of these variables for the `key` parameter
        # to ensure that the value is retained as the user switches between pages
        # Caution: Note that since streamlit's internal callbacks for
        # input widgets __inside of forms__ do not get called,
        # the input widget values are not saved to session state
        # until the form_submit_button is clicked.
        # This is problematic if the button is disabled for certain input values.
        # https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state#forms-and-callbacks
        "input_confluence_url": "https://navasage.atlassian.net",
        "input_atl_username": "",
        "input_atl_api_key": "",
        "input_profile_name": f"profile_{time.time()}",
        "input_space_key": "",
        "input_page_title": "",
        "input_gdrive_folder_id": os.environ.get("GDRIVE_FOLDER_ID"),
        "chkbox_change_gdrive_folder_id": False,
        "chkbox_delete_folder_before_export": True,
        "chkbox_dry_run_upload": True,
        "chkbox_skip_existing_gdrive_files": False,
        "chkbox_delete_unmatched_files": False,
        # Populated upon data retrieval
        "spaces": None,  # Populated if user queries spaces
        "root_node": None,  # Populated when user queries pages
        # Derived from input fields
        "space_name": None,  # Derived from input_space_key
        # Used to affect UI state
        "tree_key": f"page_tree_{time.time()}",
        "space_selected": False,
        "query_error": None,
        "reset_previous_export": False,
        # "list_spaces_expanded": True,
        "manual_select_expanded": False,
        # Exporting from Confluence
        "export_threader": StreamlitThreader("Exporter", ss),
        # Uploading to GDrive
        "upload_threader": StreamlitThreader("Uploader", ss),
    }
    for var, val in initial_vals.items():
        if var not in ss:
            ss[var] = val

    if "export_folder" not in ss:
        ss.export_folder = f"./exports/{ss.input_profile_name}"


def create_confluence_ops(ss):
    return ConfluenceOps(
        # Empty values will default to using environment variables
        url=ss.input_confluence_url,
        username=ss.input_atl_username,
        api_key=ss.input_atl_api_key,
    )


class PageNode:
    def __init__(self, node: Node):
        self.node = node

    def as_row(self):
        return {
            "id": self.node.id,
            "title": self.node.title,
            "modified": self.node.modified,
            "parent": self.node.parent.title if self.node.parent else None,
            "include": self.node.include,
            "link": self.node.link,
        }


def exclude_old_nodes(root_node, timestamp):
    logger.info("exclude_old_nodes(%r, %r)", root_node.title, timestamp)
    for n in PreOrderIter(root_node):
        n.include = n.modified >= timestamp
        # logger.info("Node %r: %r >= %r : %r", n.id, n.modified, timestamp, n.include)


def generate_dict_from_tree(node):
    """
    Generates a dictionary data structure with nested children nodes from an anytree node.
    """
    node_dict = {
        "label": node.title,
        "value": node.id,
    }
    if node.children:
        parent_dict = {
            "label": f"subpages of '{node.title}'",
            "value": f"children_{node.id}",
        }
        parent_dict["children"] = [
            c for child in node.children for c in generate_dict_from_tree(child)
        ]
        return [node_dict, parent_dict]

    return [node_dict]


from streamlit_file_browser import PREVIEW_HANDLERS


def patch_streamlit_file_browser_html_preview():
    # streamlit_file_browser v3.2.22 has a bug in the html preview panel
    # https://github.com/pragmatic-streamlit/streamlit-file-browser/blob/85e9af4e8d9b8fecff35a569dcb5f150417328f1/streamlit_file_browser/__init__.py#L153

    def patched_do_html_preview(root, file_path, url, **kwargs):
        abs_path = os.path.join(root, file_path)
        with open(abs_path) as f:
            html = f.read()
            st_embeded(html, **kwargs)
        return True

    PREVIEW_HANDLERS[".html"] = patched_do_html_preview
    PREVIEW_HANDLERS[".htm"] = patched_do_html_preview


# Streamlit helpers


class StreamlitThreader:
    def __init__(self, name: str, st_session):
        self.ss = st_session
        self.name = name
        self.queue = Queue[str]()
        self.thread_log: list[dict] = []
        self.collapse_when_complete = False
        self.state = None
        self.thread = None
        self.status_container = None
        self.finalized = False

    def reset(self):
        # TODO: check if thread is alive and join it, and queue is empty
        self.thread_log.clear()
        self.state = None
        self.thread = None
        self.status_container = None
        self.finalized = False

    def start_thread(self, target):
        self.reset()

        def thread_target():
            try:
                target(self.queue)
            except Exception as e:
                logger.exception(e)
                self.queue.put(e)

        self.state = "running"
        self.thread = Thread(target=thread_target)
        self.thread.start()
        # TODO: interrupt thread in case the page is refreshed

    def is_alive(self):
        return bool(self.thread) and self.thread.is_alive()

    def is_done(self):
        return bool(self.thread) and not self.thread.is_alive()

    def create_status_container(self, st, update_interval=1):
        "Insert container to show thread's log/status for previous/current run"
        self.status_container = st.empty()

        if not self.thread or not self.thread.is_alive():
            # Don't need to repeatedly update status
            update_interval = None

        # Set up possibly recurring fragment to poll of thread status
        @st.fragment(run_every=update_interval)
        def update_status__fragment():
            logger.info("%s.update_status__fragment(%r)", self.name, update_interval)
            while not self.queue.empty():
                obj = self.queue.get()
                if isinstance(obj, Exception):
                    # Use threading.excepthook to handle thread error
                    self.state = "error"
                    self.thread_log.append(
                        {
                            "message": f"{self.name} thread error: {obj}",
                            "state": self.state,
                        }
                    )
                else:
                    self.thread_log.append({"message": obj})

            if self.is_done():
                if not self.finalized:
                    # Append a final message to the log
                    if self.state != "error":
                        self.state = "complete"
                    self.thread_log.append(
                        {"message": f"{self.name} {self.state}", "state": self.state}
                    )
                    self.finalized = True

                    # Cause create_status_container() is rerun so that update_interval is updated to None
                    st.rerun()

            self.render_status(st)

        update_status__fragment()

    def render_status(self, st):
        "Use st.status widget to show the thread status"
        if not self.status_container or not self.thread:
            return

        with self.status_container:
            status = st.status(f"{self.name} {self.state}", expanded=True, state=self.state)
            for log_obj in self.thread_log:
                str_msg = str(log_obj["message"])
                status.write(str_msg)
                if "state" in log_obj:
                    if self.collapse_when_complete and log_obj["state"] == "complete":
                        expanded = False
                    else:
                        expanded = True
                    status.update(
                        label=str_msg,
                        state=log_obj["state"],
                        expanded=expanded,
                    )
