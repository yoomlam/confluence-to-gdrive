from anytree import Node, PreOrderIter

class PageNode:
    def __init__(self, node: Node):
        self.node = node

    def as_row(self):
        return {
            "id": self.node.id,
            "title": self.node.title,
            "modified": self.node.modified,
            "parent": self.node.parent.title if self.node.parent else None,
            "include": getattr(self.node, "include", True),
        }

def exclude_old_nodes(root_node, timestamp):
    for n in PreOrderIter(root_node):
        if n.modified < timestamp:
            n.include = False


def generate_dict_from_tree(node):
    """
    Generates a dictionary data structure with nested children nodes from an anytree node.
    """
    node_dict = {
        "label": node.title,
        "value": node.id,
    }
    if node.children:
        node_dict["children"] = [generate_dict_from_tree(child) for child in node.children]
    return node_dict



