# core/graph.py (续)
"""
LangGraph 工作流定义
"""
import sys
from typing import Literal, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

from config import get_settings
from tools import tool_registry
from agent.prompts import SYSTEM_PROMPT
from .state import AgentState


class KnowledgeAgentGraph:
    """知识图谱 Agent 工作流"""

    def __init__(self):
        self.settings = get_settings()
        self.tools = tool_registry.get_all()
        self.llm = self._create_llm()
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _create_llm(self) -> Runnable:
        """创建 LLM 实例"""
        llm = ChatOpenAI(
            model=self.settings.chat_model,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
            streaming=True,
        )
        return llm.bind_tools(self.tools)

    def _build_graph(self) -> CompiledStateGraph:
        """构建工作流图"""
        workflow = StateGraph(AgentState)

        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)

        workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )

        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=self.memory)

    def _agent_node(self, state: AgentState) -> Dict[str, Any]:
        """Agent 决策节点"""
        messages = list(state["messages"])

        if not any(isinstance(m, SystemMessage) for m in messages):
            messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

        iteration = state.get("iteration", 0) + 1
        if iteration > self.settings.max_iterations:
            return {
                "messages": [AIMessage(content="⚠️ 达到最大迭代次数，请简化问题重试")],
                "is_finished": True,
                "final_answer": "达到最大迭代次数",
                "iteration": iteration
            }

        response = self.llm.invoke(messages)

        return {
            "messages": [response],
            "iteration": iteration,
            "is_finished": not response.tool_calls,
            "final_answer": response.content if not response.tool_calls else None
        }

    def _tool_node(self, state: AgentState) -> Dict[str, Any]:
        """工具执行节点"""
        messages = state["messages"]
        last_message = messages[-1]

        tool_results = []
        tool_messages = []

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                tool = tool_registry.get(tool_name)
                if tool:
                    try:
                        result = tool.invoke(tool_args)
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result
                        })
                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"]
                            )
                        )
                    except Exception as e:
                        error_msg = f"❌ 工具执行错误: {str(e)}"
                        tool_results.append({
                            "tool": tool_name,
                            "args": tool_args,
                            "error": str(e)
                        })
                        tool_messages.append(
                            ToolMessage(
                                content=error_msg,
                                tool_call_id=tool_call["id"]
                            )
                        )
                else:
                    error_msg = f"❌ 未知工具: {tool_name}"
                    tool_messages.append(
                        ToolMessage(
                            content=error_msg,
                            tool_call_id=tool_call["id"]
                        )
                    )

        return {
            "messages": tool_messages,
            "tool_results": tool_results
        }

    def _should_continue(self, state: AgentState) -> Literal["continue", "end"]:
        """判断是否继续执行"""
        messages = state["messages"]
        last_message = messages[-1]

        if state.get("is_finished", False):
            return "end"

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"

        return "end"

    def invoke(self, user_input: str, thread_id: str = "default") -> str:
        """执行对话"""
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "iteration": 0,
            "tool_results": [],
            "is_finished": False,
            "final_answer": None,
            "context": {}
        }

        result = self.graph.invoke(initial_state, config)

        # 提取最终回复
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return result.get("final_answer", "处理完成")

    async def ainvoke(self, user_input: str, thread_id: str = "default") -> str:
        """异步执行对话"""
        config = {"configurable": {"thread_id": thread_id}}

        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "iteration": 0,
            "tool_results": [],
            "is_finished": False,
            "final_answer": None,
            "context": {}
        }

        result = await self.graph.ainvoke(initial_state, config)

        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return result.get("final_answer", "处理完成")

    def chat_stream(self, user_input: str, thread_id: str = "default"):
        """真正的流式执行"""
        # 1. 构建包含历史记录的完整消息列表
        config = {"configurable": {"thread_id": thread_id}}
        
        # 2. 获取历史记录
        # 注意：这里简化处理，实际应该从checkpointer中获取完整历史
        # 为了演示，我们直接使用当前设计
        
        # 3. 创建初始状态
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "iteration": 0,
            "tool_results": [],
            "is_finished": False,
            "final_answer": None,
            "context": {}
        }
        
        # 4. 使用LangGraph的stream方法执行工作流
        for event in self.graph.stream(initial_state, config):
            # 5. 处理每个事件，提取并返回LLM的流式输出
            if "agent" in event:
                agent_state = event["agent"]
                messages = agent_state.get("messages", [])
                if messages:
                    last_message = messages[-1]
                    # 检查是否是流式输出块
                    if hasattr(last_message, "content"):
                        yield last_message.content

    async def astream_workflow_events(self, user_input: str, thread_id: str = "default"):
        """使用astream_events方法实现流式输出（LangChain v0.2+推荐）"""
        # 1. 构建配置和初始状态
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "iteration": 0,
            "tool_results": [],
            "is_finished": False,
            "final_answer": None,
            "context": {}
        }
        
        # 2. 使用LangGraph的astream_events方法执行工作流
        async for event in self.graph.astream_events(initial_state, config, version="v1"):
            yield event


def create_agent_graph() -> KnowledgeAgentGraph:
    """创建 Agent 图实例"""
    return KnowledgeAgentGraph()
