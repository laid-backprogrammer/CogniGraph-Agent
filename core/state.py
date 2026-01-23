# core/state.py
"""
LangGraph 状态定义
"""

from typing import TypedDict, Annotated, Sequence, List, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Agent 状态"""
    # 消息历史（自动累积）
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 当前迭代次数
    iteration: int

    # 最近的工具调用结果
    tool_results: List[dict]

    # 是否已完成
    is_finished: bool

    # 最终答案
    final_answer: Optional[str]

    # 额外上下文
    context: dict
