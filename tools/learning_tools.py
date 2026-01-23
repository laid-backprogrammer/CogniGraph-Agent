# tools/learning_tools.py
"""
学习进度工具
"""

from typing import Optional
from pydantic import BaseModel, Field

from .base import tool_registry, register_tool
from storage.base import KnowledgeNode, Problem


class UpdateProficiencyInput(BaseModel):
    """更新熟练度输入"""
    node_id: str = Field(description="知识点ID")
    score: float = Field(ge=0, le=1, description="熟练度分数 0-1")


@register_tool(
    name="update_proficiency",
    description="更新知识点熟练度。0-0.3=未掌握, 0.3-0.7=学习中, 0.7-1=已掌握",
    args_schema=UpdateProficiencyInput
)
def update_proficiency(node_id: str, score: float) -> str:
    """更新熟练度"""
    try:
        graph_store = tool_registry.graph_store

        # 查找节点
        actual_id = graph_store.find_by_alias(node_id) or node_id
        node = graph_store.get_node(actual_id)

        if not node:
            return f"❓ 未找到: {node_id}"

        # 更新熟练度
        score = max(0.0, min(1.0, float(score)))
        node.proficiency = score
        graph_store.update_node(node)

        status = "🔴未掌握" if score < 0.3 else "🟡学习中" if score < 0.7 else "🟢已掌握"
        return f"✅ 更新【{actual_id}】熟练度: {score:.0%} ({status})"
    except Exception as e:
        return f"❌ 更新失败: {str(e)}"


class AddProblemInput(BaseModel):
    """添加题目输入"""
    content: str = Field(description="题目内容")
    knowledge_points: str = Field(description="关联的知识点，逗号分隔")


@register_tool(
    name="add_problem",
    description="记录题目并关联知识点",
    args_schema=AddProblemInput
)
def add_problem(content: str, knowledge_points: str) -> str:
    """记录题目"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        kp_list = [k.strip() for k in knowledge_points.split(",") if k.strip()]
        results = []
        linked_nodes = []

        for kp in kp_list:
            # 查找或创建节点
            node_id = graph_store.find_by_alias(kp)
            if not node_id:
                search_results = vector_store.search(kp, top_k=1)
                if search_results and search_results[0]['similarity'] >= 0.8:
                    node_id = search_results[0]['id']
                else:
                    # 创建新节点
                    node = KnowledgeNode(id=kp, proficiency=0.0)
                    node_id = graph_store.add_node(node)
                    vector_store.add(node_id, kp, {"name": node_id})
                    results.append(f"  📌 新增知识点: {node_id}")
                    linked_nodes.append(node_id)
                    continue

            results.append(f"  🔗 关联已有: {node_id}")
            linked_nodes.append(node_id)

        # 保存题目
        problem = Problem(
            content=content[:500],
            linked_nodes=linked_nodes,
            difficulty=1
        )
        graph_store.add_problem(problem)

        return f"📝 题目已记录，关联知识点:\n" + "\n".join(results)
    except Exception as e:
        return f"❌ 记录失败: {str(e)}"


class GetUnlearnedInput(BaseModel):
    """获取未学习前置输入"""
    target_node: str = Field(description="目标知识点")
    threshold: float = Field(default=0.7, description="熟练度阈值")


@register_tool(
    name="get_unlearned_prerequisites",
    description="获取学习某知识点需要但尚未掌握的前置知识",
    args_schema=GetUnlearnedInput
)
def get_unlearned_prerequisites(target_node: str, threshold: float = 0.7) -> str:
    """获取未学习的前置知识"""
    try:
        graph_store = tool_registry.graph_store
        vector_store = tool_registry.vector_store

        # 查找节点
        node_id = graph_store.find_by_alias(target_node)
        if not node_id:
            results = vector_store.search(target_node, top_k=1)
            if results and results[0]['similarity'] >= 0.6:
                node_id = results[0]['id']
            else:
                return f"❓ 未找到: {target_node}"

        # 获取学习路径并筛选未掌握的
        path = graph_store.get_learning_path(node_id)
        unlearned = []

        for step in path:
            node = graph_store.get_node(step)
            if node and node.proficiency < threshold:
                unlearned.append({
                    "id": step,
                    "proficiency": node.proficiency,
                    "difficulty": node.difficulty
                })

        if not unlearned:
            return f"🎉 学习【{node_id}】所需的所有前置知识都已掌握！"

        lines = [f"📋 学习【{node_id}】需要先掌握的知识点:"]
        for item in unlearned:
            status = "🔴" if item['proficiency'] < 0.3 else "🟡"
            lines.append(
                f"  {status} {item['id']} (当前: {item['proficiency']:.0%}, 难度: {'⭐' * item['difficulty']})"
            )

        lines.append(f"\n📍 建议学习顺序: {' → '.join([u['id'] for u in unlearned])}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"
