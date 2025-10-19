from mcp.server.fastmcp import FastMCP
import sys

# --- Unbuffered output to avoid hangs ---
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

mcp_server = FastMCP("FlightAI Demo")

ticket_prices = {"london": "$799", "paris": "$899", "tokyo": "$1400", "berlin": "$499"}

@mcp_server.tool()
async def get_ticket_price(destination_city: str) -> str:
    city = destination_city.lower()
    price = ticket_prices.get(city, "Unknown")
    print(f"[Tool] get_ticket_price({destination_city}) -> {price}", flush=True)
    return price

def _parse_usd(price_usd: str) -> float:
    s = (price_usd or "").strip().replace("$", "").replace(",", "")
    return float(s)

@mcp_server.tool()
async def convert_usd_to_eur(price_usd: str, rate: float = 0.92) -> str:
    try:
        usd = _parse_usd(price_usd)
        eur = usd * rate
        result = f"€{eur:0.2f}"
    except Exception:
        result = "Unknown"
    print(f"[Tool] convert_usd_to_eur({price_usd}) -> {result}", flush=True)
    return result


if __name__ == "__main__":
    print("✅ MCP Server running (stdio mode, flushing enabled)", flush=True)
    try:
        mcp_server.run(transport="stdio")
    except KeyboardInterrupt:
        print("🛑 MCP Server stopped", flush=True)
