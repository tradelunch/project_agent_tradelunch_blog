# 00_config.py
"""
00. Configuration - 시스템 전역 설정

모든 에이전트와 모듈에서 사용하는 설정값들을 정의합니다.
- LLM 설정 (Qwen3/Ollama)
- AWS 설정 (S3, RDS)
- MCP 설정
- 파일 경로 설정
- 에이전트 설정
"""

import os
from pathlib import Path

# ==================== LLM 설정 ====================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3:8b")
LLM_TEMPERATURE = 0.3

# ==================== AWS 설정 ====================
S3_BUCKET = os.getenv("S3_BUCKET", "my-blog-bucket")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_PREFIX = "blog-images/"

# ==================== RDS 설정 ====================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "blog_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# ==================== MCP 설정 ====================
MCP_SERVER_PATH = os.getenv("MCP_SERVER_PATH", "./mcp-server/build/index.js")
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"

# ==================== 파일 경로 설정 ====================
PROJECT_ROOT = Path(__file__).parent
POSTS_DIR = PROJECT_ROOT / "posts"
TEMP_DIR = PROJECT_ROOT / "temp"
LOGS_DIR = PROJECT_ROOT / "logs"

# 디렉토리 생성
POSTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ==================== Agent 설정 ====================
AGENT_TIMEOUT = 300  # seconds
MAX_RETRIES = 3

# ==================== CLI 설정 ====================
CLI_HISTORY_FILE = PROJECT_ROOT / ".agent_history.json"
CLI_MAX_HISTORY = 100

# ==================== 로깅 설정 ====================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
