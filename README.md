# Blog Multi-Agent System

A multi-agent system for automating blog post processing using LangGraph and Qwen3 8B.

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│      Project Manager Agent              │
│      (Qwen3 Orchestrator)               │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Document│ │Extract-│ │Upload- │ │Logging │
│Scanner │ │  ing   │ │  ing   │ │ Agent  │
│ Agent  │ │ Agent  │ │ Agent  │ │        │
└────────┘ └────────┘ └────────┘ └────────┘
```

## 🤖 Agents

### 1. Project Manager Agent
- **Role**: Orchestrates the entire workflow
- **Tech**: Qwen3 8B + LangGraph
- Analyzes user commands
- Determines which agents to use and in what order
- Coordinates data flow between agents

### 2. Extracting Agent
- **Role**: Markdown parsing and metadata extraction
- **Tech**: Rule-based + Qwen3 for categorization
- Parses frontmatter and content
- Extracts images
- Generates categories and tags using LLM

### 3. Uploading Agent
- **Role**: External system communication
- **Tech**: MCP (Model Context Protocol)
- Uploads images to S3
- Saves articles to RDS
- Returns URLs and IDs

### 4. Logging Agent
- **Role**: Unified logging and terminal output
- **Tech**: Rich library
- Formats agent-specific logs
- Shows progress indicators
- Displays final results

## 📦 Installation

### Prerequisites

1. **Ollama** with Qwen3 8B model
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull Qwen3 8B
ollama pull qwen3:8b

# Start Ollama server
ollama serve
```

2. **Python 3.10+**

### Setup

```bash
# Clone or create project directory
cd blog-agent

# Create virtual environment with pyenv (recommended)
python -m venv tradelunch-agents-venv
source tradelunch-agents-venv/bin/activate  # On Windows: tradelunch-agents-venv\Scripts\activate

# Install project and dependencies
pip install -e .

# Install dev dependencies (optional, for testing and linting)
pip install -e ".[dev]"
```

**Note:** The project uses `pyproject.toml` (PEP 621 standard) for dependency management, which replaces the traditional `requirements.txt` approach.

## 🚀 Usage

### Start the CLI

```bash
python cli_multi_agent.py
```

### Available Commands

#### File Processing
```bash
# Upload a blog post
blog-agent> upload ./posts/my-article.md

# Process with metadata extraction
blog-agent> process ./posts/article.md

# Analyze only (no upload)
blog-agent> analyze ./posts/draft.md
```

#### System Commands
```bash
# Show system status
blog-agent> status

# List all agents
blog-agent> agents

# Show command history
blog-agent> history

# Show help
blog-agent> help

# Exit
blog-agent> exit
```

#### Natural Language
You can also use natural language:
```bash
blog-agent> Please upload the file at ./posts/new-post.md
blog-agent> Process tutorial.md with category detection
blog-agent> Show me the agent status
```

## 📁 Project Structure

```
blog-agent/
├── agents/                      # Agent modules
│   ├── __init__.py
│   ├── base.py                  # BaseAgent abstract class
│   ├── protocol.py              # Communication protocol
│   ├── document_scanner_agent.py  # Folder structure scanner
│   ├── extracting_agent.py      # Markdown parsing
│   ├── uploading_agent.py       # S3/RDS upload
│   ├── logging_agent.py         # Logging & output
│   └── project_manager.py       # Orchestrator
├── configs/                     # Configuration modules
│   ├── env.py                   # Environment detection
│   ├── aws.py                   # AWS settings
│   ├── database.py              # Database settings
│   ├── llm.py                   # LLM settings
│   ├── agent.py                 # Agent-specific settings
│   └── paths.py                 # Path settings
├── db/                          # Database & Storage
│   ├── repositories/            # Data access layer
│   │   ├── base.py              # Base repository class
│   │   ├── category.py          # Category operations
│   │   ├── post.py              # Post operations
│   │   ├── file.py              # File operations
│   │   └── tag.py               # Tag operations
│   ├── base.py                  # Base model, mixins
│   ├── connection.py            # Session management
│   ├── models.py                # SQL models
│   └── s3.py                    # S3 utilities
├── __tests__/                   # Test suite
│   ├── test_agents.py           # Basic tests
│   ├── test_improved_agents.py  # LLM tests
│   ├── test_llm_providers.py    # Provider tests
│   ├── test_snowflake.py        # ID generation tests
│   └── test_category_storage.py # Category logic tests
├── docs/                        # Project documentation
│   └── technology/
├── posts/                       # Sample markdown
│   └── sample-post.md
├── schema/                      # Database schema
│   └── tradelunch.schema.sql    # SQL DDL
├── utils/                       # Shared utilities
│   └── snowflake.py             # ID generator
├── .python-version              # Python version (pyenv)
├── pyproject.toml               # Project config (PEP 621)
├── config.py                    # Global config entry point
├── cli_multi_agent.py           # CLI interface
├── README.md
└── CLAUDE.md                    # Claude Code guide
```

## 🔧 Configuration

Edit `config.py` to customize:

```python
# LLM Settings
MODEL_NAME = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434"

# AWS Settings
S3_BUCKET = "my-blog-bucket"
S3_REGION = "us-east-1"

# Database Settings
DB_CONFIG = {
    "host": "localhost",
    "database": "blog_db",
    ...
}
```

