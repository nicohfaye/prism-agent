"""CLI interface for the Prism AI agent."""

import asyncio

from rich.console import Console
import typer

from .commands import handle_chat_stream, list_tools
from .session import Session
from .ui import print_startup_banner

app = typer.Typer(add_completion=False)
console = Console()

# global session instance
session = Session(max_messages=20)


@app.command()
def tools(json: bool = typer.Option(False, "--json", help="Output as JSON")):
    """List available MCP tools."""
    asyncio.run(list_tools(json))


@app.command()
def chat(
    stream: bool = typer.Option(
        True, "--stream/--no-stream", help="Enable streaming responses"
    ),
):
    """Interactive chat REPL with tool-calling."""
    try:
        asyncio.run(_chat_async(stream))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/]")
    except Exception as e:
        console.print(f"[red bold]Error:[/] {e}")
        import traceback

        console.print("[dim]" + traceback.format_exc() + "[/]")
        raise typer.Exit(code=1)


async def _chat_async(stream: bool = True):
    """Async implementation of the chat REPL."""

    print_startup_banner()

    try:
        console.print("[dim]Initializing agent...[/]")
        await session.init()
        console.print("[bold green]Agent initialized successfully![/]")
    except ValueError as e:
        # handle config errors (missing api keys etc...)
        console.print(f"[red bold]Configuration Error:[/] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red bold]Failed to initialize agent:[/] {e}")
        raise typer.Exit(code=1)

    mode = "streaming" if stream else "non-streaming"
    console.print(
        f"[bold green]Agent ready ({mode})[/] \nType \n - [bold]:q[/] to quit, \n - [bold]:tools[/] to list tools, \n - [bold]:reset[/] to clear history, \n - [bold]:stats[/] for message count, \n - [bold]:clear[/] to clear screen."
    )

    try:
        while True:
            user = console.input("[bold blue]you> [/] ").strip()
            if not user:
                continue
            if user in {":q", ":quit", ":exit"}:
                break
            if user == ":tools":
                await list_tools()
                continue
            if user == ":reset":
                session.clear_history()
                console.print("[dim]history cleared[/]")
                continue
            if user == ":clear":
                console.clear()
                continue
            if user == ":stats":
                console.print(
                    f"[dim]Current messages in context: {session.get_message_count()} (max: {session.max_messages})[/]"
                )
                continue

            session.add_user_message(user)

            # prevent excessive token usage
            session.trim_messages()

            # stream the response
            text = await handle_chat_stream(session, stream=stream)

            # Add AI response to history
            if text:
                session.add_ai_message(text)

    finally:
        await session.cleanup()


if __name__ == "__main__":
    app()
