# agents/05_logging_agent.py
"""
05. LoggingAgent - 로깅 및 터미널 출력 에이전트

통일된 로깅과 아름다운 터미널 출력을 제공합니다.

역할:
- 에이전트별 로그 포맷팅
- 진행 상태 표시
- 결과 요약 출력 (Rich UI)
- 에러 메시지 강조
- 작업 히스토리 표시
"""

from typing import Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.tree import Tree
from rich.live import Live
from .base import BaseAgent


class LoggingAgent(BaseAgent):
    """
    통일된 로깅 및 터미널 출력 에이전트

    작업:
    1. 에이전트별 로그 포맷팅
    2. 진행 상태 표시
    3. 결과 요약 출력
    4. 에러 메시지 강조
    """

    def __init__(self):
        super().__init__(
            name="LoggingAgent",
            description="Unified logging and terminal output formatting",
        )
        self.console = Console()
        self.logs: List[Dict[str, Any]] = []

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 실행

        Expected task actions:
            - log: 일반 로그
            - log_step: 단계 로그 (에이전트 작업)
            - log_result: 최종 결과 출력
            - log_error: 에러 출력
            - show_progress: 진행률 표시
        """
        action = task.get("action")
        data = task.get("data", {})

        try:
            if action == "log":
                self._log_message(data.get("message", ""), data.get("level", "info"))

            elif action == "log_step":
                self._log_agent_step(
                    data.get("agent_name", "Unknown"),
                    data.get("step", ""),
                    data.get("status", "running"),
                )

            elif action == "log_result":
                self._log_final_result(data.get("result", {}))

            elif action == "log_error":
                self._log_error(
                    data.get("error", "Unknown error"), data.get("agent_name", "System")
                )

            elif action == "show_summary":
                self._show_task_summary(data.get("tasks", []))

            return {"success": True, "agent": self.name}

        except Exception as e:
            return {"success": False, "error": str(e), "agent": self.name}

    def _log_message(self, message: str, level: str = "info"):
        """일반 로그 메시지 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        styles = {
            "info": ("ℹ️", "cyan"),
            "success": ("✅", "green"),
            "error": ("❌", "red"),
            "warning": ("⚠️", "yellow"),
            "debug": ("🔍", "dim"),
        }

        icon, style = styles.get(level, ("•", "white"))

        self.console.print(f"[{timestamp}] {icon} {message}", style=style)

        # 로그 저장
        self.logs.append({"timestamp": timestamp, "level": level, "message": message})

    def _log_agent_step(self, agent_name: str, step: str, status: str = "running"):
        """에이전트 단계 로그"""
        status_icons = {
            "running": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "pending": "⏳",
        }

        icon = status_icons.get(status, "•")

        self.console.print(
            f"  {icon} [{agent_name}] {step}",
            style="bold" if status == "running" else "",
        )

    def _log_final_result(self, result: Dict[str, Any]):
        """최종 결과를 패널로 출력"""
        if result.get("success", False):
            data = result.get("data", {})

            content = f"""[bold green]✅ Task Completed Successfully![/bold green]

[bold]Article Details:[/bold]
  • Title: {data.get('title', 'N/A')}
  • Category: {data.get('category', 'N/A')}
  • Article ID: {data.get('article_id', 'N/A')}
  • Slug: {data.get('slug', 'N/A')}
  • Images: {data.get('image_count', 0)}

[bold]Published URL:[/bold]
  {data.get('published_url', 'N/A')}
"""

            self.console.print(
                Panel(
                    content,
                    title="📝 Blog Post Published",
                    border_style="green",
                    padding=(1, 2),
                )
            )
        else:
            error = result.get("error", "Unknown error")
            self.console.print(
                Panel(
                    f"[bold red]❌ Task Failed[/bold red]\n\n{error}",
                    title="Error",
                    border_style="red",
                    padding=(1, 2),
                )
            )

    def _log_error(self, error: str, agent_name: str = "System"):
        """에러 메시지 출력"""
        self.console.print(
            Panel(
                f"[bold red]Error in {agent_name}:[/bold red]\n\n{error}",
                border_style="red",
                padding=(1, 2),
            )
        )

    def _show_task_summary(self, tasks: List[Dict[str, Any]]):
        """작업 목록을 테이블로 표시"""
        if not tasks:
            self.console.print("[yellow]No tasks to display[/yellow]")
            return

        table = Table(title="📋 Task Summary", show_header=True)
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Agent", style="blue", width=20)
        table.add_column("Action", style="white", width=20)
        table.add_column("Status", width=12)
        table.add_column("Duration", style="dim", width=10)

        for task in tasks:
            status = task.get("status", "unknown")
            status_style = {
                "completed": "[green]✅ Done[/green]",
                "failed": "[red]❌ Failed[/red]",
                "running": "[yellow]⚙️ Running[/yellow]",
                "pending": "[dim]⏳ Pending[/dim]",
            }.get(status, status)

            duration = task.get("duration", 0)
            duration_str = f"{duration:.2f}s" if duration else "-"

            table.add_row(
                task.get("task_id", "N/A"),
                task.get("agent_name", "N/A"),
                task.get("action", "N/A"),
                status_style,
                duration_str,
            )

        self.console.print(table)

    def show_agent_tree(self, agents: List[Dict[str, Any]]):
        """에이전트 구조를 트리로 표시"""
        tree = Tree("🤖 [bold]Multi-Agent System[/bold]")

        for agent in agents:
            agent_branch = tree.add(
                f"[cyan]{agent['name']}[/cyan] - {agent.get('status', 'idle')}"
            )
            if agent.get("description"):
                agent_branch.add(f"[dim]{agent['description']}[/dim]")

        self.console.print(tree)

    def show_progress_bar(self, total: int, description: str = "Processing"):
        """진행률 바 표시 (컨텍스트 매니저로 사용)"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console,
        )

    def clear_console(self):
        """콘솔 클리어"""
        self.console.clear()

    def print_banner(self, title: str, subtitle: str = ""):
        """배너 출력"""
        banner = f"""[bold cyan]{title}[/bold cyan]"""
        if subtitle:
            banner += f"\n[dim]{subtitle}[/dim]"

        self.console.print(Panel(banner, border_style="cyan", padding=(1, 2)))
