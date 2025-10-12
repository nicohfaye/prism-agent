"""UI utilities and formatting helpers for the CLI."""

from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_startup_banner():
    """Print a cool ASCII art banner when starting the agent."""
    banner = r"""
    ____  ____  ____  _____ __  ___        ___    ____
   / __ \/ __ \/  _/ / ___//  |/  /       /   |  /  _/
  / /_/ / /_/ // /   \__ \/ /|_/ /       / /| |  / /  
 / ____/ _, _// /   ___/ / /  / /       / ___ |_/ /   
/_/   /_/ |_/___/  /____/_/  /_/       /_/  |_/___/   
    """

    # Create a colorful text object
    text = Text(banner, style="bold cyan")

    # Wrap in a panel
    panel = Panel(
        text,
        title="[bold magenta]Prism Agent[/bold magenta]",
        subtitle="[dim]github.com/nicohfaye[/dim]",
        border_style="cyan",
        padding=(0, 2),
    )

    console.print(panel)
    console.print()


def format_tool_description(description: str) -> str:
    """
    Extract a concise one-line description from a tool's full description.

    Args:
        description: The full tool description

    Returns:
        A short, one-line description
    """
    # Split by newline first, then by period
    first_line = description.split("\n")[0].strip()
    short_desc = first_line.split(". ")[0].strip()
    if not short_desc.endswith("."):
        short_desc += "."
    return short_desc


def print_tool(name: str, description: str):
    """Print a formatted tool entry."""
    short_desc = format_tool_description(description)
    console.print(f"[yellow]•[/] [bold yellow]{name}[/] — {short_desc}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[red bold]Error:[/] {message}")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow bold]⚠️  {message}[/]")


def print_info(message: str, dim: bool = True):
    """Print an informational message."""
    if dim:
        console.print(f"[dim]{message}[/]")
    else:
        console.print(message)


def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]{message}[/]")


def print_tool_usage(tool_name: str):
    """Print a real-time tool usage notification."""
    console.print(f"[dim]🔧 Using tool: [cyan]{tool_name}[/cyan][/]")


def print_response_stats(elapsed: float, tools_used: List[str] = None):
    """Print response time and tool usage statistics."""
    if tools_used:
        tools_str = ", ".join(tools_used)
        console.print(
            f"[dim]Response time: {elapsed:.2f}s | Tools used: [cyan]{tools_str}[/cyan][/]"
        )
    else:
        console.print(f"[dim]Response time: {elapsed:.2f}s[/]")
