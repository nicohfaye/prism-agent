import os

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .mcp_client import create_mcp_client

load_dotenv()

# system prompt?
system_prompt = """You are a snarky assistant. Be brief and end with: "If that's all, I'll retire.\""""


async def build_agent():
    """
    Build the agent and return both agent and MCP client.

    The client must be kept alive and properly closed when done.

    Returns:
        tuple: (agent, mcp_client)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required but not set. "
            "Please set it before starting the agent."
        )

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,  # more deterministic
        api_key=api_key,
        timeout=45,
        max_retries=2,
        streaming=True,  # Enable streaming for faster perceived response
    )

    client: MultiServerMCPClient = create_mcp_client()

    # Try to get tools, but handle connection failures gracefully
    try:
        tools = await client.get_tools()
        if tools:
            print(f"Successfully loaded {len(tools)} tools from MCP servers")
        else:
            print("No tools available from MCP servers")
    except Exception as e:
        # check if connection errors
        error_str = str(e).lower()
        is_connection_error = (
            "connection" in error_str
            or "connect" in error_str
            or "taskgroup" in error_str  # ExceptionGroups from connection failures
        )

        if is_connection_error:
            print("\n⚠️  WARNING: Could not connect to MCP servers.")
            print("   Make sure Docker containers are running: docker-compose up -d")
            print("   The agent will continue without MCP tools.\n")
        else:
            print(f"\n⚠️  WARNING: Error loading MCP tools: {e}")
            print("   The agent will continue without MCP tools.\n")

        # Continue without tools
        tools = []

        try:
            await client.connections.clear()
        except Exception:
            pass
        client = None

    # minimal langgraph reAct agent
    agent = create_react_agent(
        model,
        tools,
    )

    return agent, client
