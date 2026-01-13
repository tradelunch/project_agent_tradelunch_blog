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

from .base import BaseAgent
from .extracting_agent import ExtractingAgent
from .uploading_agent import UploadingAgent
from .logging_agent import LoggingAgent
from .protocol import AgentTask, AgentResponse


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

    def __init__(
        self, llm_model: str = "qwen3:8b", base_url: str = "http://localhost:11434"
    ):
        super().__init__(
            name="ProjectManager", description="Orchestrates multi-agent workflow"
        )

        # LLM 초기화
        self.llm = ChatOllama(model=llm_model, base_url=base_url, temperature=0)

        # 특화 에이전트들 초기화
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
        workflow.add_node("extract", self.extract_node)
        workflow.add_node("upload", self.upload_node)
        workflow.add_node("finalize", self.finalize_node)

        # 엣지 설정
        workflow.add_edge("analyze_command", "extract")
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
        사용자 명령 분석 및 작업 계획 수립 (Qwen3 사용)
        """
        self._log("Analyzing user command with LLM...")

        user_command = state["user_command"]

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

            file_path = (
                file_match.group(1).strip()
                if file_match
                else state.get("file_path", "")
            )
            if file_path == "not specified":
                file_path = state.get("file_path", "")

            actions_str = (
                actions_match.group(1).strip() if actions_match else "extract, upload"
            )
            actions = [a.strip() for a in actions_str.split(",")]

            self._log(f"Extracted file: {file_path}")
            self._log(f"Planned actions: {', '.join(actions)}")

            state["file_path"] = file_path
            state["plan"] = actions
            state["current_step"] = "analyzed"

        except Exception as e:
            self._log(f"Command analysis failed: {e}", "warning")
            # 폴백: 기본 계획
            state["plan"] = ["extract", "upload"]
            state["current_step"] = "analyzed"

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
            state["errors"].append(
                f"Extraction failed: {result.get('error', 'Unknown')}"
            )
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
            # 최종 결과 구성
            state["final_result"] = {
                "success": True,
                "data": {
                    **state["uploaded_data"],
                    "extracted_metadata": {
                        "title": state["extracted_data"].get("title"),
                        "category": state["extracted_data"].get("category"),
                        "tags": state["extracted_data"].get("tags"),
                        "word_count": state["extracted_data"].get("word_count"),
                    },
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
            self.extracting_agent.get_info(),
            self.uploading_agent.get_info(),
            self.logging_agent.get_info(),
        ]
