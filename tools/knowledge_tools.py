# tools/knowledge_tools.py (续)
"""
知识点管理工具
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .base import tool_registry, register_tool
from storage.base import KnowledgeNode


class AddKnowledgeNodeInput(BaseModel):
    """添加知识点输入"""
    node_id: str = Field(description="知识点名称/ID")
    description: str = Field(default="", description="知识点描述")
    difficulty: int = Field(default=1, ge=1, le=5, description="难度等级 1-5")
    aliases: str = Field(default="", description="别名，逗号分隔")


@register_tool(
    name="add_knowledge_node",
    description="添加新知识点到图谱。difficulty: 1=入门 5=困难。aliases: 逗号分隔的别名",
    args_schema=AddKnowledgeNodeInput
)
def add_knowledge_node(
        node_id: str,
        description: str = "",
        difficulty: int = 1,
        aliases: str = ""
) -> str:
    """添加知识点节点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 处理别名
        alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases else []

        # 处理 "A/B" 格式
        if "/" in node_id:
            parts = node_id.split("/")
            real_id = parts[0].strip()
            for p in parts[1:]:
                if p.strip():
                    alias_list.append(p.strip())
            node_id = real_id

        # 创建节点
        node = KnowledgeNode(
            id=node_id,
            description=description,
            difficulty=difficulty,
            proficiency=0.0,
            aliases=list(set(alias_list))
        )

        # 存储到图数据库
        actual_id = graph_store.add_node(node)

        # 同步到向量库
        search_text = f"{node_id} {description} {' '.join(alias_list)}".strip()
        vector_store.add(
            id=node_id,
            text=search_text,
            metadata={
                "name": node_id,
                "description": description,
                "aliases": ",".join(alias_list)
            }
        )

        return f"✅ 成功添加知识点: {actual_id} (难度={difficulty})"
    except Exception as e:
        return f"❌ 添加失败: {str(e)}"


class QueryNodeInput(BaseModel):
    """查询知识点输入"""
    keyword: str = Field(description="要查询的知识点关键词")


@register_tool(
    name="query_node",
    description="查询知识点详情，支持精确匹配和语义搜索",
    args_schema=QueryNodeInput
)
def query_node(keyword: str) -> str:
    """查询知识点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        keyword = keyword.strip()
        if "/" in keyword:
            keyword = keyword.split("/")[0].strip()

        # 1. 精确匹配
        node = graph_store.get_node(keyword)

        # 2. 别名匹配
        if not node:
            found_id = graph_store.find_by_alias(keyword)
            if found_id:
                node = graph_store.get_node(found_id)
                keyword = found_id

        # 3. 语义搜索
        if not node:
            results = vector_store.search(keyword, top_k=3)
            if results and results[0]['similarity'] >= 0.6:
                keyword = results[0]['id']
                node = graph_store.get_node(keyword)

        if not node:
            # 给出相似建议
            similar = vector_store.search(keyword, top_k=3)
            if similar:
                suggestions = ", ".join([
                    f"{s['id']}({s['similarity']:.0%})" for s in similar
                ])
                return f"❓ 未找到: {keyword}\n💡 相似节点: {suggestions}"
            return f"❓ 未找到知识点: {keyword}"

        # 格式化输出
        prof = node.proficiency
        status = "🔴未学习" if prof < 0.3 else "🟡学习中" if prof < 0.7 else "🟢已掌握"
        prereqs = graph_store.get_prerequisites(keyword)
        prereq_str = f", 前置: {', '.join(prereqs)}" if prereqs else ""

        return (
            f"📚 {keyword}: {status}({prof:.0%}), 难度={node.difficulty}{prereq_str}\n"
            f"   描述: {node.description or '无'}"
        )
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


class SearchSimilarInput(BaseModel):
    """搜索相似知识点输入"""
    keyword: str = Field(description="搜索关键词")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")


@register_tool(
    name="search_similar_nodes",
    description="向量语义搜索相似知识点",
    args_schema=SearchSimilarInput
)
def search_similar_nodes(keyword: str, top_k: int = 5) -> str:
    """搜索相似知识点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        results = vector_store.search(keyword, top_k)
        if not results:
            return f"❓ 没有找到与 '{keyword}' 相似的知识点"

        lines = [f"🔍 与 '{keyword}' 相似的知识点:"]
        for r in results:
            node = graph_store.get_node(r['id'])
            if node:
                prof = node.proficiency
                status = "🟢" if prof >= 0.7 else "🟡" if prof >= 0.3 else "🔴"
                lines.append(
                    f"  {status} {r['id']} (相似度: {r['similarity']:.0%}, 熟练度: {prof:.0%})"
                )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 搜索失败: {str(e)}"


class DeleteNodeInput(BaseModel):
    """删除知识点输入"""
    node_id: str = Field(description="要删除的知识点ID")


@register_tool(
    name="delete_knowledge_node",
    description="删除知识点及其相关依赖",
    args_schema=DeleteNodeInput
)
def delete_knowledge_node(node_id: str) -> str:
    """删除知识点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 查找节点
        actual_id = graph_store.find_by_alias(node_id) or node_id
        node = graph_store.get_node(actual_id)

        if not node:
            return f"❓ 未找到: {node_id}"

        prereqs = graph_store.get_prerequisites(actual_id)
        dependents = graph_store.get_dependents(actual_id)

        # 删除
        graph_store.delete_node(actual_id)
        vector_store.delete(actual_id)

        info = [f"✅ 已删除知识点: {actual_id}"]
        if prereqs:
            info.append(f"   移除了 {len(prereqs)} 个前置依赖")
        if dependents:
            info.append(f"   移除了 {len(dependents)} 个后续依赖")

        return "\n".join(info)
    except Exception as e:
        return f"❌ 删除失败: {str(e)}"


class ListNodesInput(BaseModel):
    """列出知识点输入"""
    dummy: str = Field(default="", description="占位参数，可忽略")


@register_tool(
    name="list_all_nodes",
    description="列出所有知识点及其学习状态",
    args_schema=ListNodesInput
)
def list_all_nodes(dummy: str = "") -> str:
    """列出所有知识点"""
    try:
        graph_store = tool_registry.graph_store
        nodes = graph_store.get_all_nodes()

        if not nodes:
            return "📭 知识图谱为空，请先添加知识点"

        lines = ["📚 当前所有知识点:", "-" * 40]

        # 按熟练度分组
        mastered, learning, unlearned = [], [], []

        for node in nodes:
            prof = node.proficiency
            diff = node.difficulty
            desc = node.description[:20] if node.description else ""

            info = f"{node.id} ({prof:.0%}) {'⭐' * diff}"
            if desc:
                info += f" - {desc}"

            if prof >= 0.7:
                mastered.append(info)
            elif prof >= 0.3:
                learning.append(info)
            else:
                unlearned.append(info)

        if mastered:
            lines.append(f"\n🟢 已掌握 ({len(mastered)}):")
            for item in mastered:
                lines.append(f"  ✓ {item}")

        if learning:
            lines.append(f"\n🟡 学习中 ({len(learning)}):")
            for item in learning:
                lines.append(f"  ◐ {item}")

        if unlearned:
            lines.append(f"\n🔴 未学习 ({len(unlearned)}):")
            for item in unlearned:
                lines.append(f"  ○ {item}")

        stats = graph_store.get_statistics()
        lines.append(
            f"\n📊 统计: {stats['node_count']}个知识点, "
            f"{stats['edge_count']}条依赖, {stats['problem_count']}道题目"
        )

        return "\n".join(lines)
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"
