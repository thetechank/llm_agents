import asyncio
import gradio as gr
from openai import OpenAI
from agents import Agent, Runner, function_tool, trace
from openai import guardrails

# ----------------------------------------------------
# Define simple function tools
# ----------------------------------------------------
@function_tool
def get_ticket_price(city: str):
    """Return a hardcoded flight price."""
    prices = {"berlin": 499, "paris": 450, "amsterdam": 380}
    return f"The ticket price to {city.title()} is ${prices.get(city.lower(), 500)}."


@function_tool
def usd_to_eur(amount: float):
    """Convert USD to EUR (fixed rate for demo)."""
    return f"{amount} USD is approximately {amount * 0.93:.2f} EUR."


# ----------------------------------------------------
# Define weather agent (used as a TOOL)
# ----------------------------------------------------
weather_agent = Agent(
    name="weather_agent",
    model="gpt-4o-mini",
    instructions="""
    You are a weather assistant. 
    You return short, cheerful weather updates for a given city.
    """,
)


@function_tool
def get_weather(city: str):
    """Tool that delegates to weather_agent"""
    print("🌦️ [Weather Agent called]")
    # run the weather agent as a sub-agent
    runner = Runner()
    result = asyncio.run(runner.run(weather_agent, [{"role": "user", "content": f"What is the weather in {city}?"}]))
    return result.final_output


# ----------------------------------------------------
# Define booking agent (handoff target)
# ----------------------------------------------------
booking_agent = Agent(
    name="booking_agent",
    model="gpt-4o-mini",
    instructions="""
    You are a booking agent. 
    When handed off, confirm booking politely with details.
    """,
)


# ----------------------------------------------------
# Define main agent (has tools, weather agent, and handoff)
# ----------------------------------------------------
main_agent = Agent(
    name="travel_assistant",
    model="gpt-4o",
    instructions="""
    You are a friendly travel assistant.
    You can provide ticket prices, convert currency, or tell weather via the weather agent tool.
    If user confirms to book, handoff to booking_agent.
    """,
    tools=[get_ticket_price, usd_to_eur, get_weather],
    handoffs=[booking_agent],
)

# ----------------------------------------------------
# Add Guardrails (using OpenAI SDK)
# ----------------------------------------------------
# Guardrails prevent unsafe / irrelevant requests
travel_guardrail = guardrails.Guardrail.from_preset("sensitive")
# You can also use other presets like: "harmful_content", "sensitive", "profanity"

# ----------------------------------------------------
# Runner
# ----------------------------------------------------
runner = Runner()

async def chat_fn(message, history):
    print(f"\n🟢 User: {message}")

    # Guardrail enforcement
    check = await travel_guardrail.validate_input(message)
    if not check.valid:
        print("🚨 Guardrail triggered: ", check.failure_reason)
        return "⚠️ Sorry, I can’t answer that question."

    # Normal flow
    if "book" in message.lower():
        print("✈️ Handoff → Booking Agent")
        result = await runner.run(booking_agent, [{"role": "user", "content": message}])
        print(f"📨 Booking Agent: {result.final_output}")
        return result.final_output

    print("🤖 Main Agent processing...")
    result = await runner.run(main_agent, [{"role": "user", "content": message}])
    print(f"📨 Main Agent: {result.final_output}")
    return result.final_output


# ----------------------------------------------------
# Gradio Chat Interface
# ----------------------------------------------------
demo = gr.ChatInterface(
    chat_fn,
    title="🌍 FlightAI Multi-Agent Demo (Simple)",
    description="""
    Demonstrates:
    - One main agent using tools & guardrails  
    - Weather agent as a tool  
    - Booking agent via handoff  
    - Guardrails using OpenAI SDK  
    - Logged flow in console
    """,
)

if __name__ == "__main__":
    print("🚀 Starting simple multi-agent demo...")
    asyncio.run(demo.launch())
