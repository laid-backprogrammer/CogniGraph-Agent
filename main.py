# main.py
"""
主入口文件
"""

import argparse
import sys

from config import get_settings
from cli import InteractiveCLI


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="知识图谱学习助手 - LangGraph + MCP 架构"
    )

    parser.add_argument(
        "--mode",
        choices=["cli"],
        default="cli",
        help="运行模式: cli(交互式), mcp(WebSocket服务), mcp-stdio(标准输入输出), api(REST API)"
    )

    parser.add_argument(
        "--agent",
        choices=["langgraph", "react"],
        default="langgraph",
        help="Agent 类型: langgraph(推荐) 或 react(手动实现)"
    )
    args = parser.parse_args()

    if args.mode == "cli":
        # 交互式 CLI
        cli = InteractiveCLI(use_langgraph=(args.agent == "langgraph"))
        cli.run()

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
