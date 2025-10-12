"""Session management for the chat agent."""

from typing import List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from rich.console import Console

from .graph import build_agent
from .mcp_utils import cleanup_client

console = Console()


class Session:
    """Manages agent state and conversation history."""

    def __init__(self, max_messages: int = 20):
        self.thread: List[BaseMessage] = []
        self.agent = None
        self.mcp_client = None
        self.max_messages = max_messages

    async def init(self):
        """Initialize the agent and MCP client."""
        if not self.agent:
            self.agent, self.mcp_client = await build_agent()

    def add_user_message(self, content: str):
        """Add a user message to the conversation history."""
        self.thread.append(HumanMessage(content=content))

    def add_ai_message(self, content: str):
        """Add an AI message to the conversation history."""
        self.thread.append(AIMessage(content=content))

    def clear_history(self):
        """Clear all conversation history."""
        self.thread = []

    def get_message_count(self) -> int:
        """Get the current number of messages in history."""
        return len(self.thread)

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

        await cleanup_client(self.mcp_client)

        if self.mcp_client:
            console.print("[dim]Cleaned up resources and cleared message history[/]")
        else:
            console.print("[dim]Cleared message history[/]")
