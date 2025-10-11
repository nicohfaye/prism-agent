# prism-ai

A sandboxed LangGraph agent with MCP (Model Context Protocol) tool-calling abilities.

## Features

- 🤖 LangGraph ReAct agent with OpenAI
- 🔧 MCP protocol support for extensible tools
- 🐳 Docker-based MCP servers
- 💬 CLI and FastAPI interfaces
- 🧹 Proper resource lifecycle management

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Start MCP Servers (AWS Docs)

```bash
# Start AWS Docs MCP server in Docker
docker compose up -d

# Verify it's running
docker ps
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
```

### 4. Run the Agent

**CLI Interface:**

```bash
uv run -m src.cli chat
```

**FastAPI Server:**

```bash
uvicorn src.server:app --reload
# Visit http://localhost:8000/docs
```

## Using MCP Tools

The agent automatically discovers and uses tools from connected MCP servers.

### Check Available Tools

```bash
# In CLI
uv run -m src.cli tools

# Or in chat
you> :tools
```

### Agent Tool Access

The agent automatically:

1. Discovers tools on startup from MCP servers
2. Understands tool schemas and capabilities
3. Decides when to use tools based on user requests
4. Executes tools and incorporates results

**Example:**

```
you> What tools do you have?
agent> I have access to tools from Context7...

you> Use your tools to help me with X
agent> *calls appropriate tool* Here's what I found...
```

## Architecture

```
┌─────────────────────────────────────┐
│     Your Application                │
│  ┌───────────────────────────────┐  │
│  │  LangGraph Agent              │  │
│  │  + OpenAI (gpt-4o-mini)       │  │
│  └─────────────┬─────────────────┘  │
│                │                     │
│  ┌─────────────▼─────────────────┐  │
│  │  MultiServerMCPClient         │  │
│  │  (LangChain MCP Adapters)     │  │
│  └─────────────┬─────────────────┘  │
└────────────────┼─────────────────────┘
                 │ HTTP (MCP Protocol)
                 ▼
┌────────────────────────────────────┐
│   Docker: MCP Servers              │
│  ┌──────────────────────────────┐  │
│  │  AWS Docs (:3011)            │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

## Configuration

Environment variables in `.env`:

```bash
# Required
OPENAI_API_KEY=sk-your-key

# MCP Servers
MCP_AWS_DOCS_URL=http://localhost:3011

# Optional
OPENAI_MODEL=gpt-4o-mini
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=prism-ai
```

## Documentation

- [MCP Setup Guide](./MCP_SETUP.md) - Detailed MCP server configuration (AWS Docs)
- [API Documentation](http://localhost:8000/docs) - FastAPI interactive docs (when server running)

## Development

```bash
# Run tests (if available)
pytest

# Format code
black src/

# Type checking
mypy src/
```

## Project Structure

```
prism-ai/
├── src/
│   ├── cli.py          # CLI interface
│   ├── server.py       # FastAPI server
│   ├── graph.py        # Agent construction
│   ├── mcp_client.py   # MCP client configuration
│   └── schemas.py      # Pydantic models
├── docker-compose.yml  # MCP server definitions (AWS Docs)
├── .env.example        # Environment template
└── README.md
```

## License

MIT
