# Prism-Agent

A sandboxed LangGraph agent with MCP (Model Context Protocol) tool-calling abilities.

## Features

- 🤖 LangGraph ReAct agent with OpenAI
- 🔧 MCP protocol support for extensible tools
- 🐳 Docker-based MCP servers
- 💬 CLI and FastAPI interfaces

## Prerequisites

This project uses **uv** for python project management and dependencies. [Read the docs here](https://docs.astral.sh/uv/getting-started/installation/)

### 1. Install Dependencies

```bash
uv sync
```

### 2. Start MCP Servers (Docker Compose)

```bash
docker compose up -d

docker ps
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your OpenAI API key
vim .env
```

### 4. Run the Agent

**CLI Interface:**

```bash
uv run -m src.cli chat
```

## Using MCP Tools

The agent automatically discovers and uses tools from connected MCP servers.

### Check Available Tools

```bash
# In CLI
uv run -m src.cli tools

# or in chat
you> :tools
```

### Agent Tool Access

The agent automatically:

1. Discovers tools on startup from MCP servers
2. Understands tool schemas and capabilities
3. Decides when to use tools based on user requests
4. Executes tools and incorporates results

## Configuration

Environment variables in `.env`:

```bash
# required
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini

# MCP Servers
MCP_<NAME>_URL=http://localhost:<PORT>/mcp

# optional Langsmith tracing for LLM calls
LANGSMITH_API_KEY=your-key
LANGSMITH_PROJECT=your-project
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_TRACING=true
```

## Project Structure

```
prism-agent/
├── src/
│   ├── cli.py          # CLI interface
│   ├── server.py       # FastAPI server
│   ├── graph.py        # LangGraph Agent
│   ├── mcp_client.py   # MCP client configuration
│   └── schemas.py      # Pydantic models
├── docker-compose.yml  # MCP server definitions
├── .env.example        # Environment template
└── README.md
```
