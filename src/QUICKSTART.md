# 🚀 Quick Start Guide

## 설치 및 실행 (5분 안에!)

### 1. Ollama 설치 및 Qwen3 모델 다운로드

```bash
# Ollama 설치 (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Windows: https://ollama.com/download 에서 다운로드

# Qwen3 8B 모델 다운로드 (약 4.7GB)
ollama pull qwen3:8b

# 모델 테스트
ollama run qwen3:8b "안녕하세요"
```

### 2. Python 환경 설정

```bash
# 프로젝트 디렉토리로 이동
cd blog-agent

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 시스템 테스트

```bash
# 테스트 실행 (Ollama 없이도 대부분 작동)
python 90_test_agents.py
```

예상 출력:
```
============================================================
🧪 Blog Multi-Agent System - Test Suite
============================================================

📋 Phase 1: Individual Agent Tests (No LLM required)

============================================================
Testing ExtractingAgent
============================================================
✅ Title: Getting Started with LangGraph Multi-Agent Systems
✅ Slug: getting-started-with-langgraph-multi-agent-systems
✅ Images found: 3
✅ Word count: 234

============================================================
Testing UploadingAgent
============================================================
✅ Article ID: 789
✅ Published URL: https://myblog.com/posts/test-article
✅ Images uploaded: 1

============================================================
Testing LoggingAgent
============================================================
✅ LoggingAgent test completed

📊 Test Results Summary
============================================================
✅ PASSED - Extracting
✅ PASSED - Uploading
✅ PASSED - Logging

Total: 3/3 tests passed
============================================================

🎉 All tests passed! System is ready.
```

### 4. Ollama 서버 시작

**별도 터미널에서:**
```bash
ollama serve
```

이 터미널은 계속 열어두세요!

### 5. CLI 실행

**원래 터미널에서:**
```bash
python 10_cli_multi_agent.py
```

## 📝 첫 번째 블로그 포스트 업로드

### 방법 1: 제공된 샘플 사용

```bash
blog-agent> upload ./posts/sample-post.md
```

### 방법 2: 자신의 마크다운 파일 만들기

```bash
# 1. 새 마크다운 파일 생성
cat > ./posts/my-first-post.md << 'EOF'
---
title: "My First Blog Post"
author: "Your Name"
date: "2026-01-03"
---

# Hello World

This is my first post using the multi-agent system!

## Why This is Cool

- Automated processing
- Intelligent categorization
- Easy to use

![My Image](./images/photo.jpg)
EOF

# 2. CLI에서 업로드
blog-agent> upload ./posts/my-first-post.md
```

## 🎯 주요 명령어

```bash
# 파일 업로드
blog-agent> upload ./posts/article.md

# 메타데이터 분석 포함 처리
blog-agent> process ./posts/article.md

# 상태 확인
blog-agent> status

# 에이전트 목록
blog-agent> agents

# 히스토리 보기
blog-agent> history

# 도움말
blog-agent> help

# 종료
blog-agent> exit
```

## 🔧 문제 해결

### "Connection refused" 에러

**원인**: Ollama가 실행되지 않음

**해결**:
```bash
# 별도 터미널에서
ollama serve
```

### "Model not found" 에러

**원인**: Qwen3 모델이 다운로드되지 않음

**해결**:
```bash
ollama pull qwen3:8b
```

### Import 에러

**원인**: 의존성이 제대로 설치되지 않음

**해결**:
```bash
pip install -r requirements.txt --force-reinstall
```

### 파일을 찾을 수 없음

**원인**: 잘못된 경로

**해결**:
```bash
# 현재 디렉토리 확인
pwd

# posts 디렉토리 확인
ls -la ./posts/

# 절대 경로 사용
blog-agent> upload /full/path/to/post.md
```

## 🎉 성공 확인

시스템이 제대로 작동하면 다음과 같은 출력을 볼 수 있습니다:

```
╭─ 📝 Blog Post Published ─────────────────────╮
│                                               │
│ ✅ Task Completed Successfully!              │
│                                               │
│ Article Details:                              │
│   • Title: My First Blog Post                 │
│   • Category: General                         │
│   • Article ID: 456                           │
│   • Slug: my-first-blog-post                  │
│   • Images: 1                                 │
│                                               │
│ Published URL:                                │
│   https://myblog.com/posts/my-first-blog-post │
│                                               │
╰───────────────────────────────────────────────╯
```

## 📚 다음 단계

1. **MCP 서버 구축**: 실제 S3/RDS 연동
2. **추가 에이전트**: SEO, Translation, Validation 등
3. **자동화**: GitHub Actions로 커밋 시 자동 처리
4. **웹 인터페이스**: Flask/FastAPI로 웹 UI 추가

## 💡 팁

- 자연어로 명령할 수 있습니다: `"please upload my article"`
- `history` 명령으로 이전 작업 확인 가능
- `status` 명령으로 실시간 에이전트 상태 확인
- Qwen3가 카테고리를 자동으로 분류해줍니다!

---

질문이나 이슈가 있다면 GitHub Issues에 올려주세요!
