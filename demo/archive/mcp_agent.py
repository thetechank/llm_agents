import asyncio
import os
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from mcp import StdioServerParameters

# --- Load environment ---
load_dotenv(override=True)

async def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ No API key found. Set OPENAI_API_KEY in .env")
    print("✅ API key found")

    # Launch MCP server as subprocess (unbuffered)
    server_params = {"command": "python", "args": ["-u", "mcp_server.py"]}

    # Use async context manager to connect
    async with MCPServerStdio(
        params=server_params,
        name="FlightAITools",
        client_session_timeout_seconds=120,
    ) as mcp:
        print("✅ Connected to MCP server")
        tools = [t.name for t in await mcp.list_tools()]
        print(f"🧰 Tools available: {tools}")

        # Create the agent
        agent = Agent(
            name="FlightAI",
            instructions="You are a helpful airline assistant. Use tools if needed.",
            mcp_servers=[mcp],
            model="gpt-4o-mini",
        )

        print("⚙️ Asking agent ...")
        result = await Runner.run(
            agent,
            "How much is the ticket price to Berlin and convert it to euros",
        )

        print("✅ Final output:", result.final_output)

asyncio.run(main())
