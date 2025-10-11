# MCP Servers Setup

## Overview

This project uses two MCP servers with different transport mechanisms:

### 1. Context7 MCP Server (HTTP)

- **Transport**: `streamable_http`
- **Runs via**: Docker Compose
- **Endpoint**: `http://localhost:8080/mcp`
- **Purpose**: Fetch up-to-date library documentation

### 2. Fetch MCP Server (stdio)

- **Transport**: `stdio`
- **Runs via**: Direct Docker command (launched by MCP client)
- **Command**: `docker run -i --rm mcp/fetch`
- **Purpose**: Download HTML website contents as Markdown

## Configuration

### Environment Variables (.env)

```properties
# Context7 (HTTP-based)
MCP_CONTEXT7_URL=http://localhost:8080/mcp
CONTEXT7_API_KEY=your-api-key-here

# Fetch (stdio-based)
MCP_FETCH_ENABLED=true
```

### Docker Compose (docker-compose.yaml)

Only Context7 needs a docker-compose service since it uses HTTP:

```yaml
services:
  context7:
    image: mcp/context7
    stdin_open: true
    tty: false
    ports:
      - "8080:8080"
    environment:
      - CONTEXT7_API_KEY=${CONTEXT7_API_KEY}
```

**Note**: Fetch server does NOT need a docker-compose service because:

- It uses stdio (stdin/stdout) for communication, not HTTP
- It's launched on-demand by the MCP client when needed
- Each request spawns a new Docker container that exits after completion

## How It Works

### Context7 (HTTP Server)

1. Start with `docker compose up -d`
2. Server runs continuously on port 8080
3. Client makes HTTP requests to `http://localhost:8080/mcp`

### Fetch (stdio Process)

1. Client spawns: `docker run -i --rm mcp/fetch`
2. Client sends requests via stdin
3. Server responds via stdout
4. Container exits when done (--rm flag)

## Usage

### Start Context7 Server

```bash
docker compose up -d
```

### Enable Fetch Server

Just set `MCP_FETCH_ENABLED=true` in `.env` - no manual startup needed!

### Test Tools

```bash
uv run -m src.cli chat
> :tools
```

You should see:

- `resolve-library-id` (from Context7)
- `get-library-docs` (from Context7)
- `fetch` (from Fetch server)

## Troubleshooting

### Context7 not connecting

```bash
# Check if container is running
docker ps | grep context7

# Check if port is accessible
curl http://localhost:8080/mcp

# Restart container
docker compose restart context7
```

### Fetch not working

```bash
# Test Docker image directly
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | docker run -i --rm mcp/fetch

# Make sure Docker is running
docker info

# Pull latest image
docker pull mcp/fetch
```

### Both servers not connecting

- Make sure Docker Desktop is running
- Check `.env` file has correct values
- Try `docker compose down && docker compose up -d`

## Transport Types Explained

### HTTP (streamable_http)

- Server runs continuously
- Client makes HTTP requests
- Good for: services that need to maintain state, APIs, web services
- Example: Context7

### stdio (Standard Input/Output)

- Server runs per-request
- Client launches process, communicates via pipes
- Good for: CLI tools, scripts, stateless operations
- Example: Fetch

## Why Two Different Transports?

**Context7** uses HTTP because:

- It maintains connections to documentation APIs
- It caches library information
- Multiple requests can share the same server instance

**Fetch** uses stdio because:

- Each fetch is independent
- No state needs to be maintained
- Simpler, more secure (container per request)
- No open ports needed
