"""Command handlers for the CLI application."""

import time
from typing import Optional

from rich.console import Console

from .mcp_client import get_server_configs
from .mcp_utils import cleanup_client, get_tools_from_servers, print_server_status
from .session import Session
from .ui import (
    print_error,
    print_response_stats,
    print_tool,
    print_tool_usage,
    print_warning,
)

console = Console()


def _handle_tool_calls(
    chunk, tools_used: list, status, first_content_received: bool
) -> bool:
    """
    Handle tool call chunks during streaming.

    Args:
        chunk: The chunk from the stream event
        tools_used: List to track tool names
        status: The console status spinner
        first_content_received: Whether any content has been received yet

    Returns:
        Updated first_content_received flag
    """
    if chunk and hasattr(chunk, "tool_calls") and chunk.tool_calls:
        for tool_call in chunk.tool_calls:
            tool_name = tool_call.get("name", "unknown")
            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)
                # Stop spinner before showing tool usage
                if not first_content_received:
                    status.stop()
                    first_content_received = True
                # Show tool usage in real-time
                print_tool_usage(tool_name)
    return first_content_received


def _handle_content_chunk(
    chunk, first_content_received: bool, status
) -> tuple[str, bool]:
    """
    Handle content chunks during streaming.

    Args:
        chunk: The chunk from the stream event
        first_content_received: Whether any content has been received yet
        status: The console status spinner

    Returns:
        Tuple of (content_text, updated first_content_received flag)
    """
    if chunk and hasattr(chunk, "content") and chunk.content:
        content = chunk.content
        if isinstance(content, str):
            # Stop spinner on first content
            if not first_content_received:
                status.stop()
                first_content_received = True
            console.print(content, end="", markup=False)
            return content, first_content_received
    return "", first_content_received


async def list_tools(json_output: bool = False):
    """
    List available MCP tools.

    Args:
        json_output: If True, output as JSON format
    """
    # Get server configurations
    server_configs = get_server_configs()

    if not server_configs:
        print_warning("No MCP servers configured yet (set MCP_*_URL env vars)")
        return

    # Get tools from all servers
    tool_list, client, results = await get_tools_from_servers(
        server_configs, verbose=True
    )

    # Print server status
    print_server_status(results)

    # Check if any servers connected successfully
    successful_servers = [name for name, success, _ in results if success]

    if not successful_servers:
        print_error("All MCP servers failed to connect. Check the errors above.")
        return

    # Clean up client connections
    await cleanup_client(client)

    if not tool_list:
        print_warning("No tools available from connected servers")
        return

    if json_output:
        import json as _json

        console.print_json(
            _json.dumps(
                [{"name": t.name, "description": t.description} for t in tool_list]
            )
        )
        return

    console.print(f"[bold]Available Tools ({len(tool_list)}):[/]\n")
    for t in tool_list:
        print_tool(t.name, t.description)


async def handle_chat_stream(session: Session, stream: bool = True) -> Optional[str]:
    """
    Handle a chat response from the agent (streaming or non-streaming).

    Args:
        session: The active session
        stream: If True, stream the response. If False, wait for full response.

    Returns:
        The complete response text, or None if error
    """
    start = time.time()

    if not stream:
        # Non-streaming mode: use ainvoke
        try:
            with console.status("[dim]Thinking...", spinner="dots"):
                result = await session.agent.ainvoke({"messages": session.thread})

            elapsed = time.time() - start

            # Check if any tools were used
            tools_used = []
            for msg in result.get("messages", []):
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        if tool_name not in tools_used:
                            tools_used.append(tool_name)

            # Get last message from result
            last_message = result.get("messages", [])[-1]

            # Extract text content
            content = last_message.content
            if isinstance(content, list):
                # Handle content blocks
                text = next(
                    (
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and "text" in block
                    ),
                    "",
                )
            else:
                text = content or ""

            # Print the response
            console.print(text)

            # Display stats
            print_response_stats(elapsed, tools_used if tools_used else None)

            return text

        except Exception as e:
            error_msg = f"Error: {e}"
            print_error(error_msg)
            return error_msg

    # Streaming mode
    full_response = ""
    tools_used = []
    first_content_received = False

    # Start spinner
    status = console.status("[dim]Thinking...", spinner="dots")
    status.start()

    try:
        # Stream the agent's response
        async for event in session.agent.astream_events(
            {"messages": session.thread}, version="v2"
        ):
            kind = event["event"]

            # Only process chat model stream events
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")

                # Handle tool calls
                first_content_received = _handle_tool_calls(
                    chunk, tools_used, status, first_content_received
                )

                # Handle content streaming
                content_text, first_content_received = _handle_content_chunk(
                    chunk, first_content_received, status
                )
                full_response += content_text

        elapsed = time.time() - start

        # stop spinner
        if not first_content_received:
            status.stop()

        # print newline after streaming
        console.print()

        # stats after response
        print_response_stats(elapsed, tools_used if tools_used else None)

        return full_response

    except Exception as e:
        # stop spinner on error
        if not first_content_received:
            status.stop()
        error_msg = f"Error: {e}"
        print_error(error_msg)
        return error_msg
