import sys
import asyncio
from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP("FlightAI Demo")


ticket_prices = {"london": "$799", "paris": "$899", "tokyo": "$1400", "berlin": "$499"}

## Tool to get the ticket price in USD

@mcp_server.tool()
async def get_ticket_price(destination_city: str) -> str:
    """Get the price of a return ticket to the destination city. 
    Call this whenever you need to know the ticket price, for example when a customer
    asks 'How much is a ticket to this city'
    """
    print(f"Tool get_ticket_price called for {destination_city}")
    city = destination_city.lower()
    return ticket_prices.get(city, "Unknown")

def _parse_usd(price_usd: str) -> float:
    s = (price_usd or "").strip()
    s = s.replace("$", "").replace(",", "")
    return float(s)

## Tool to convert a price in USD to EUR

@mcp_server.tool()
async def convert_usd_to_eur(price_usd: str, rate: float = 0.92) -> str:
    """
    Convert a USD price like "$499" to EUR using the provided USD->EUR rate.
    Returns a string like "€459.08".
    """
    try:
        usd = _parse_usd(price_usd)
        eur = usd * rate
        return f"€{eur:0.2f}"
    except Exception:
        return "Unknown"

if __name__ == "__main__":
    print("MCP Server is running") 
    mcp_server.run(transport='stdio')