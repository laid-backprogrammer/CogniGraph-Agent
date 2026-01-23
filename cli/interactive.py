# cli/interactive.py
"""
交互式命令行界面
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import get_settings
from core import create_agent_graph, KnowledgeAgentGraph
from tools import tool_registry
from agent import ReActAgent


class InteractiveCLI:
    """交互式 CLI"""

    def __init__(self, use_langgraph: bool = True):
        self.console = Console()
        self.settings = get_settings()
        self.use_langgraph = use_langgraph

        if use_langgraph:
            self.agent = create_agent_graph()
        else:
            self.agent = ReActAgent()

        self.thread_id = "cli_session"

    def print_banner(self):
        """打印启动横幅"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║           🎓 知识图谱学习助手 (LangGraph + MCP)              ║
╠══════════════════════════════════════════════════════════════╣
║  功能:                                                       ║
║    • 发送题目 → 分析知识点并构建图谱                         ║
║    • 询问知识点 → 获取学习路径                               ║
║    • 学完后说 '我学会了xxx' → 更新熟练度                     ║                        ║
╠══════════════════════════════════════════════════════════════╣
║  命令:                                                       ║
║    /graph   - 查看所有知识点                                 ║
║    /struct  - 查看图谱结构                                   ║
║    /stats   - 查看统计信息                                   ║
║    /export  - 导出图谱到 JSON                                ║
║    /clear   - 清空对话历史                                   ║
║    /mode    - 切换 Agent 模式 (LangGraph/ReAct)              ║
║    /help    - 显示帮助信息                                   ║
║    /quit    - 退出程序                                       ║
╚══════════════════════════════════════════════════════════════╝
        """
        self.console.print(Panel(banner, style="blue"))

    def handle_command(self, command: str) -> bool | None:
        """处理命令，返回是否继续运行"""
        cmd = command.lower().strip()

        if cmd in ['/quit', '/exit', '/q']:
            self.console.print("👋 再见！", style="yellow")
            return False

        elif cmd == '/graph':
            result = tool_registry.get("list_all_nodes").invoke({"dummy": ""})
            self.console.print(Panel(result, title="📚 知识图谱", border_style="green"))

        elif cmd == '/struct':
            result = tool_registry.get("get_graph_structure").invoke({"dummy": ""})
            self.console.print(Panel(result, title="🗺️ 图谱结构", border_style="blue"))

        elif cmd == '/stats':
            self._show_statistics()

        elif cmd == '/export':
            self._export_graph()

        elif cmd == '/clear':
            if self.use_langgraph:
                self.thread_id = f"cli_session_{id(self)}"
            else:
                self.agent.clear_history()
            self.console.print("✅ 对话历史已清空", style="green")

        elif cmd == '/mode':
            self._toggle_mode()

        
        elif cmd == '/help':
            self._show_help()

        elif cmd.startswith('/'):
            self.console.print(f"❓ 未知命令: {cmd}", style="red")
            self.console.print("输入 /help 查看可用命令")

        else:
            return None  # 不是命令，需要发送给 Agent

        return True

    def _show_statistics(self):
        """显示统计信息"""
        stats = tool_registry.graph_store.get_statistics()

        table = Table(title="📊 知识图谱统计")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="green")

        table.add_row("知识点总数", str(stats['node_count']))
        table.add_row("依赖关系数", str(stats['edge_count']))
        table.add_row("题目记录数", str(stats['problem_count']))
        table.add_row("", "")

        dist = stats['proficiency_distribution']
        table.add_row("🔴 未学习", str(dist['未学习']))
        table.add_row("🟡 学习中", str(dist['学习中']))
        table.add_row("🟢 已掌握", str(dist['已掌握']))

        self.console.print(table)

    def _export_graph(self):
        """导出图谱"""
        filepath = "knowledge_graph_export.json"
        tool_registry.graph_store.export_to_json(filepath)
        self.console.print(f"✅ 已导出到 {filepath}", style="green")

    def _toggle_mode(self):
        """切换 Agent 模式"""
        self.use_langgraph = not self.use_langgraph

        if self.use_langgraph:
            self.agent = create_agent_graph()
            mode_name = "LangGraph"
        else:
            self.agent = ReActAgent()
            mode_name = "ReAct (手动)"

        self.console.print(f"✅ 已切换到 {mode_name} 模式", style="green")


    def _show_help(self):
        """显示帮助"""
        help_text = """
## 使用说明

### 基本对话
直接输入问题或题目，AI 会自动分析并构建知识图谱。

