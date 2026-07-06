"""
Centralized MCP session manager for Google Workspace and Stripe MCP servers.
Each call spawns a short-lived stdio session — no leaked connections.
"""
import os
import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def get_resolved_creds_path() -> str:
    """Resolve the GOOGLE_OAUTH_CREDENTIALS path relative to the backend folder."""
    creds_path = os.getenv("GOOGLE_OAUTH_CREDENTIALS", "credentials.json")
    resolved_path = Path(creds_path)
    if not resolved_path.is_absolute():
        # Resolve relative to backend/ directory (parent of app/)
        backend_dir = Path(__file__).resolve().parent.parent
        resolved_path = backend_dir / creds_path
        if not resolved_path.exists() and creds_path == "credentials.json":
            resolved_path = backend_dir / "credentials.json"
    return str(resolved_path.resolve())



async def call_google_workspace_tool(tool_name: str, arguments: dict) -> str:
    """Connect to @alanxchen/google-workspace-mcp and call a tool."""
    creds_path = get_resolved_creds_path()
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@alanxchen/google-workspace-mcp"],
        env={
            **os.environ,
            "GOOGLE_OAUTH_CREDENTIALS": creds_path,
            "NODE_NO_WARNINGS": "1",
        },
    )
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                # Extract text content from MCP result
                if result.content:
                    parts = [
                        c.text for c in result.content if hasattr(c, "text")
                    ]
                    return "\n".join(parts) if parts else str(result.content)
                return "No results returned."
    except Exception as e:
        return f"Google Workspace MCP error: {str(e)}"


async def call_stripe_tool(tool_name: str, arguments: dict) -> str:
    """Connect to @stripe/mcp and call a tool."""
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key or stripe_key.startswith("sk_test_your"):
        return "Stripe is not configured. Please set STRIPE_SECRET_KEY in .env"

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@stripe/mcp", f"--api-key={stripe_key}"],
        env={**os.environ},
    )
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                if result.content:
                    parts = [
                        c.text for c in result.content if hasattr(c, "text")
                    ]
                    return "\n".join(parts) if parts else str(result.content)
                return "No results returned."
    except Exception as e:
        return f"Stripe MCP error: {str(e)}"


async def list_mcp_tools(server: str) -> list[str]:
    """Debug helper: list available tools on a given MCP server."""
    if server == "google":
        creds_path = get_resolved_creds_path()
        params = StdioServerParameters(
            command="npx",
            args=["-y", "@alanxchen/google-workspace-mcp"],
            env={**os.environ, "GOOGLE_OAUTH_CREDENTIALS": creds_path, "NODE_NO_WARNINGS": "1"},
        )
    elif server == "stripe":
        stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
        params = StdioServerParameters(
            command="npx",
            args=["-y", "@stripe/mcp", f"--api-key={stripe_key}"],
            env={**os.environ},
        )
    else:
        return [f"Unknown server: {server}"]

    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [t.name for t in tools.tools]
    except Exception as e:
        return [f"Error listing tools: {str(e)}"]
