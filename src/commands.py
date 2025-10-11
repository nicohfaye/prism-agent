"""Command handlers for the CLI application."""

import time
from typing import Optional

from rich.console import Console

from .mcp_client import create_mcp_client
from .session import Session
from .ui import (
    print_error,
    print_response_stats,
    print_tool,
    print_tool_usage,
    print_warning,
    show_mcp_connection_error,
)

console = Console()


async def list_tools(json_output: bool = False):
    """
    List available MCP tools.

    Args:
        json_output: If True, output as JSON format
    """
    client = create_mcp_client()
    try:
        tool_list = await client.get_tools()
    except Exception as e:
        # Check if it's a connection error (including nested ExceptionGroups)
        error_str = str(e).lower()
        is_connection_error = (
            "connection" in error_str
            or "connect" in error_str
            or "taskgroup" in error_str  # ExceptionGroups from connection failures
        )

        if is_connection_error:
            show_mcp_connection_error()
        else:
            print_error(f"Failed to fetch tools: {e}")

        return
    finally:
        try:
            await client.connections.clear()
        except Exception:
            pass

    if not tool_list:
        print_warning("No MCP servers configured yet (set MCP_*_URL env vars)")
        return

    if json_output:
        import json as _json

        console.print_json(
            _json.dumps(
                [{"name": t.name, "description": t.description} for t in tool_list]
            )
        )
        return

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

    try:
        # Stream the agent's response
        async for event in session.agent.astream_events(
            {"messages": session.thread}, version="v2"
        ):
            kind = event["event"]

            # Track tool calls
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        tool_name = tool_call.get("name", "unknown")
                        if tool_name and tool_name not in tools_used:
                            tools_used.append(tool_name)
                            # show tool usage in real-time
                            print_tool_usage(tool_name)

            # Stream text content as it arrives
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        console.print(content, end="", markup=False)
                        full_response += content

        elapsed = time.time() - start

        # Print newline after streaming
        console.print()

        # Display stats after streaming completes
        print_response_stats(elapsed, tools_used if tools_used else None)

        return full_response

    except Exception as e:
        error_msg = f"Error: {e}"
        print_error(error_msg)
        return error_msg
