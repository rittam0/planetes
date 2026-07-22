"""MCP server exposing AstraScope tools to AI clients."""
import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from backend.agents.tools import GetObjectTool, GetConjunctionsTool, ExplainEncounterTool

# Initialize tools
get_object_tool = GetObjectTool()
get_conjunctions_tool = GetConjunctionsTool()
explain_encounter_tool = ExplainEncounterTool()

# MCP server instance
server = Server("astra-scope")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_space_object",
            description="Retrieve orbital data for a satellite or debris object by NORAD ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "norad_id": {
                        "type": "string",
                        "description": "NORAD catalog ID of the object"
                    }
                },
                "required": ["norad_id"]
            }
        ),
        Tool(
            name="list_conjunctions",
            description="Retrieve upcoming close-approach events for an object",
            inputSchema={
                "type": "object",
                "properties": {
                    "norad_id": {
                        "type": "string",
                        "description": "NORAD catalog ID of the primary object"
                    }
                },
                "required": ["norad_id"]
            }
        ),
        Tool(
            name="explain_encounter",
            description="Get a structured explanation of a conjunction encounter",
            inputSchema={
                "type": "object",
                "properties": {
                    "primary_norad": {
                        "type": "string",
                        "description": "NORAD ID of primary object"
                    },
                    "secondary_norad": {
                        "type": "string",
                        "description": "NORAD ID of secondary object"
                    }
                },
                "required": ["primary_norad", "secondary_norad"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute a tool call."""
    if name == "search_space_object":
        result = get_object_tool._run(arguments["norad_id"])
        return [TextContent(type="text", text=result)]

    elif name == "list_conjunctions":
        result = get_conjunctions_tool._run(arguments["norad_id"])
        return [TextContent(type="text", text=result)]

    elif name == "explain_encounter":
        result = explain_encounter_tool._run(
            arguments["primary_norad"],
            arguments["secondary_norad"]
        )
        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
