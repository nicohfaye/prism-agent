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

    # Context7 MCP server
    context7_url = os.getenv("MCP_CONTEXT7_URL")
    if context7_url:
        servers["context7"] = {
            "transport": "streamable_http",
            "url": context7_url,
            "timeout": 5,  # 5 second timeout
        }
        print(f"Configured Context7 MCP server: {context7_url}")

    if not servers:
        print("No MCP servers configured. Agent will run without external tools.")

    return MultiServerMCPClient(servers)
