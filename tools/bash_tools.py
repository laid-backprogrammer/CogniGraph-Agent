# 在 tools 目录创建 bash_tools.py 文件
from typing import Dict, Any
from pydantic import BaseModel, Field
import subprocess as sp
import os

from .base import tool_registry, register_tool


class BashInput(BaseModel):
    """Bash 命令输入"""
    command: str = Field(description="要执行的 Shell 命令")


@register_tool(
    name="bash",
    description="Shell cmd. Read:cat/grep/find/rg/ls. Write:echo>/sed.失败则尝试用windows的一些方法来读写",
    args_schema=BashInput
)
def bash(command: str) -> str:
    """
    执行 bash 命令的工具函数
    """
    print(f"$ {command}")

    try:
        result = sp.run(command, shell=True, capture_output=True,
                        text=True, timeout=300)
        output = result.stdout + result.stderr or "(empty)"

        # 限制输出长度
        output = output[:50000]

        return output
    except Exception as e:
        return f"执行错误: {str(e)}"
