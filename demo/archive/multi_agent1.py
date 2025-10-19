import asyncio
import gradio as gr
from agents import Agent, Runner, function_tool
from agents import input_guardrail, GuardrailFunctionOutput, InputGuardrailTripwireTriggered
from dotenv import load_dotenv
import os
# ----------------------------------------------------
# Function tools (MCP-style)
# ----------------------------------------------------

load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("❌ No API key found. Set OPENAI_API_KEY in .env")
print("✅ API key found")

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

# Convert to a tool using the built-in method
weather_agent_tool = weather_agent.as_tool(
    tool_name="weather_agent_tool",
    tool_description="Agent to get the weather of a city",
)

# ----------------------------------------------------
# Booking agent (Handoff target)
# ----------------------------------------------------
booking_agent = Agent(
    name="booking_agent",
    model="gpt-4o-mini",
    instructions="""
    You are a polite booking assistant. When handed off, confirm booking details clearly with all details received
    """,
)

# ----------------------------------------------------
# Guardrail: blocks “refund” or “complaint” in user message
# ----------------------------------------------------
@input_guardrail
async def block_refund_or_complaint_guardrail(ctx, agent, message) -> GuardrailFunctionOutput:
    """If the user mentions refund or complaint, trigger guardrail and stop the flow."""
    text = message.lower() if isinstance(message, str) else str(message)
    trigger = ("refund" in text) or ("complaint" in text)
    print(f"🛡️ Guardrail check: {'triggered' if trigger else 'passed'} for message='{message}'")
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
    instructions="""
    You are a friendly travel assistant.
    - Use get_ticket_price to fetch ticket cost.
    - Use convert_usd_to_eur for currency conversion.
    - Use weather_agent tool for weather queries.
    If user confirms “book”, handoff to booking_agent with all details of price and weather
    """,
    tools=[get_ticket_price, convert_usd_to_eur, weather_agent_tool],
    handoffs=[booking_agent],
    input_guardrails=[block_refund_or_complaint_guardrail],
)

# ----------------------------------------------------
# Runner and chat logic
# ----------------------------------------------------
runner = Runner()

async def chat_fn(message, history):
    """
    Main Chat Function
    """
    items = [{"role": msg["role"], "content": msg["content"]} for msg in history]
    items.append({"role": "user", "content": message})

    print(f"\n🟢 User: {message}")

    try:
        # Run the main agent (guardrail automatically enforced)
        #result = await runner.run(main_agent, [{"role": "user", "content": message}])
        result = await runner.run(main_agent,items)
    except InputGuardrailTripwireTriggered:
        # Stop execution immediately when guardrail trips
        print("🚨 Guardrail triggered! Stopping flow immediately.")
        return "⚠️ Sorry, I can’t continue this conversation due to content policy."

    print(f"📨 Main Agent: {result.final_output}")
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
