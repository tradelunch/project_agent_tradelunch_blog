# agents/06_project_manager.py
"""
06. ProjectManagerAgent - 전체 워크플로우 오케스트레이션 에이전트

모든 에이전트를 조율하여 전체 작업을 관리합니다.

역할:
- 사용자 명령 분석 (Qwen3 LLM)
- 작업 계획 수립
- 에이전트 선택 및 순서 결정
- 에이전트 간 데이터 전달
- 최종 결과 취합 및 보고

LangGraph를 사용한 상태 기반 워크플로우:
  analyze_command → extract → upload → finalize
"""

import asyncio
from typing import Dict, Any, List, Literal
from typing_extensions import TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from llm_factory import get_shared_llm

from .base import BaseAgent
from .protocol import AgentTask, AgentResponse
from .document_scanner_agent import DocumentScannerAgent
from .extracting_agent import ExtractingAgent
from .uploading_agent import UploadingAgent
from .logging_agent import LoggingAgent


class AgentState(TypedDict):
    """전체 워크플로우 상태"""

    # 입력
    user_command: str
    file_path: str

    # 처리 단계
    current_step: str
    plan: List[str]

    # 데이터
    extracted_data: Dict[str, Any]
    uploaded_data: Dict[str, Any]

    # 메타데이터
    task_id: str
    start_time: datetime
    errors: List[str]

    # 최종 결과
    final_result: Dict[str, Any]


