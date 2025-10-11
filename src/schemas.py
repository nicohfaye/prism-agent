from typing import Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    threadId: str | None = None


class MessageDict(BaseModel):
    """Simplified message format for API responses."""

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'tool'")
    content: str = Field(..., description="Message text content")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    threadId: str
    messages: List[MessageDict]
    finalText: str


threads: Dict[str, List[BaseMessage]] = {}


def langchain_to_dict(msg: BaseMessage) -> MessageDict:
    """Convert LangChain message to simple dict for API response."""
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = "tool"

    content = msg.content
    if isinstance(content, list):
        # handle content blocks (like from Claude/multi-modal responses)
        text = next(
            (
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and "text" in block
            ),
            "",
        )
    else:
        text = str(content) if content else ""

    return MessageDict(role=role, content=text)
