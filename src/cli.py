import asyncio
import os
from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from rich.console import Console
from rich.markdown import Markdown
import typer

from .graph import build_agent
from .mcp_client import create_mcp_client

app = typer.Typer(add_completion=False)
console = Console()


class Session:
    def __init__(self):
        self.thread: List[BaseMessage] = []
        self.agent = None
        self.mcp_client = None
        self.max_messages = 20  # Keep last 20 messages (10 exchanges)

    async def init(self):
        if not self.agent:
            self.agent, self.mcp_client = await build_agent()

    def trim_messages(self):
        """Keep only recent messages to reduce token usage."""
        if len(self.thread) > self.max_messages:
            # Keep the most recent messages
            self.thread = self.thread[-self.max_messages :]
            console.print(
                f"[dim]Trimmed message history to last {self.max_messages} messages[/]"
            )

    async def cleanup(self):
        """Close MCP client connections and reset session for next use."""
        # Clear message history for fresh start next time
        self.thread = []

        if self.mcp_client:
            try:
                self.mcp_client.connections.clear()
                console.print(
                    "[dim]Cleaned up resources and cleared message history[/]"
                )
            except Exception as e:
                console.print(f"[dim]Warning: Error during cleanup: {e}[/]")
        else:
            console.print("[dim]Cleared message history[/]")


session = Session()


@app.command()
def tools(json: bool = typer.Option(False, "--json", help="Output as JSON")):
    """List available MCP tools."""
    asyncio.run(_list_tools_async(json))


async def _list_tools_async(json: bool = False):
    """Async implementation of tools listing."""
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
            console.print("\n[yellow bold]⚠️  Cannot connect to MCP servers[/]")
            console.print("\n[dim]Make sure Docker containers are running:[/]")
            console.print("  [cyan]docker-compose up -d[/]\n")

            # Show configured servers
            hints = [
                f"{k}={v}"
                for k, v in os.environ.items()
                if k.startswith("MCP_")
                and k.endswith("_URL")  # a bit scary to list from .env xD
            ]
            if hints:
                console.print("[dim]Configured servers:[/]")
                for h in hints:
                    console.print(f"  • [dim]{h}[/]")
            console.print()
        else:
            console.print(f"[red]Failed to fetch tools:[/] {e}")

        return
    finally:
        try:
            await client.connections.clear()
        except Exception:
            pass

    if not tool_list:
        console.print(
            "[bold yellow]No MCP servers configured yet[/] (set MCP_*_URL env vars)"
        )
        return

    if json:
        import json as _json

        console.print_json(
            _json.dumps(
                [{"name": t.name, "description": t.description} for t in tool_list]
            )
        )
        return

    for t in tool_list:
        # Use only the first line/sentence for a concise overview
        # Split by newline first, then by period
        first_line = t.description.split("\n")[0].strip()
        short_desc = first_line.split(". ")[0].strip()
        if not short_desc.endswith("."):
            short_desc += "."
        console.print(f"[yellow]•[/] [bold yellow]{t.name}[/] — {short_desc}")


@app.command()
def chat():
    """Interactive chat REPL with tool-calling."""
    try:
        asyncio.run(_chat_async())
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/]")
    except Exception as e:
        console.print(f"[red bold]Error:[/] {e}")
        import traceback

        console.print("[dim]" + traceback.format_exc() + "[/]")
        raise typer.Exit(code=1)


async def _chat_async():
    """Async implementation of the chat REPL."""
    try:
        console.print("[dim]Initializing agent...[/]")
        await session.init()
        console.print("[bold green]Agent initialized successfully![/]")
    except ValueError as e:
        # Handle configuration errors (like missing API keys)
        console.print(f"[red bold]Configuration Error:[/] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red bold]Failed to initialize agent:[/] {e}")
        raise typer.Exit(code=1)

    console.print(
        "[bold green]Agent ready.[/] Type :q to quit, :tools to list tools, :reset to clear history, :stats for message count."
    )

    try:
        while True:
            user = console.input("[bold blue]you> [/] ").strip()
            if not user:
                continue
            if user in {":q", ":quit", ":exit"}:
                break
            if user == ":tools":
                await _list_tools_async()
                continue
            if user == ":reset":
                session.thread = []
                console.print("[dim]history cleared[/]")
                continue
            if user == ":stats":
                console.print(
                    f"[dim]Current messages in context: {len(session.thread)} (max: {session.max_messages})[/]"
                )
                continue

            # Add user message using LangChain's HumanMessage
            session.thread.append(HumanMessage(content=user))

            # Trim message history to prevent excessive token usage
            session.trim_messages()

            try:
                import time

                start = time.time()

                # Langsmith tracing can be disabled through env variables.
                result = await session.agent.ainvoke({"messages": session.thread})

                elapsed = time.time() - start
                console.print(f"[dim]Response time: {elapsed:.2f}s[/]")

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

            except Exception as e:
                text = f"Error: {e}"

            # Add AI response to history
            session.thread.append(AIMessage(content=text))
            console.print(Markdown(text or "_(no text returned)_"))

    finally:
        # Always cleanup, even if interrupted
        await session.cleanup()


if __name__ == "__main__":
    app()
