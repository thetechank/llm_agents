import os
from dotenv import load_dotenv
from IPython.display import Markdown, display, update_display
from openai import OpenAI
from agents import Agent, Runner, trace, function_tool
from typing import Dict
import asyncio
import gradio as gr
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
from mcp.types import TextContent
from agents.mcp import MCPServerStdio
# ruff: noqa: F70

load_dotenv(override=True)

force_dark_mode = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

async def main():

    api_key = os.getenv('OPENAI_API_KEY')

    # Check the key

    if not api_key:
        print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
    elif not api_key.startswith("sk-proj-"):
        print("An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
    elif api_key.strip() != api_key:
        print("An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
    else:
        print("API key found and looks good so far!")

    MODEL = "gpt-4o-mini"
    client = OpenAI()


    system_message = "You are a helpful assistant for an Airline called FlightAI. "
    system_message += "Give short, courteous answers, no more than 1 sentence. "
    system_message += "Always be accurate. If you don't know the answer, say so."

    # server_params = [{"command": "uv", "args":["run", "mcp_server.py"]}]
    # server_params = [{"command": "uv", "args":["run", "mcp_server.py"]}]
    # server_params = [{"command": "python", "args": ["mcp_server.py"]}]
    # server_params = [{"command": "uv", "args": ["run", "python", "-u", "mcp_server.py"]}]
    
    server_params = [{"command": "python", "args": ["-u", "mcp_server.py"]}]
    stack = AsyncExitStack()
    await stack.__aenter__()
    mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(
                        params=server_param,
                        name=f"stdio-{i}",
                        client_session_timeout_seconds=120,
                        # optional:
                        # cache_tools_list=True,
                        # use_structured_content=True,
                    )
                )
                for i, server_param in enumerate(server_params)
            ]
    print(mcp_servers)
    for s in mcp_servers:
        print(f"Connected to MCP server: {s.name}")
        print(f"Tools available: {[t.name for t in await s.list_tools()]}")

    
    print("Agent")
    agent = Agent(
        name="FlightAI",
        instructions=(
            system_message
        ),
        #tools=[get_ticket_price],
        mcp_servers=mcp_servers,
        model="gpt-4o-mini",
        )
    #result = await (Runner.run(agent, input="How much is the ticket price to Berlin. And convert it to Euros too, please."))
    #print(result.final_output)
            
    async def chat_mcp(message, history):
        print(history)
        print(message)
        items = [{"role":m.get("role"),"content":m.get("content")} for m in history if isinstance(m.get("content"), str)]
        items.append({"role": "user", "content": message})
        print(items)
        with trace("FlightAIMCPChat"):
            print("Call Agent")
            result = await Runner.run(agent, items)
            return result.final_output

    gr.ChatInterface(fn=chat_mcp, type="messages",js=force_dark_mode).launch()

    # await stack.aclose()

if __name__ == "__main__":
    print("Running") 
    asyncio.run(main())
