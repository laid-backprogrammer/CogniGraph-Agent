# tools/base.py
"""
工具基类和注册器 - LangChain 风格
"""

from typing import Dict, List, Callable, Any, Optional, Type
from dataclasses import dataclass, field
from functools import wraps
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from storage import SQLiteGraphStore, ChromaVectorStore
from config import get_settings


@dataclass
class ToolRegistry:
    """工具注册器"""
    _tools: Dict[str, BaseTool] = field(default_factory=dict)
    _graph_store: Optional[SQLiteGraphStore] = None
    _vector_store: Optional[ChromaVectorStore] = None

    @property
    def graph_store(self) -> SQLiteGraphStore:
        if self._graph_store is None:
            settings = get_settings()
            self._graph_store = SQLiteGraphStore(settings.sqlite_db_path)
        return self._graph_store

    @property
    def vector_store(self) -> ChromaVectorStore:
        if self._vector_store is None:
            settings = get_settings()
            self._vector_store = ChromaVectorStore(settings.vector_db_path)
        return self._vector_store

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_names(self) -> List[str]:
        """获取所有工具名"""
        return list(self._tools.keys())

    def get_tools_description(self) -> str:
        """获取工具描述"""
        lines = ["## 可用工具\n"]
        for tool in self._tools.values():
            lines.append(f"### {tool.name}")
            lines.append(f"{tool.description}\n")
        return "\n".join(lines)


# 全局工具注册器
tool_registry = ToolRegistry()


def register_tool(
        name: str,
        description: str,
        args_schema: Optional[Type[BaseModel]] = None
):
    """工具注册装饰器"""

    def decorator(func: Callable):
        tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            args_schema=args_schema
        )
        tool_registry.register(tool)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._tool = tool
        return wrapper

    return decorator


