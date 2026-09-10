import sys
import os
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server/main.py", "--transport", "stdio"],
        env=os.environ.copy()
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # 调用检索工具
            ret_ret = await session.call_tool(
                "retrieve_compliance",
                arguments={"query": "增值税进项抵扣条件", "top_k": 3}
            )
            data = json.loads(ret_ret.content[0].text)
            # 输出原始json，stdout输出
            print(json.dumps(data, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