class ProjectManagerAgent(BaseAgent):
    """
    프로젝트 관리자 에이전트 - 전체 워크플로우 오케스트레이션

    역할:
    1. 사용자 명령 분석 (Qwen3 사용)
    2. 작업 계획 수립
    3. 적절한 에이전트 선택 및 순서 결정
    4. 에이전트 간 데이터 전달
    5. 최종 결과 취합
    """

    def __init__(self, llm: ChatOllama = None):
        super().__init__(name="ProjectManager", description="Orchestrates multi-agent workflow")

        # LLM 초기화 (싱글톤 공유 인스턴스 사용)
        self.llm = llm or get_shared_llm()

        # 특화 에이전트들 초기화
        self.document_scanner = DocumentScannerAgent()
        self.extracting_agent = ExtractingAgent(llm=self.llm)
        self.uploading_agent = UploadingAgent()
        self.logging_agent = LoggingAgent()

        # 워크플로우 그래프 설정
        self.workflow = None
        self.setup_workflow()

    def setup_workflow(self):
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("analyze_command", self.analyze_command_node)
        workflow.add_node("resolve_file", self.resolve_file_node)
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("upload", self.upload_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 설정
        workflow.add_edge("analyze_command", "resolve_file")
        workflow.add_edge("resolve_file", "extract")
        workflow.add_edge("extract", "upload")
        workflow.add_edge("upload", "finalize")
        workflow.add_edge("finalize", END)

        # 시작점 설정
        workflow.set_entry_point("analyze_command")

        # 컴파일
        self.workflow = workflow.compile()

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        메인 실행 로직

        Args:
            task: {
                "user_command": str,  # 사용자 명령
                "file_path": str      # 처리할 파일 (옵션)
            }
        """
        user_command = task["data"].get("user_command", "")
        file_path = task["data"].get("file_path", "")

        if not user_command:
            return {"success": False, "error": "No user command provided"}

        # 초기 상태 설정
        initial_state = {
            "user_command": user_command,
            "file_path": file_path,
            "current_step": "start",
            "plan": [],
            "extracted_data": {},
            "uploaded_data": {},
            "task_id": task.get("task_id", "unknown"),
            "start_time": datetime.now(),
            "errors": [],
            "final_result": {},
        }

        try:
            # 워크플로우 실행
            self._log("Starting workflow execution...")
            result = await asyncio.to_thread(self.workflow.invoke, initial_state)

            # 결과 반환
            if result.get("final_result", {}).get("success", False):
                return {
                    "success": True,
                    "data": result["final_result"],
                    "agent": self.name,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("errors", ["Unknown error"])[0],
                    "agent": self.name,
                }

        except Exception as e:
            self._log(f"Workflow execution failed: {e}", "error")
            return {"success": False, "error": str(e), "agent": self.name}

    def analyze_command_node(self, state: AgentState) -> AgentState:
        """
        사용자 명령 분석 및 작업 계획 수립
        
        Known commands (upload, process, analyze) bypass LLM for speed.
        Only natural language commands require LLM analysis.
        """
        user_command = state["user_command"]
        file_path = state.get("file_path", "")
        
        # Check for known commands - skip LLM if command is structured
        known_commands = {
            "upload": ["extract", "upload"],
            "process": ["extract", "upload"],
            "analyze": ["extract"],
        }
        
        command_parts = user_command.strip().split()
        first_word = command_parts[0].lower() if command_parts else ""
        
        if first_word in known_commands and file_path:
            # Skip LLM - use predefined actions for known commands
            self._log(f"Processing '{first_word}' command...")
            
            # Extract filename from command if no file_path was pre-resolved
            if not file_path and len(command_parts) > 1:
                file_path = " ".join(command_parts[1:])
            
            state["file_path"] = file_path
            state["plan"] = known_commands[first_word]
            state["current_step"] = "analyzed"
            
            self._log(f"File: {file_path}")
            self._log(f"Actions: {', '.join(state['plan'])}")
            
            return state
        
        # Use LLM only for natural language / ambiguous commands
        self._log("Analyzing user command with LLM...")

        # Qwen3에게 명령 분석 요청
        prompt = f"""You are a project manager for a blog automation system. 
Analyze this user command and determine the file path and required actions.

User command: "{user_command}"

Respond in this format:
FILE_PATH: [extracted file path or "not specified"]
ACTIONS: [comma-separated list of actions: extract, upload, analyze_metadata]
REASONING: [brief explanation]

Examples:
- "upload ./posts/my-article.md" -> FILE_PATH: ./posts/my-article.md, ACTIONS: extract, upload
- "process new-post.md with metadata" -> FILE_PATH: new-post.md, ACTIONS: extract, analyze_metadata, upload
"""

        try:
            response = self.llm.invoke(prompt)
            analysis = response.content

            # 파싱
            import re

            file_match = re.search(r"FILE_PATH:\s*(.+)", analysis)
            actions_match = re.search(r"ACTIONS:\s*(.+)", analysis)

            parsed_file = file_match.group(1).strip() if file_match else file_path
            if parsed_file == "not specified":
                parsed_file = file_path

            actions_str = actions_match.group(1).strip() if actions_match else "extract, upload"
            actions = [a.strip() for a in actions_str.split(",")]

            self._log(f"Extracted file: {parsed_file}")
            self._log(f"Planned actions: {', '.join(actions)}")

            state["file_path"] = parsed_file
            state["plan"] = actions
            state["current_step"] = "analyzed"

        except Exception as e:
            self._log(f"Command analysis failed: {e}", "warning")
            # 폴백: 기본 계획
            state["plan"] = ["extract", "upload"]
            state["current_step"] = "analyzed"

        return state

    def resolve_file_node(self, state: AgentState) -> AgentState:
        """
        파일 경로 해결 - DocumentScannerAgent를 사용하여 파일 찾기
        
        직접 경로가 없으면 파일 이름으로 검색
        """
        from pathlib import Path
        
        file_path = state.get("file_path", "")
        
        if not file_path:
            self._log("No file path to resolve", "warning")
            return state
        
        self._log(f"Resolving file: {file_path}")
        
        # 직접 경로가 존재하면 그대로 사용
        if Path(file_path).exists():
            self._log(f"File exists at: {file_path}")
            state["current_step"] = "resolved"
            return state
        
        # 파일이 없으면 DocumentScannerAgent로 검색
        self._log(f"File not found, searching with DocumentScannerAgent...")
        matches = self.document_scanner.find_file_by_name(file_path)
        
        if not matches:
            state["errors"].append(f"File not found: {file_path}")
            self._log(f"No matches found for: {file_path}", "error")
            return state
        
        if len(matches) == 1:
            # 단일 매치 - 바로 사용
            resolved_path = matches[0]["path"]
            state["file_path"] = resolved_path
            self._log(f"Found: {resolved_path}", "success")
        else:
            # 다중 매치 - 첫 번째(가장 좋은 매치) 사용
            resolved_path = matches[0]["path"]
            state["file_path"] = resolved_path
            self._log(f"Multiple matches found, using best match: {resolved_path}", "warning")
            for m in matches[1:4]:  # Show up to 3 other matches
                self._log(f"  Other match: {m['name']} ({m['match_type']})")
        
        state["current_step"] = "resolved"
        return state

    def extract_node(self, state: AgentState) -> AgentState:
        """ExtractingAgent 호출"""
        self._log("Calling ExtractingAgent...")

        file_path = state["file_path"]
        if not file_path:
            state["errors"].append("No file path specified")
            return state

        # ExtractingAgent 실행
        task = {
            "task_id": state["task_id"],
            "action": "extract",
            "data": {
                "file_path": file_path,
                "extract_metadata": "analyze_metadata" in state["plan"],
            },
        }

        # 동기 실행 (LangGraph 노드는 동기)
        import asyncio

        result = asyncio.run(self.extracting_agent.run(task))

        if result["success"]:
            state["extracted_data"] = result["data"]
            state["current_step"] = "extracted"
            self._log(f"Extraction completed: {result['data']['title']}", "success")
        else:
            state["errors"].append(f"Extraction failed: {result.get('error', 'Unknown')}")
            self._log(f"Extraction failed", "error")

        return state

    def upload_node(self, state: AgentState) -> AgentState:
        """UploadingAgent 호출"""
        self._log("Calling UploadingAgent...")

        if not state.get("extracted_data"):
            state["errors"].append("No extracted data to upload")
            return state

        # UploadingAgent 실행
        task = {
            "task_id": state["task_id"],
            "action": "full_upload",
            "data": state["extracted_data"],
        }

        import asyncio

        result = asyncio.run(self.uploading_agent.run(task))

        if result["success"]:
            state["uploaded_data"] = result["data"]
            state["current_step"] = "uploaded"
            self._log(
                f"Upload completed: Article ID {result['data']['article_id']}",
                "success",
            )
        else:
            state["errors"].append(f"Upload failed: {result.get('error', 'Unknown')}")
            self._log(f"Upload failed", "error")

        return state

    def finalize_node(self, state: AgentState) -> AgentState:
        """최종 결과 정리 및 로깅"""
        self._log("Finalizing workflow...")

        # 성공 여부 판단
        success = len(state["errors"]) == 0 and state.get("uploaded_data")

        if success:
            # 파일 이름 추출
            from pathlib import Path
            file_name = Path(state.get("file_path", "")).name or "N/A"
            
            # 이미지 정보 추출
            extracted_images = state["extracted_data"].get("images", [])
            thumbnail = state["extracted_data"].get("thumbnail")
            uploaded_images = state["uploaded_data"].get("images", [])
            
            # 최종 결과 구성
            state["final_result"] = {
                "success": True,
                "data": {
                    **state["uploaded_data"],
                    "file_name": file_name,
                    "thumbnail": thumbnail,
                    "images": uploaded_images,
                    "extracted_metadata": {
                        "title": state["extracted_data"].get("title"),
                        "categories": state["extracted_data"].get("categories", []),  # Full hierarchy
                        "category": state["extracted_data"].get("category"),  # Backward compat
                        "tags": state["extracted_data"].get("tags"),
                        "word_count": state["extracted_data"].get("word_count"),
                        "reading_time": state["extracted_data"].get("reading_time"),
                        "user_id": state["extracted_data"].get("user_id"),
                        "username": state["extracted_data"].get("username"),
                        "status": state["extracted_data"].get("status"),
                        "date": state["extracted_data"].get("date"),
                        "description": state["extracted_data"].get("description"),
                        "summary": state["extracted_data"].get("summary"),
                    },
                    # Include MCP payload from uploaded_data
                    "mcp_payload": state["uploaded_data"].get("mcp_payload"),
                },
            }

            # LoggingAgent로 결과 출력
            log_task = {
                "task_id": state["task_id"],
                "action": "log_result",
                "data": {"result": state["final_result"]},
            }
            import asyncio

            asyncio.run(self.logging_agent.run(log_task))

        else:
            # 실패
            state["final_result"] = {
                "success": False,
                "error": "; ".join(state["errors"]),
            }

            # 에러 로깅
            log_task = {
                "task_id": state["task_id"],
                "action": "log_error",
                "data": {
                    "error": state["final_result"]["error"],
                    "agent_name": self.name,
                },
            }
            import asyncio

            asyncio.run(self.logging_agent.run(log_task))

        state["current_step"] = "finalized"

        # 실행 시간 계산
        duration = (datetime.now() - state["start_time"]).total_seconds()
        self._log(f"Workflow completed in {duration:.2f}s")

        return state

    def get_agents_info(self) -> List[Dict[str, Any]]:
        """모든 에이전트 정보 반환"""
        return [
            self.get_info(),
            self.document_scanner.get_info(),
            self.extracting_agent.get_info(),
            self.uploading_agent.get_info(),
            self.logging_agent.get_info(),
        ]

    def check_file_exists(
        self, filename: str, quiet: bool = False, search_root: str | None = None
    ) -> Dict[str, Any]:
        """
        파일 이름으로 존재 여부 확인 및 경로 반환

        Args:
            filename: 파일 이름 또는 부분 경로
            quiet: True면 로깅 안함 (CLI find 명령용)
            search_root: 검색할 루트 폴더 (None이면 기본 posts/, docs/ 사용)

        Returns:
            {
                "exists": bool,
                "path": str or None,
                "matches": List[Dict] - all matches if multiple
            }
        """
        from pathlib import Path

        result = {
            "exists": False,
            "path": None,
            "matches": []
        }
        
        # 1. Check if it's a direct path that exists
        if Path(filename).exists():
            result["exists"] = True
            result["path"] = str(Path(filename).resolve())
            if not quiet:
                self._log(f"File exists: {result['path']}", "success")
            return result
        
        # 2. Use DocumentScannerAgent to find the file
        search_dirs = [Path(search_root)] if search_root else None
        matches = self.document_scanner.find_file_by_name(filename, search_dirs=search_dirs)
        
        if not matches:
            if not quiet:
                self._log(f"File not found: {filename}", "error")
            return result
        
        result["matches"] = matches
        
        if len(matches) == 1:
            result["exists"] = True
            result["path"] = matches[0]["path"]
            if not quiet:
                self._log(f"Found: {result['path']}", "success")
        else:
            # Multiple matches - show suggestions
            result["exists"] = True
            result["path"] = matches[0]["path"]  # Best match
            if not quiet:
                self._log(f"Found {len(matches)} matches for '{filename}':", "warning")
                for m in matches[:5]:
                    self._log(f"  • {m['name']} ({m['match_type']})")
        
        return result

    def list_available_files(self) -> Dict[str, Any]:
        """
        DocumentScannerAgent를 사용하여 사용 가능한 모든 파일 스캔
        
        Returns:
            {
                "posts": [...],
                "docs": {...},
                "total_files": int
            }
        """
        from pathlib import Path
        from config import POSTS_DIR, PROJECT_ROOT
        
        self._log("Scanning available files...")
        
        result = {
            "posts": [],
            "docs": {},
            "total_files": 0
        }
        
        # Scan posts/ directory (flat structure)
        if POSTS_DIR.exists():
            for md_file in POSTS_DIR.glob("*.md"):
                result["posts"].append({
                    "name": md_file.name,
                    "path": str(md_file),
                    "size": md_file.stat().st_size
                })
        
        # Scan docs/ directory (nested structure with categories)
        docs_dir = PROJECT_ROOT / "docs"
        if docs_dir.exists():
            # Use DocumentScannerAgent's internal scan method directly (sync)
            scan_data = self.document_scanner._scan_documentation(docs_dir)
            result["docs"] = scan_data
        
        result["total_files"] = len(result["posts"]) + result["docs"].get("total_articles", 0)
        
        self._log(f"Found {result['total_files']} files total", "success")
        return result

    def print_file_tree(self, root_dir: str = "posts") -> None:
        """
        터미널에 파일 트리 출력
        
        Args:
            root_dir: 스캔할 루트 디렉토리 (기본값: posts)
        """
        from rich.console import Console
        from rich.tree import Tree
        from pathlib import Path
        import config
        
        console = Console()
        target_dir = config.PROJECT_ROOT / root_dir
        
        if not target_dir.exists():
            console.print(f"[red]❌ Directory not found: {root_dir}[/red]")
            return
        
        tree = Tree(f"📁 [bold]{root_dir}/[/bold]")
        
        def add_files_to_tree(branch, directory, depth=0):
            """Recursively add files and folders to tree"""
            items = sorted(directory.iterdir(), key=lambda x: (x.is_file(), x.name))
            
            file_count = 0
            for item in items:
                if item.name.startswith('.'):
                    continue
                    
                if item.is_dir():
                    # Add folder
                    folder_branch = branch.add(f"📂 [blue]{item.name}/[/blue]")
                    sub_count = add_files_to_tree(folder_branch, item, depth + 1)
                    if sub_count == 0:
                        folder_branch.label = f"📂 [dim]{item.name}/[/dim] [dim](empty)[/dim]"
                    file_count += sub_count
                elif item.suffix == ".md":
                    # Markdown file
                    size_kb = item.stat().st_size / 1024
                    branch.add(f"📄 {item.name} [dim]({size_kb:.1f}KB)[/dim]")
                    file_count += 1
                elif item.suffix in [".png", ".jpg", ".jpeg", ".gif", ".webp"]:
                    # Image file
                    size_kb = item.stat().st_size / 1024
                    branch.add(f"📷 [dim]{item.name} ({size_kb:.1f}KB)[/dim]")
            
            return file_count
        
        total = add_files_to_tree(tree, target_dir)
        
        if total == 0:
            tree.add("[dim]No markdown files found[/dim]")
        
        tree.add(f"\n[bold]Total:[/bold] {total} markdown file(s)")
        console.print(tree)
