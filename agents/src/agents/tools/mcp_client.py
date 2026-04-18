import os
import asyncio
from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client

class MCPHousingClient:
    """Wraps the MCP server connection for housing research."""
    
    def __init__(self, server_url: str = None):
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8001/sse")
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool with the given name and arguments."""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result.content[0].text if result.content else None

    async def search_houses(self, **kwargs) -> Any:
        return await self.call_tool("search_houses", kwargs)

    async def get_valuation_data(self, **kwargs) -> Any:
        return await self.call_tool("get_valuation_data", kwargs)

    async def get_neighborhood_snapshot(self, **kwargs) -> Any:
        return await self.call_tool("get_neighborhood_snapshot", kwargs)

    async def get_mortgage_rates(self, **kwargs) -> Any:
        return await self.call_tool("get_mortgage_rates", kwargs)

    async def calculate_roi(self, **kwargs) -> Any:
        return await self.call_tool("calculate_roi", kwargs)

    async def get_market_snapshot(self, **kwargs) -> Any:
        return await self.call_tool("get_market_snapshot", kwargs)