### 示例
- "求解方程 x² - 5x + 6 = 0"
- "什么是导数？"
- "我学会了极限"
- "查看学习微积分的路径"

### 命令
| 命令 | 说明 |
|------|------|
| /graph | 查看所有知识点 |
| /struct | 查看图谱结构 |
| /stats | 查看统计信息 |
| /export | 导出图谱到 JSON |
| /obsidian-sync | 同步到 Obsidian |
| /obsidian-import | 从 Obsidian 导入 |
| /obsidian-export | 导出到 Obsidian 文件夹 |
| /clear | 清空对话 |
| /mode | 切换模式 |
| /help | 显示帮助 |
| /quit | 退出 |
        """
        self.console.print(Markdown(help_text))

    def chat(self, user_input: str) -> str:
        """发送消息给 Agent（非流式）"""
        if self.use_langgraph:
            return self.agent.invoke(user_input, self.thread_id)
        else:
            return self.agent.chat(user_input)

    def stream_chat(self, user_input: str) -> str:
        """发送消息给 Agent（流式）"""
        if self.use_langgraph:
            from rich.live import Live
            
            full_response = []
            current_content = ""
            
            # 创建初始面板
            panel = Panel(Markdown(current_content), title="🤖 助手", border_style="green")
            
            # 使用 Live 上下文管理器处理实时更新
            with Live(panel, console=self.console, refresh_per_second=10) as live:
                # 开始真正的流式输出
                for chunk in self.agent.stream_chat(user_input, self.thread_id):
                    # 累积内容
                    current_content += chunk
                    full_response.append(chunk)
                    # 更新面板内容
                    live.update(Panel(Markdown(current_content), title="🤖 助手", border_style="green"))
            
            self.console.print()  # 确保最后换行
            return "".join(full_response)
        else:
            # ReAct 版本仍使用非流式
            response = self.agent.chat(user_input)
            self.console.print()
            self.console.print(Panel(
                Markdown(response),
                title="🤖 助手",
                border_style="green"
            ))
            return response

    async def run_async(self):
        """异步运行交互式会话"""
        self.print_banner()

        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]👤 你[/bold cyan]")

                if not user_input.strip():
                    continue

                # 检查是否是命令
                if user_input.startswith('/'):
                    result = self.handle_command(user_input)
                    if result is False:
                        break
                    continue

                # 发送给 Agent
                if self.use_langgraph:
                    # LangGraph 模式使用推荐的 astream_events 方法实现流式输出
                    self.console.print()
                    self.console.print("🤖 助手:", style="green")
                    self.console.print("─────────────────────────────────────────────────────────────")
                    
                    # 使用 astream_events 方法获取细粒度的流式事件
                    current_response = ""
                    
                    # 使用异步生成器处理事件
                    async for event in self.agent.astream_workflow_events(user_input, self.thread_id):
                        # 处理不同类型的事件
                        event_type = event.get("event")
                        
                        if event_type == "on_chat_model_stream":
                            # 处理聊天模型的流式输出
                            data = event.get("data", {})
                            chunk = data.get("chunk")
                            
                            if chunk:
                                # 检查chunk是否有content属性
                                content = getattr(chunk, "content", "")
                                if content:
                                    # 实时输出token
                                    self.console.print(content, end="", style="white")
                                    current_response += content
                        
                        elif event_type == "on_tool_start":
                            # 处理工具调用开始事件
                            tool_name = event.get("name", "")
                            self.console.print(f"\n🔧 正在调用工具: {tool_name}", style="yellow")
                        
                        elif event_type == "on_tool_end":
                            # 处理工具调用结束事件
                            tool_name = event.get("name", "")
                            self.console.print(f"\n✅ 工具调用完成: {tool_name}", style="green")
                    
                    self.console.print()
                    self.console.print("─────────────────────────────────────────────────────────────")
                else:
                    # ReAct 模式使用非流式输出
                    with Progress(
                            SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            console=self.console,
                            transient=True
                    ) as progress:
                        progress.add_task("🤔 思考中...", total=None)
                        response = self.chat(user_input)
                    
                    self.console.print()
                    self.console.print(Panel(
                        Markdown(response),
                        title="🤖 助手",
                        border_style="green"
                    ))

            except KeyboardInterrupt:
                self.console.print("\n👋 再见！", style="yellow")
                break
            except Exception as e:
                self.console.print(f"❌ 错误: {e}", style="red")
                import traceback
                traceback.print_exc()
    
    def run(self):
        """运行交互式会话（同步包装器）"""
        import asyncio
        asyncio.run(self.run_async())
