# tools/graph_tools.py
"""
图谱分析工具
"""

from typing import Optional, List
from pydantic import BaseModel, Field

from .base import tool_registry, register_tool
from storage.base import KnowledgeNode, KnowledgeEdge


class AddDependencyInput(BaseModel):
    """添加依赖输入"""
    prerequisite: str = Field(description="前置知识点")
    target: str = Field(description="目标知识点")
    weight: float = Field(default=1.0, ge=0, le=1, description="依赖权重")


@register_tool(
    name="add_dependency",
    description="添加依赖关系: prerequisite -> target。例如学导数需先学极限: prerequisite='极限', target='导数'",
    args_schema=AddDependencyInput
)
def add_dependency(prerequisite: str, target: str, weight: float = 1.0) -> str:
    """添加依赖关系"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 智能查找或创建节点
        prereq_id = graph_store.find_by_alias(prerequisite)
        if not prereq_id:
            # 尝试向量搜索
            results = vector_store.search(prerequisite, top_k=1)
            if results and results[0]['similarity'] >= 0.8:
                prereq_id = results[0]['id']
            else:
                # 创建新节点
                node = KnowledgeNode(id=prerequisite, proficiency=0.0)
                prereq_id = graph_store.add_node(node)
                vector_store.add(prereq_id, prerequisite, {"name": prereq_id})

        target_id = graph_store.find_by_alias(target)
        if not target_id:
            results = vector_store.search(target, top_k=1)
            if results and results[0]['similarity'] >= 0.8:
                target_id = results[0]['id']
            else:
                node = KnowledgeNode(id=target, proficiency=0.0)
                target_id = graph_store.add_node(node)
                vector_store.add(target_id, target, {"name": target_id})

        # 添加边
        edge = KnowledgeEdge(
            source=prereq_id,
            target=target_id,
            weight=weight
        )
        graph_store.add_edge(edge)

        return f"✅ 添加依赖: 【{prereq_id}】→【{target_id}】"
    except Exception as e:
        return f"❌ 添加边失败: {str(e)}"


class GetLearningPathInput(BaseModel):
    """获取学习路径输入"""
    target_node: str = Field(description="目标知识点")


@register_tool(
    name="get_learning_path",
    description="获取学习某知识点的完整路径，包含所有前置知识",
    args_schema=GetLearningPathInput
)
def get_learning_path(target_node: str) -> str:
    """获取学习路径"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 查找节点
        node_id = graph_store.find_by_alias(target_node)
        if not node_id:
            results = vector_store.search(target_node, top_k=3)
            if results and results[0]['similarity'] >= 0.6:
                node_id = results[0]['id']
            else:
                if results:
                    suggestions = ", ".join([r['id'] for r in results])
                    return f"❓ 未找到: {target_node}\n💡 您是否想找: {suggestions}"
                return f"❓ 未找到: {target_node}，请先添加"

        # 获取学习路径
        path = graph_store.get_learning_path(node_id)

        if len(path) <= 1:
            return f"📍 【{node_id}】无前置依赖，可直接学习"

        lines = [f"📊 学习【{node_id}】的路径:"]
        unlearned = []

        for i, step in enumerate(path, 1):
            node = graph_store.get_node(step)
            if node:
                prof = node.proficiency
                status = "🟢" if prof >= 0.7 else "🟡" if prof >= 0.3 else "🔴"
                if prof < 0.7:
                    unlearned.append(step)
                lines.append(f"  {i}. {status} {step} ({prof:.0%})")
            else:
                lines.append(f"  {i}. ❓ {step} (未找到)")
                unlearned.append(step)

        if unlearned:
            lines.append(f"\n⚠️ 需要先学: {' → '.join(unlearned)}")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ 失败: {str(e)}"


class GetGraphStructureInput(BaseModel):
    """获取图谱结构输入"""
    dummy: str = Field(default="", description="占位参数")


@register_tool(
    name="get_graph_structure",
    description="查看知识图谱的整体结构，包括根节点和叶子节点",
    args_schema=GetGraphStructureInput
)
def get_graph_structure(dummy: str = "") -> str:
    """获取图谱结构"""
    try:
        graph_store = tool_registry.graph_store

        nodes = graph_store.get_all_nodes()
        edges = graph_store.get_all_edges()

        if not nodes:
            return "📭 图谱为空"

        lines = ["🗺️ 知识图谱结构:", "=" * 40]

        # 构建关系映射
        prereq_map = {}  # target -> [prerequisites]
        depend_map = {}  # source -> [dependents]

        for edge in edges:
            prereq_map.setdefault(edge.target, []).append(edge.source)
            depend_map.setdefault(edge.source, []).append(edge.target)

        # 找出根节点和叶子节点
        all_ids = {n.id for n in nodes}
        roots = [nid for nid in all_ids if nid not in prereq_map]
        leaves = [nid for nid in all_ids if nid not in depend_map]

        lines.append(f"\n🌱 基础知识点（无前置）: {', '.join(roots) if roots else '无'}")
        lines.append(f"🎯 目标知识点（无后续）: {', '.join(leaves) if leaves else '无'}")

        if edges:
            lines.append("\n📐 依赖关系:")
            for edge in edges:
                lines.append(f"  {edge.source} → {edge.target}")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ 获取结构失败: {str(e)}"


