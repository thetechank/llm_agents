import os
import asyncio
from dotenv import load_dotenv
import gradio as gr
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from contextlib import asynccontextmanager

load_dotenv(override=True)

class FlightAIDemo:
    """Simple wrapper to manage MCP server lifecycle"""
    
    def __init__(self):
        self.agent = None
        self.mcp_server = None
        self.initialized = False
    
    async def initialize(self):
        """Setup the agent with MCP server"""
        if self.initialized:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("❌ No API key found. Set OPENAI_API_KEY in .env")
        print("✅ API key found")

        system_message = (
            "You are a helpful assistant for an Airline called FlightAI. "
            "Give short, courteous answers, no more than 1 sentence. "
            "Always be accurate. If you don't know the answer, say so."
        )

        # Connect to MCP server
        server_params = {"command": "python", "args": ["-u", "mcp_server.py"]}
        self.mcp_server = MCPServerStdio(
            params=server_params,
            name="stdio-0",
            client_session_timeout_seconds=120,
        )
        await self.mcp_server.__aenter__()
        
        print("✅ Connected to MCP server")
        tools = [t.name for t in await self.mcp_server.list_tools()]
        print(f"🧰 Tools available: {tools}")

        # Create the agent
        self.agent = Agent(
            name="FlightAI",
            instructions=system_message,
            mcp_servers=[self.mcp_server],
            model="gpt-4o-mini"
        )
        print("✅ Agent initialized!")
        self.initialized = True
    
    async def chat(self, message, history):
        """Handle chat messages"""
        if not self.initialized:
            await self.initialize()
        
        # Format conversation history
        items = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in history
        ]
        items.append({"role": "user", "content": message})
        
        print(f"💬 User: {message}")
        
        try:
            # Run the agent
            result = await Runner.run(self.agent, items)
            print(f"✅ Response: {result.final_output}")
            return result.final_output
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_server:
            await self.mcp_server.__aexit__(None, None, None)
            print("✅ MCP server disconnected")

# Create global instance
demo_app = FlightAIDemo()

async def chat_wrapper(message, history):
    """Wrapper for Gradio"""
    return await demo_app.chat(message, history)

def main():
    """Main function"""
    print("🚀 Starting FlightAI Demo...")
    
    # Launch Gradio - it handles async automatically
    demo = gr.ChatInterface(
        fn=chat_wrapper,
        type="messages",
        title="✈️ FlightAI Assistant"
    )
    
    demo.launch()

if __name__ == "__main__":
    main()