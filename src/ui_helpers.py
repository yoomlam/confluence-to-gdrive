import logging
import os
from anytree import Node, PreOrderIter
from streamlit_embeded import st_embeded
from datetime import datetime

logger = logging.getLogger(__name__)


class PageNode:
    def __init__(self, node: Node):
        self.node = node
        if not hasattr(node, "include"):
            node.include = True

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
    assert isinstance(timestamp, datetime)
    for n in PreOrderIter(root_node):
        assert isinstance(n.modified, datetime)
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
from queue import Queue
from threading import Thread


class StreamlitThreader:
    def __init__(self, name: str, st_session):
        self.ss = st_session
        self.name = name
        self.queue = Queue()
        self.alive = False

        self.thread_log = []
        self.thread = None

        self.status_container = None
        self.collapse_when_complete = False

    def start_thread(self, target):
        def thread_target():
            try:
                target(self.queue)
            except Exception as e:
                self.queue.put(e)

        self.thread_log.clear()
        self.alive = True
        self.thread = Thread(target=thread_target)
        self.thread.start()

    def create_status_container(self, st, update_interval=1):
        "Insert container to show thread's log/status for previous/current run"
        self.status_container = st.empty()

        if not self.alive:
            # render logs of previous thread run once
            self.render_status(st)
            return

        # Else set up recurring fragment to poll of thread status
        @st.fragment(run_every=update_interval)
        def update_status():
            print("update_status()")
            while not self.queue.empty():
                obj = self.queue.get()
                if isinstance(obj, Exception):
                    # Use threading.excepthook to handle thread error
                    self.thread_log.append(
                        {
                            "message": f"{self.name} thread error: {obj}",
                            "state": "error",
                        }
                    )
                else:
                    self.thread_log.append({"message": obj})

            if not self.thread.is_alive():
                self.alive = False
                self.thread_log.append(
                    {"message": f"{self.name} thread done", "state": "complete"}
                )

            self.render_status(st)

        update_status()

    def render_status(self, st):
        "Use st.status widget to show the thread status"
        if not self.status_container or not self.thread:
            return

        with self.status_container:
            status = st.status(f"{self.name} running", expanded=True)
            for log_obj in self.thread_log:
                str_msg = str(log_obj["message"])
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
                else:
                    status.write(str_msg)
