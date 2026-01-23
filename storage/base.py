# storage/base.py
"""
存储抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class KnowledgeNode:
    """知识点节点"""
    id: str
    description: str = ""
    difficulty: int = 1
    proficiency: float = 0.0
    aliases: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "difficulty": self.difficulty,
            "proficiency": self.proficiency,
            "aliases": self.aliases,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeNode":
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            difficulty=data.get("difficulty", 1),
            proficiency=data.get("proficiency", 0.0),
            aliases=data.get("aliases", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class KnowledgeEdge:
    """知识点依赖边"""
    source: str  # 前置知识
    target: str  # 目标知识
    weight: float = 1.0
    relation_type: str = "prerequisite"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Problem:
    """题目记录"""
    id: Optional[int] = None
    content: str = ""
    linked_nodes: List[str] = field(default_factory=list)
    difficulty: int = 1
    created_at: datetime = field(default_factory=datetime.now)


class BaseGraphStorage(ABC):
    """图存储抽象基类"""

    @abstractmethod
    def add_node(self, node: KnowledgeNode) -> str:
        """添加节点"""
        pass

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        pass

    @abstractmethod
    def update_node(self, node: KnowledgeNode) -> bool:
        """更新节点"""
        pass

    @abstractmethod
    def delete_node(self, node_id: str) -> bool:
        """删除节点"""
        pass

    @abstractmethod
    def add_edge(self, edge: KnowledgeEdge) -> bool:
        """添加边"""
        pass

    @abstractmethod
    def get_prerequisites(self, node_id: str) -> List[str]:
        """获取前置知识"""
        pass

    @abstractmethod
    def get_dependents(self, node_id: str) -> List[str]:
        """获取后续知识"""
        pass

    @abstractmethod
    def get_all_nodes(self) -> List[KnowledgeNode]:
        """获取所有节点"""
        pass

    @abstractmethod
    def get_all_edges(self) -> List[KnowledgeEdge]:
        """获取所有边"""
        pass


class BaseVectorStorage(ABC):
    """向量存储抽象基类"""

    @abstractmethod
    def add(self, id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """添加向量"""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """删除向量"""
        pass