class DeleteNodeInput(BaseModel):
    """删除节点输入"""
    node_id: str = Field(description="要删除的节点ID或别名")


@register_tool(
    name="delete_node",
    description="删除指定的知识节点，同时会删除相关的依赖关系和向量数据",
    args_schema=DeleteNodeInput
)
def delete_node(node_id: str) -> str:
    """删除节点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 智能查找节点
        actual_id = graph_store.find_by_alias(node_id)
        if not actual_id:
            return f"❌ 未找到节点: {node_id}"

        # 删除向量
        vector_store.delete(actual_id)
        
        # 删除节点（会级联删除相关边）
        graph_store.delete_node(actual_id)
        
        return f"✅ 成功删除节点: {actual_id}"
    except Exception as e:
        return f"❌ 删除节点失败: {str(e)}"


class MergeNodesInput(BaseModel):
    """合并节点输入"""
    source_node: str = Field(description="源节点ID或别名，将被合并到目标节点")
    target_node: str = Field(description="目标节点ID或别名，合并后保留")


@register_tool(
    name="merge_nodes",
    description="合并两个节点，将源节点的所有关系和属性合并到目标节点",
    args_schema=MergeNodesInput
)
def merge_nodes(source_node: str, target_node: str) -> str:
    """合并节点"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 智能查找节点
        source_id = graph_store.find_by_alias(source_node)
        target_id = graph_store.find_by_alias(target_node)
        
        if not source_id:
            return f"❌ 未找到源节点: {source_node}"
        if not target_id:
            return f"❌ 未找到目标节点: {target_node}"
        if source_id == target_id:
            return f"❌ 源节点和目标节点相同，无需合并"

        # 获取所有边
        all_edges = graph_store.get_all_edges()
        
        # 处理边：将所有指向源节点的边改为指向目标节点，将所有从源节点出发的边改为从目标节点出发
        for edge in all_edges:
            if edge.source == source_id and edge.target == target_id:
                # 删除自环边
                continue
            if edge.source == source_id:
                # 源节点 → 其他节点 → 目标节点 → 其他节点
                new_edge = KnowledgeEdge(
                    source=target_id,
                    target=edge.target,
                    weight=edge.weight,
                    relation_type=edge.relation_type,
                    metadata=edge.metadata
                )
                graph_store.add_edge(new_edge)
            elif edge.target == source_id:
                # 其他节点 → 源节点 → 其他节点 → 目标节点
                new_edge = KnowledgeEdge(
                    source=edge.source,
                    target=target_id,
                    weight=edge.weight,
                    relation_type=edge.relation_type,
                    metadata=edge.metadata
                )
                graph_store.add_edge(new_edge)
        
        # 获取源节点和目标节点的属性
        source_node_obj = graph_store.get_node(source_id)
        target_node_obj = graph_store.get_node(target_id)
        
        # 合并属性（保留目标节点的主要属性，合并源节点的别名和元数据）
        if source_node_obj and target_node_obj:
            # 合并别名
            merged_aliases = list(set(target_node_obj.aliases + source_node_obj.aliases + [source_id]))
            # 合并元数据
            merged_metadata = target_node_obj.metadata.copy()
            merged_metadata.update(source_node_obj.metadata)
            
            # 更新目标节点
            target_node_obj.aliases = merged_aliases
            target_node_obj.metadata = merged_metadata
            graph_store.update_node(target_node_obj)
        
        # 删除向量
        vector_store.delete(source_id)
        
        # 删除源节点（会级联删除相关边）
        graph_store.delete_node(source_id)
        
        return f"✅ 成功合并节点: {source_id} → {target_id}"
    except Exception as e:
        return f"❌ 合并节点失败: {str(e)}"


class InitDatabaseInput(BaseModel):
    """初始化数据库输入"""
    confirm: bool = Field(description="确认是否要清空数据库，只能输入true")


@register_tool(
    name="init_database",
    description="清空整个数据库，包括所有节点、边和向量数据，谨慎使用！",
    args_schema=InitDatabaseInput
)
def init_database(confirm: bool) -> str:
    """清空数据库初始化"""
    try:
        if not confirm:
            return "❌ 必须确认要清空数据库，将confirm设置为true"
        
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store
        
        # 获取所有节点
        nodes = graph_store.get_all_nodes()
        
        # 删除所有向量和节点
        for node in nodes:
            vector_store.delete(node.id)
            graph_store.delete_node(node.id)
        
        return "✅ 数据库已成功清空初始化"
    except Exception as e:
        return f"❌ 初始化数据库失败: {str(e)}"
