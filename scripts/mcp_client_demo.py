import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx2
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect ShiftMate's MCP tools")
    parser.add_argument("--http", help="Streamable HTTP URL, such as /mcp/")
    parser.add_argument("--tool", help="Optionally call one read-only tool")
    parser.add_argument(
        "--arguments",
        default="{}",
        help="JSON object passed to --tool (default: {})",
    )
    return parser.parse_args()


async def inspect(client: Client, tool: str | None, payload: dict[str, Any]) -> None:
    listed = await client.list_tools()
    print("Available tools:")
    for item in listed.tools:
        print(f"- {item.name}")
    if tool:
        result = await client.call_tool(tool, payload)
        print(json.dumps(result.structured_content, ensure_ascii=False, indent=2))


async def run() -> None:
    args = arguments()
    payload = json.loads(args.arguments)
    if not isinstance(payload, dict):
        raise SystemExit("--arguments must be a JSON object")
    token = os.environ.get("SHIFTMATE_MCP_ACCESS_TOKEN")
    if not token:
        raise SystemExit("SHIFTMATE_MCP_ACCESS_TOKEN is required")

    if args.http:
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}
        ) as http_client:
            transport = streamable_http_client(args.http, http_client=http_client)
            async with Client(transport) as client:
                await inspect(client, args.tool, payload)
        return

    server = StdioServerParameters(
        command=str(PROJECT_ROOT / ".venv" / "bin" / "python"),
        args=["-m", "backend.app.mcp.server"],
        cwd=PROJECT_ROOT,
        env=dict(os.environ),
    )
    async with Client(server) as client:
        await inspect(client, args.tool, payload)


if __name__ == "__main__":
    asyncio.run(run())
