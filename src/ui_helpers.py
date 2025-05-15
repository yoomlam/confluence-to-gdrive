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
        parent_dict["children"] = [c for child in node.children for c in generate_dict_from_tree(child)]
        return [node_dict, parent_dict]    
    
    return [node_dict]



