"""
MCP stdio子进程客户端
不直接import mcp_server内部函数，通过MCP协议调用独立子进程
"""
import asyncio
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
MCP_SCRIPT_PATH = str(PROJECT_ROOT / "mcp_server" / "main.py")


class McpStdioClient:
    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._read = None
        self._write = None
        self._ctx = None

    async def connect(self):
        """拉起MCP为子进程，建立MCP stdio会话"""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", MCP_SCRIPT_PATH, "--transport", "stdio"],
            env=None
        )
        self._ctx = stdio_client(server_params)
        self._read, self._write = await self._ctx.__aenter__()
        self._session = ClientSession(self._read, self._write)
        await self._session.initialize()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._session is None:
            raise RuntimeError("MCP未connect，请先调用connect()")
        resp = await self._session.call_tool(tool_name, arguments)
        import json
        return json.loads(resp.content[0].text)

    async def close(self):
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)


async def demo():
    client = McpStdioClient()
    await client.connect()
    try:
        res = await client.call_tool("retrieve_compliance", {"query": "增值税进项抵扣条件", "top_k": 3})
        print("✅MCP调用结果：")
        print(res)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(demo())
