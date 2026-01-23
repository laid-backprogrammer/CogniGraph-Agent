# agent/react_agent.py
"""
ReAct Agent - 备用手动实现（不依赖 LangGraph）
"""

import re
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI

from config import get_settings
from tools import tool_registry
from .prompts import SYSTEM_PROMPT


class ReActAgent:
    """ReAct 模式的 Agent（手动实现，用于对比或降级）"""

    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url
        )
        self.chat_history: List[Dict[str, str]] = []

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM"""
        response = self.client.chat.completions.create(
            model=self.settings.chat_model,
            messages=messages,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens
        )
        return response.choices[0].message.content

    def _parse_action(self, text: str) -> tuple[Optional[str], Dict[str, Any]]:
        """解析 Action"""
        action_match = re.search(r'Action:\s*(\w+)', text)
        if not action_match:
            return None, {}

        action = action_match.group(1).strip()

        input_match = re.search(r'Action Input:\s*(\{.*?\})', text, re.DOTALL)
        if not input_match:
            simple_match = re.search(r'Action Input:\s*["\']?([^"\'\n]+)["\']?', text)
            if simple_match:
                return action, {"input": simple_match.group(1).strip()}
            return action, {}

        input_str = input_match.group(1).strip()
        input_str = re.sub(r',\s*}', '}', input_str)

        try:
            return action, json.loads(input_str)
        except json.JSONDecodeError:
            return action, {"input": input_str}

    def _execute_tool(self, action: str, action_input: Dict[str, Any]) -> str:
        """执行工具"""
        tool = tool_registry.get(action)
        if not tool:
            available = ", ".join(tool_registry.get_names())
            return f"❌ 未知工具: {action}\n可用工具: {available}"

        try:
            result = tool.invoke(action_input)
            return str(result)
        except Exception as e:
            return f"❌ 执行错误: {str(e)}"

    def chat(self, user_input: str) -> str:
        """ReAct 循环对话"""
        react_prompt = SYSTEM_PROMPT + """

## ReAct 格式（严格遵守）

思考时使用:
Thought: 你的思考过程
Action: 工具名称
Action Input: {"参数名": "参数值"}
Observation: (等待工具返回)

最终回复时:
Thought: 我已经完成了所有操作
Final Answer: 给用户的最终回复
"""

        messages = [
            {"role": "system", "content": react_prompt},
            *self.chat_history[-6:],
            {"role": "user", "content": user_input}
        ]

        scratchpad = ""

        for i in range(self.settings.max_iterations):
            current_messages = messages.copy()
            if scratchpad:
                current_messages.append({
                    "role": "assistant",
                    "content": scratchpad
                })

            response = self._call_llm(current_messages)
            print(f"\n--- 迭代 {i + 1} ---")
            print(response[:500] + ("..." if len(response) > 500 else ""))

            if "Final Answer:" in response:
                final_match = re.search(r'Final Answer:\s*(.*)', response, re.DOTALL)
                if final_match:
                    answer = final_match.group(1).strip()
                    self.chat_history.append({"role": "user", "content": user_input})
                    self.chat_history.append({"role": "assistant", "content": answer})
                    return answer

            action, action_input = self._parse_action(response)

            if action:
                print(f"\n🔧 执行: {action}({json.dumps(action_input, ensure_ascii=False)})")
                observation = self._execute_tool(action, action_input)
                print(f"📋 结果: {observation[:200]}...")
                scratchpad += response + f"\nObservation: {observation}\n\n"
            else:
                if response.strip():
                    self.chat_history.append({"role": "user", "content": user_input})
                    self.chat_history.append({"role": "assistant", "content": response})
                    return response
                scratchpad += response + "\n"

        return "⚠️ 达到最大迭代次数，请简化问题重试"

    def clear_history(self):
        """清空对话历史"""
        self.chat_history.clear()
