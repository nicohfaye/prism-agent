import asyncio
from contextlib import asynccontextmanager
import uuid

from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, HumanMessage

from .graph import build_agent
from .schemas import ChatRequest, ChatResponse, langchain_to_dict, threads

agent = None
mcp_client = None
threads_lock = asyncio.Lock()
MAX_MESSAGES = 20  # Keep last 20 messages to reduce token usage


def trim_messages(messages: list) -> list:
    """Trim message history to prevent excessive token usage."""
    if len(messages) > MAX_MESSAGES:
        return messages[-MAX_MESSAGES:]
    return messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    global agent, mcp_client

    # initialize agent and MCP client
    try:
        agent, mcp_client = await build_agent()
        print("Agent initialized successfully")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        raise

    yield

    # Shutdown: cleanup resources
    print("Shutting down...")
    if mcp_client:
        try:
            mcp_client.connections.clear()
            print("MCP client closed")
        except Exception as e:
            print(f"Warning: Error closing MCP client: {e}")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint."""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Check MCP client connection
    mcp_status = "connected" if mcp_client else "disconnected"

    return {
        "status": "healthy",
        "agent": "initialized",
        "mcp_client": mcp_status,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    global agent

    # Guard against agent not being initialized
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="Agent is still initializing. Please try again in a moment.",
        )

    tid = req.threadId or str(uuid.uuid4())

    # Thread-safe access to shared threads dict
    async with threads_lock:
        history = threads.get(tid, []).copy()

    try:
        history.append(HumanMessage(content=req.message))

        # Trim history to prevent excessive token usage
        history = trim_messages(history)

        result = await agent.ainvoke({"messages": history})

        # Get the last message from result
        last_message = result["messages"][-1]

        # Extract text content from the last message
        if isinstance(last_message.content, str):
            final = last_message.content
        else:
            # handle content blocks
            blocks = (
                last_message.content if isinstance(last_message.content, list) else []
            )
            final = next(
                (
                    b.get("text", "")
                    for b in blocks
                    if isinstance(b, dict) and "text" in b
                ),
                "",
            )

        history.append(AIMessage(content=final))

        async with threads_lock:
            threads[tid] = history

        client_messages = [langchain_to_dict(msg) for msg in history]
        return ChatResponse(threadId=tid, messages=client_messages, finalText=final)

    except Exception as e:
        # return error message as assistant response
        error_msg = f"Error processing request: {str(e)}"
        history.append(AIMessage(content=error_msg))

        async with threads_lock:
            threads[tid] = history

        client_messages = [langchain_to_dict(msg) for msg in history]
        return ChatResponse(threadId=tid, messages=client_messages, finalText=error_msg)
