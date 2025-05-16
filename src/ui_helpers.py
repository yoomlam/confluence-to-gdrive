import os
from anytree import Node, PreOrderIter
from streamlit_embeded import st_embeded

class PageNode:
    def __init__(self, node: Node):
        self.node = node
        node.include = True

    def as_row(self):
        return {
            "id": self.node.id,
            "title": self.node.title,
            "modified": self.node.modified,
            "parent": self.node.parent.title if self.node.parent else None,
            "include": self.node.include,
        }


def exclude_old_nodes(root_node, timestamp):
    for n in PreOrderIter(root_node):
        n.include = n.modified >= timestamp


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
            "label": f"{node.title} subpages",
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
    PREVIEW_HANDLERS[".html"]=patched_do_html_preview
    PREVIEW_HANDLERS[".htm"]=patched_do_html_preview


from datetime import datetime

test_pages_response = [
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
test_nodes = [
    {"label": "Product", "value": "927367268"},
    {
        "label": "Product subpages",
        "value": "children_927367268",
        "children": [
            {"label": "Feature Brief: Extensible data sources", "value": "1203175560"},
            {
                "label": "Feature Brief: Extensible data sources subpages",
                "value": "children_1203175560",
                "children": [
                    {"label": "Tech spec for ingesting policy PDFs", "value": "1233616975"},
                    {
                        "label": "Evaluation Criteria for PDF-Parsing Tools",
                        "value": "1291419695",
                    },
                    {"label": "Tech Spec for improving PDF parsing", "value": "1305083960"},
                    {
                        "label": "Tech Spec for improving PDF parsing subpages",
                        "value": "children_1305083960",
                        "children": [
                            {
                                "label": "Sample inputs and outputs for test cases",
                                "value": "1307967493",
                            }
                        ],
                    },
                    {
                        "label": "Tech Spec: Separating Chunks and Citations",
                        "value": "1342177290",
                    },
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
    },
]
