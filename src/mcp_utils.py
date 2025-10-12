"""Utilities for handling MCP server connections and errors."""

import asyncio
from typing import Dict, List, Optional, Tuple

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from rich.console import Console

console = Console()


async def test_server_connection(
    client: MultiServerMCPClient, server_name: str, timeout: float = 5.0
) -> Tuple[str, bool, str]:
    """
    Test connection to a single MCP server.

    Args:
        client: The MCP client with all servers configured
        server_name: Name of the server to test
        timeout: Timeout for the connection test in seconds

    Returns:
        Tuple of (server_name, success, message)
    """
    try:
        # Use the client's get_tools method with server_name parameter
        tools = await asyncio.wait_for(
            client.get_tools(server_name=server_name), timeout=timeout
        )
        tool_count = len(tools) if tools else 0
        return (server_name, True, f"Connected ({tool_count} tools)")
    except asyncio.TimeoutError:
        return (server_name, False, "Connection timeout")
    except Exception as e:
        error_msg = str(e)[:100]  # Truncate long errors
        return (server_name, False, error_msg)


async def check_all_servers(
    server_configs: Dict[str, dict],
) -> Tuple[List[Tuple[str, bool, str]], MultiServerMCPClient]:
    """
    Check connectivity to all configured MCP servers.

    Args:
        server_configs: Dictionary of server configurations

    Returns:
        Tuple of (results list, client) where results is a list of
        (server_name, success, message) tuples
    """
    if not server_configs:
        return ([], None)

    # Create a client with all servers
    client = MultiServerMCPClient(server_configs)

    # Test each server individually using concurrent tasks
    tasks = [
        test_server_connection(client, server_name)
        for server_name in server_configs.keys()
    ]
    results = await asyncio.gather(*tasks)

    return (list(results), client)


async def get_tools_from_servers(
    server_configs: Dict[str, dict], verbose: bool = False
) -> Tuple[List[BaseTool], Optional[MultiServerMCPClient], List[Tuple[str, bool, str]]]:
    """
    Get tools from all configured MCP servers.

    This is the main function to use for getting MCP tools. It handles:
    - Server connectivity testing
    - Tool collection from successful servers
    - Error handling for failed servers

    Args:
        server_configs: Dictionary of server configurations
        verbose: If True, print warning messages for failed tool fetches

    Returns:
        Tuple of (tools, client, results) where:
        - tools: List of BaseTool objects from all successful servers
        - client: MultiServerMCPClient instance (or None if no servers connected)
        - results: List of (server_name, success, message) tuples
    """
    if not server_configs:
        return ([], None, [])

    # Check all servers individually
    results, client = await check_all_servers(server_configs)

    # Get successful servers
    successful_servers = [name for name, success, _ in results if success]

    if not successful_servers:
        return ([], None, results)

    # Collect tools from successful servers
    tools = []
    for server_name in successful_servers:
        try:
            server_tools = await client.get_tools(server_name=server_name)
            tools.extend(server_tools)
        except Exception as e:
            if verbose:
                console.print(
                    f"[yellow]⚠️  Warning: Failed to get tools from {server_name}: {e}[/]"
                )

    return (tools, client, results)


def print_server_status(results: List[Tuple[str, bool, str]]):
    """
    Print the status of all MCP servers.

    Args:
        results: List of (server_name, success, message) tuples
    """
    if not results:
        console.print("[yellow]No MCP servers configured[/]")
        return

    console.print("\n[bold]MCP Server Status:[/]")
    for server_name, success, message in results:
        if success:
            console.print(f"  [green]✓[/] {server_name}: [dim]{message}[/]")
        else:
            console.print(f"  [red]✗[/] {server_name}: [dim]{message}[/]")
    console.print()


async def cleanup_client(client: Optional[MultiServerMCPClient]):
    """
    Safely clean up MCP client connections.

    Args:
        client: The MCP client to clean up (can be None)
    """
    if client:
        try:
            await client.connections.clear()
        except Exception:
            pass  # Silently ignore cleanup errors
