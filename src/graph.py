import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .mcp_client import get_server_configs
from .mcp_utils import cleanup_client, get_tools_from_servers

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
        streaming=True,
    )

    # Get server configurations and check connectivity
    server_configs = get_server_configs()

    if not server_configs:
        print(
            "\n⚠️  No MCP servers configured. Set MCP_*_URL or MCP_*_ENABLED env vars."
        )
        print("   The agent will continue without MCP tools.\n")
        return create_react_agent(model, []), None

    # Get tools from all servers
    tools, client, results = await get_tools_from_servers(server_configs, verbose=True)

    # Get successful and failed servers
    successful_servers = [name for name, success, _ in results if success]
    failed_servers = [(name, msg) for name, success, msg in results if not success]

    # Print summary
    if successful_servers and tools:
        print(
            f"Successfully loaded {len(tools)} tools from {len(successful_servers)} server(s): {', '.join(successful_servers)}"
        )

    if failed_servers:
        print(f"\n⚠️  WARNING: {len(failed_servers)} server(s) failed to connect:")
        for name, msg in failed_servers:
            print(f"   • {name}: {msg}")
        if "context7" in [name for name, _ in failed_servers]:
            print("   Tip: Start Context7 with: docker-compose up -d")
        print()

    if not tools:
        print("⚠️  No tools available. The agent will continue without MCP tools.\n")
        await cleanup_client(client)
        client = None

    # minimal langgraph reAct agent
    agent = create_react_agent(
        model,
        tools,
    )

    return agent, client
