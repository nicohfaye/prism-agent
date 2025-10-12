import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()


def get_server_configs() -> Dict[str, Dict[str, Any]]:
    """
    Get MCP server configurations without creating a client.

    Returns:
        Dictionary of server configurations
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

    # Fetch uses stdio transport, not HTTP
    fetch_enabled = os.getenv("MCP_FETCH_ENABLED", "false").lower() == "true"
    if fetch_enabled:
        servers["fetch"] = {
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/fetch"],
        }

    time_enabled = os.getenv("MCP_TIME_ENABLED", "false").lower() == "true"
    if time_enabled:
        servers["time"] = {
            "transport": "stdio",
            "command": "docker",
            "args": ["run", "-i", "--rm", "mcp/time"],
        }

    return servers


def create_mcp_client() -> MultiServerMCPClient:
    """
    Create MCP client with configured servers.

    Servers can be configured via environment variables:
    - MCP_CONTEXT7_URL: Context7 mcp server
    - MCP_FETCH_ENABLED: Enable fetch server
    - MCP_TIME_ENABLED: Enable time server
    """
    servers = get_server_configs()

    # Print configured servers
    for name, config in servers.items():
        if config.get("transport") == "streamable_http":
            print(f"Configured {name.title()} MCP server: {config['url']}")
        else:
            print(f"Configured {name.title()} MCP server via stdio")

    if not servers:
        print("No MCP servers configured. Agent will run without external tools.")

    return MultiServerMCPClient(servers)
