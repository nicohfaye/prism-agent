import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()


def create_mcp_client() -> MultiServerMCPClient:
    """
    Create MCP client with configured servers.

    Servers can be configured via environment variables:
    - MCP_CONTEXT7_URL: Context7 mcp server
    """
    servers: Dict[str, Dict[str, Any]] = {}

    # Context7 MCP server (HTTP)
    context7_url = os.getenv("MCP_CONTEXT7_URL")
    if context7_url:
        servers["context7"] = {
            "transport": "streamable_http",
            "url": context7_url,
            "timeout": 10,
        }
        print(f"Configured Context7 MCP server: {context7_url}")

    # Fetch uses stdio transport, not HTTP
    fetch_enabled = os.getenv("MCP_FETCH_ENABLED", "false").lower() == "true"
    if fetch_enabled:
        servers["fetch"] = {
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/fetch"],
        }
        print("Configured Fetch MCP server via stdio")

    time_enabled = os.getenv("MCP_TIME_ENABLED", "false").lower() == "true"
    if time_enabled:
        servers["time"] = {
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/time"],
        }
        print("Configured Time MCP server via stdio")

    if not servers:
        print("No MCP servers configured. Agent will run without external tools.")

    return MultiServerMCPClient(servers)