## 📝 Markdown File Format

### Basic Format
```markdown
---
title: "Your Post Title"
userId: 1
status: 'public'  # 'public', 'private', or 'follower'
author: "Your Name"
date: "2026-01-03"
---

# Your Post Title

Content goes here...

![Image](./images/diagram.png)
```

### Status Values (Post Visibility)

The `status` field controls who can see your post:

| Status | Visibility | Use Case |
|--------|------------|----------|
| `'public'` | Everyone | Published articles (default) |
| `'private'` | Only author | Drafts, personal notes |
| `'follower'` | Followers only | Exclusive content |

**Important:** Tags and description are **always generated by LLM** from content analysis (frontmatter values are ignored).

See [FRONTMATTER_GUIDE.md](FRONTMATTER_GUIDE.md) for complete documentation.

## 🎯 Features

- ✅ **Modular Design**: Each agent handles specific tasks
- ✅ **Natural Language**: Use conversational commands
- ✅ **Intelligent Routing**: Qwen3 decides the workflow
- ✅ **Progress Tracking**: Real-time status updates
- ✅ **Rich Terminal UI**: Beautiful formatted output
- ✅ **Command History**: Track all operations

## 🔮 Future Enhancements

### Additional Agents
- **ValidationAgent**: Check markdown quality
- **TranslationAgent**: Multi-language support
- **SEOAgent**: Optimize for search engines
- **ImageAgent**: AI image generation

### MCP Integration
Once MCP server is implemented:
- Real S3 uploads
- Actual RDS operations
- Cloud deployment

## 🐛 Troubleshooting

### Ollama Connection Error
```bash
# Make sure Ollama is running
ollama serve

# Test connection
ollama run qwen3:8b "Hello"
```

### Import Errors
```bash
# Reinstall dependencies
pip install -e . --force-reinstall
```

### File Not Found
```bash
# Check file path
ls -la ./posts/

# Use absolute path
blog-agent> upload /full/path/to/post.md
```

## 📊 Example Session

```
╔══════════════════════════════════════════════╗
║   📝 Blog Multi-Agent System                ║
║   Powered by Qwen3 8B + LangGraph           ║
╚══════════════════════════════════════════════╝

blog-agent> upload ./posts/sample-post.md

────────────────────────────────────────────────────────
Executing: upload ./posts/sample-post.md
────────────────────────────────────────────────────────

[14:23:15] ℹ️ [ProjectManager] Starting workflow execution...
[14:23:15] ℹ️ [ProjectManager] Analyzing user command with LLM...
[14:23:16] ℹ️ [ProjectManager] Extracted file: ./posts/sample-post.md
[14:23:16] ℹ️ [ProjectManager] Planned actions: extract, upload
[14:23:16] ℹ️ [ProjectManager] Calling ExtractingAgent...
[14:23:16] ℹ️ [ExtractingAgent] Parsing file: ./posts/sample-post.md
[14:23:16] ℹ️ [ExtractingAgent] Extracting images...
[14:23:16] ℹ️ [ExtractingAgent] Found 3 image(s)
[14:23:16] ✅ [ExtractingAgent] Task task_abc123 completed
[14:23:16] ℹ️ [ProjectManager] Extraction completed: Getting Started with LangGraph
[14:23:16] ℹ️ [ProjectManager] Calling UploadingAgent...
[14:23:16] ℹ️ [UploadingAgent] Uploading 3 image(s) to S3...
[14:23:17] ℹ️ [UploadingAgent] Uploaded: architecture.png -> https://s3...
[14:23:17] ℹ️ [UploadingAgent] Uploaded: flow-diagram.png -> https://s3...
[14:23:18] ℹ️ [UploadingAgent] Uploaded: results-chart.png -> https://s3...
[14:23:18] ℹ️ [UploadingAgent] Saving article to database...
[14:23:18] ℹ️ [UploadingAgent] Article saved with ID: 456
[14:23:18] ✅ [UploadingAgent] Task task_abc123 completed

╭─ 📝 Blog Post Published ─────────────────────╮
│                                               │
│ ✅ Task Completed Successfully!              │
│                                               │
│ Article Details:                              │
│   • Title: Getting Started with LangGraph    │
│   • Category: Tutorial                        │
│   • Article ID: 456                           │
│   • Slug: getting-started-with-langgraph      │
│   • Images: 3                                 │
│                                               │
│ Published URL:                                │
│   https://myblog.com/posts/getting-started... │
│                                               │
╰───────────────────────────────────────────────╯

blog-agent> status

╭─ 📊 Status ───────────────────────────────────╮
│                                               │
│ System Status:                                │
│                                               │
│ Agents:                                       │
│   🟢 ProjectManager: [idle]                  │
│   🟢 ExtractingAgent: [completed]            │
│   🟢 UploadingAgent: [completed]             │
│   🟢 LoggingAgent: [idle]                    │
│                                               │
│ Session:                                      │
│   • Commands executed: 1                      │
│   • Model: qwen3:8b                        │
│                                               │
╰───────────────────────────────────────────────╯

blog-agent> exit
Goodbye! 👋
```

## 📄 License

MIT

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.
