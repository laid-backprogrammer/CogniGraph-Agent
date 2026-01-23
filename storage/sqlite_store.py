# storage/sqlite_store.py
"""
SQLite 图存储实现
"""

import sqlite3
import json
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import networkx as nx

from .base import (
    BaseGraphStorage,
    KnowledgeNode,
    KnowledgeEdge,
    Problem
)


class SQLiteGraphStore(BaseGraphStorage):
    """SQLite 图存储"""

    def __init__(self, db_path: str = "knowledge.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库"""
        with self._get_conn() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    description TEXT DEFAULT '',
                    difficulty INTEGER DEFAULT 1,
                    proficiency REAL DEFAULT 0.0,
                    aliases TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    relation_type TEXT DEFAULT 'prerequisite',
                    metadata TEXT DEFAULT '{}',
                    PRIMARY KEY (source, target),
                    FOREIGN KEY (source) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (target) REFERENCES nodes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    linked_nodes TEXT DEFAULT '[]',
                    difficulty INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
            ''')

    def add_node(self, node: KnowledgeNode) -> str:
        """添加或更新节点"""
        with self._get_conn() as conn:
            conn.execute('''
                INSERT INTO nodes (id, description, difficulty, proficiency, aliases, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    description = excluded.description,
                    difficulty = excluded.difficulty,
                    proficiency = excluded.proficiency,
                    aliases = excluded.aliases,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                node.id,
                node.description,
                node.difficulty,
                node.proficiency,
                json.dumps(node.aliases, ensure_ascii=False),
                json.dumps(node.metadata, ensure_ascii=False)
            ))
        return node.id

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """获取节点"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (node_id,)
            ).fetchone()

            if row:
                return KnowledgeNode(
                    id=row["id"],
                    description=row["description"],
                    difficulty=row["difficulty"],
                    proficiency=row["proficiency"],
                    aliases=json.loads(row["aliases"]),
                    metadata=json.loads(row["metadata"])
                )
        return None

    def update_node(self, node: KnowledgeNode) -> bool:
        """更新节点"""
        with self._get_conn() as conn:
            cursor = conn.execute('''
                UPDATE nodes SET
                    description = ?,
                    difficulty = ?,
                    proficiency = ?,
                    aliases = ?,
                    metadata = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                node.description,
                node.difficulty,
                node.proficiency,
                json.dumps(node.aliases, ensure_ascii=False),
                json.dumps(node.metadata, ensure_ascii=False),
                node.id
            ))
            return cursor.rowcount > 0

    def delete_node(self, node_id: str) -> bool:
        """删除节点及相关边"""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM edges WHERE source = ? OR target = ?",
                         (node_id, node_id))
            cursor = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            return cursor.rowcount > 0

    def add_edge(self, edge: KnowledgeEdge) -> bool:
        """添加边"""
        with self._get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO edges (source, target, weight, relation_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                edge.source,
                edge.target,
                edge.weight,
                edge.relation_type,
                json.dumps(edge.metadata, ensure_ascii=False)
            ))
        return True

    def get_prerequisites(self, node_id: str) -> List[str]:
        """获取前置知识"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT source FROM edges WHERE target = ?", (node_id,)
            ).fetchall()
            return [row["source"] for row in rows]

    def get_dependents(self, node_id: str) -> List[str]:
        """获取后续知识"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT target FROM edges WHERE source = ?", (node_id,)
            ).fetchall()
            return [row["target"] for row in rows]

    def get_all_nodes(self) -> List[KnowledgeNode]:
        """获取所有节点"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM nodes ORDER BY id").fetchall()
            return [
                KnowledgeNode(
                    id=row["id"],
                    description=row["description"],
                    difficulty=row["difficulty"],
                    proficiency=row["proficiency"],
                    aliases=json.loads(row["aliases"]),
                    metadata=json.loads(row["metadata"])
                )
                for row in rows
            ]

    def get_all_edges(self) -> List[KnowledgeEdge]:
        """获取所有边"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
            return [
                KnowledgeEdge(
                    source=row["source"],
                    target=row["target"],
                    weight=row["weight"],
                    relation_type=row["relation_type"],
                    metadata=json.loads(row["metadata"])
                )
                for row in rows
            ]

    def node_exists(self, node_id: str) -> bool:
        """检查节点是否存在"""
        return self.get_node(node_id) is not None

    def find_by_alias(self, alias: str) -> Optional[str]:
        """通过别名查找节点"""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT id, aliases FROM nodes").fetchall()
            for row in rows:
                if row["id"].lower() == alias.lower():
                    return row["id"]
                aliases = json.loads(row["aliases"])
                if any(a.lower() == alias.lower() for a in aliases):
                    return row["id"]
        return None

    def get_learning_path(self, target_node: str) -> List[str]:
        """获取学习路径（拓扑排序）"""
        G = nx.DiGraph()
        for edge in self.get_all_edges():
            G.add_edge(edge.source, edge.target, weight=edge.weight)

        if target_node not in G:
            return [target_node]

        ancestors = nx.ancestors(G, target_node)
        sub_nodes = list(ancestors) + [target_node]
        sub_G = G.subgraph(sub_nodes)

        try:
            return list(nx.topological_sort(sub_G))
        except nx.NetworkXUnfeasible:
            return list(ancestors) + [target_node]

    # 题目管理
    def add_problem(self, problem: Problem) -> int:
        """添加题目"""
        with self._get_conn() as conn:
            cursor = conn.execute('''
                INSERT INTO problems (content, linked_nodes, difficulty)
                VALUES (?, ?, ?)
            ''', (
                problem.content,
                json.dumps(problem.linked_nodes, ensure_ascii=False),
                problem.difficulty
            ))
            return cursor.lastrowid

    def get_problems_by_node(self, node_id: str) -> List[Problem]:
        """获取节点相关的题目"""
        with self._get_conn() as conn:
            rows = conn.execute('''
                SELECT * FROM problems 
                WHERE linked_nodes LIKE ?
            ''', (f'%"{node_id}"%',)).fetchall()

            return [
                Problem(
                    id=row["id"],
                    content=row["content"],
                    linked_nodes=json.loads(row["linked_nodes"]),
                    difficulty=row["difficulty"]
                )
                for row in rows
            ]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_conn() as conn:
            node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            problem_count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]

            # 熟练度分布
            rows = conn.execute("SELECT proficiency FROM nodes").fetchall()
            dist = {"未学习": 0, "学习中": 0, "已掌握": 0}
            for row in rows:
                prof = row[0]
                if prof < 0.3:
                    dist["未学习"] += 1
                elif prof < 0.7:
                    dist["学习中"] += 1
                else:
                    dist["已掌握"] += 1

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "problem_count": problem_count,
            "proficiency_distribution": dist
        }

    def export_to_json(self, filepath: str):
        """导出到 JSON"""
        data = {
            "nodes": [n.to_dict() for n in self.get_all_nodes()],
            "edges": [
                {"source": e.source, "target": e.target, "weight": e.weight}
                for e in self.get_all_edges()
            ],
            "statistics": self.get_statistics()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
