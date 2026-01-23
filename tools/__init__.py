# tools/__init__.py
from .base import ToolRegistry, tool_registry
from .knowledge_tools import (
    add_knowledge_node,
    query_node,
    search_similar_nodes,
    delete_knowledge_node,
    list_all_nodes,
)
from .graph_tools import (
    add_dependency,
    get_learning_path,
    get_graph_structure,
    delete_node,
    merge_nodes,
    init_database,
)
from .learning_tools import (
    update_proficiency,
    add_problem,
    get_unlearned_prerequisites,
)
# 在 tools/__init__.py 中添加
from .bash_tools import bash  # 导入 bash 工具



__all__ = [
    "ToolRegistry",
    "tool_registry",
    "add_knowledge_node",
    "query_node",
    "search_similar_nodes",
    "delete_knowledge_node",
    "delete_node",
    "list_all_nodes",
    "add_dependency",
    "get_learning_path",
    "get_graph_structure",
    "merge_nodes",
    "init_database",
    "update_proficiency",
    "add_problem",
    "get_unlearned_prerequisites",
    "bash",
]
