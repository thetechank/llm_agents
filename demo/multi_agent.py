import os
import secrets
import string
#import asyncio
import gradio as gr
from agents import Agent, Runner, function_tool, handoff, RunContextWrapper
from agents import input_guardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered, trace
from agents import SQLiteSession
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from dotenv import load_dotenv

ALPHANUM = string.ascii_lowercase + string.digits

def make_trace_id(tag: str) -> str:
    """
    Return a string of the form 'trace_<tag><random>',
    where the total length after 'trace_' is 32 chars.
    """
    tag += "0"
    pad_len = 32 - len(tag)
    random_suffix = ''.join(secrets.choice(ALPHANUM) for _ in range(pad_len))
    return f"trace_{tag}{random_suffix}"

# ----------------------------------------------------
# Function tools (MCP-style)
# ----------------------------------------------------

load_dotenv(override=True)

# We wil not use our old way of adding history to the message.

# Session to store conversation history
# we are using SQLite session here, but you can use InMemorySession or any other session
# For production, you can use a persistent session like SQLiteSession
session = SQLiteSession("FlightAI-123")

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ No API key found. Set OPENAI_API_KEY in .env")
print("✅ API key found")

## Functions that Agent will use as tool
@function_tool
def get_ticket_price(destination_city: str) -> str:
    """Return the price of a round-trip ticket to the destination city."""
    ticket_prices = {"london": "$799", "paris": "$899", "tokyo": "$1400", "berlin": "$499"}
    print(f"🧰 Tool get_ticket_price called for {destination_city}")
    city = destination_city.lower()
    return ticket_prices.get(city, "Unknown")


def _parse_usd(price_usd: str) -> float:
    s = (price_usd or "").strip().replace("$", "").replace(",", "")
    return float(s)


@function_tool
def convert_usd_to_eur(price_usd: str, rate: float = 0.92) -> str:
    """Convert a USD price like '$499' to EUR."""
    print(f"🧮 Tool convert_usd_to_eur called for {price_usd}")
    try:
        usd = _parse_usd(price_usd)
        eur = usd * rate
        return f"€{eur:0.2f}"
    except Exception:
        return "Unknown"


@function_tool
def get_weather(city: str) -> str:
    """Return a simple hardcoded weather report."""
    print(f"🌦️ Tool from 📨 Weather Agent get_weather called for {city}")
    weather_data = {
        "london": "Cloudy with light showers, around 15°C.",
        "paris": "Sunny, around 22°C.",
        "tokyo": "Rainy, around 18°C.",
        "berlin": "Partly cloudy, around 19°C.",
    }
    return weather_data.get(city.lower(), "Weather data not available.")


# ----------------------------------------------------
# Weather agent (Agent used as Tool)
# ----------------------------------------------------
weather_agent = Agent(
    name="weather_agent",
    model="gpt-4o-mini",
    instructions="""
    You are a cheerful weather assistant. Use the get_weather tool to answer questions about the weather.
    """,
    tools=[get_weather],
)

# Convert to a tool using the built-in method. This is OPENAI Sdk way, but every SDK has its own way
weather_agent_tool = weather_agent.as_tool(
    tool_name="weather_agent_tool",
    tool_description="Agent to get the weather of a city",
)

# ----------------------------------------------------
# Booking agent (Handoff target)
# Handoff Means that the agent is now handing over the conversation to another agent and that agent will respond
# ----------------------------------------------------
def on_handoff(ctx: RunContextWrapper[None]):
    print("🔁 Handoff called")
    print("📨Further Message is handled by Booking Agent")

booking_agent = Agent(
    name="booking_agent",
    model="gpt-4o-mini",
    instructions="""
    You are a polite booking assistant. When handed off, reply back that the booking is confirmed with all details that include City, Price and Weather
    """,
    handoff_description="This Agent Books the flight and responds with a confirmation and detais"
)

# Open AI SDK way of creating handoff. Can be different in other SDKs
booking_agent_handoff = handoff(
    agent=booking_agent,
    on_handoff=on_handoff
    #tool_name_override="custom_handoff_tool",
    #tool_description_override="Custom description",
)

# ----------------------------------------------------
# Guardrail: blocks “refund” or “complaint” in user message
# ----------------------------------------------------
@input_guardrail
async def block_refund_or_complaint_guardrail(ctx, agent, message) -> GuardrailFunctionOutput:
    """If the user mentions refund or complaint, trigger guardrail and stop the flow."""
    text = message.lower() if isinstance(message, str) else str(message)
    trigger = ("refund" in text) or ("complaint" in text)
    print(f"🛡️ Guardrail check: {'❌ triggered' if trigger else '✅ passed'} for message='{message}'")
    return GuardrailFunctionOutput(
        output_info={"text": message, "triggered": trigger},
        tripwire_triggered=trigger,
    )

# ----------------------------------------------------
# Main agent
# ----------------------------------------------------
main_agent = Agent(
    name="travel_assistant",
    model="gpt-4o",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a friendly travel assistant.
    - Use get_ticket_price to fetch ticket cost.
    - Use convert_usd_to_eur for currency conversion.
    - Use weather_agent tool for weather queries.
    If user asks to book, handoff to booking_agent and do not reply. Let the booking agent reply with confirmation.
    """,
    tools=[get_ticket_price, convert_usd_to_eur, weather_agent_tool],
    handoffs=[booking_agent_handoff],
    input_guardrails=[block_refund_or_complaint_guardrail],
)

# ----------------------------------------------------
# Runner and chat logic
# ----------------------------------------------------
runner = Runner()

async def chat_fn(message, history):
    """
    Main Chat Function with grouped tracing using 'with trace'.
    """
    #items = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    #items.append({"role": "user", "content": message})
    print(f"\n🟢 User: {message}")

    trace_name = "FlightAI-MultiAgentSystem"
    # Start a single trace context for the entire conversation turn
    with trace(trace_name, trace_id = make_trace_id(trace_name), group_id="Flight1"):
        try:
            # Run the main agent (guardrail automatically enforced)
            # result = await runner.run(main_agent, items +  [{"role": "user", "content": message}])
            result = await runner.run(main_agent, message, session=session)
        except InputGuardrailTripwireTriggered:
            print("🚨 ❌ Guardrail triggered! Stopping flow immediately.")
            
            await session.pop_item()

            return "⚠️ Sorry, I can’t continue this conversation due to content policy."

        return result.final_output

# ----------------------------------------------------
# Gradio Interface
# ----------------------------------------------------
demo = gr.ChatInterface(
    chat_fn,
    title="🌍 FlightAI Demo with Guardrail",
    type="messages",
    description="""
    Demonstrates:
    - Input guardrail blocking “refund” or “complaint”  
    - Main agent with two function tools and one agent-as-tool  
    - Handoff to booking agent  
    - Logged flow in console
    """,
)

if __name__ == "__main__":
    print("🚀 Starting FlightAI Demo with Guardrail...")
    demo.launch()
