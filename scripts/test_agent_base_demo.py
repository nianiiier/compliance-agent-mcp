import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import logging
from mcp.client.sse import sse_client
from agent_orchestrator.mcp_client.mcp_tool_client import MCPToolClient
from agent_orchestrator.graph.state import ComplianceAgentState

logging.basicConfig(level=logging.INFO)

async def main():
    # ✅ 前置：另一个终端已启动 MCP SSE server
    url = "http://127.0.0.1:8005/sse"
    async with sse_client(url) as (read, write):
        client = MCPToolClient(read_stream=read, write_stream=write)
        await client.connect()
        try:
            tools = await client.list_tools()
            print(f"\n✅可用MCP工具：{[t.name for t in tools]}")

            ret_result = await client.call_tool(
                "retrieve_compliance",
                arguments={"query": "增值税进项抵扣条件", "top_k": 3}
            )
            print("\n====MCP返回结果====")
            print(ret_result)

            if ret_result.get("ok"):
                clauses = ret_result.get("clauses", [])
                state = ComplianceAgentState(
                    user_input="请审查增值税进项抵扣相关合规风险",
                    compliance_clauses=clauses,
                    violation_points=[]
                )
                print("\n✅成功填充ComplianceAgentState")
                print(state.model_dump_json(indent=2))
            else:
                print(f"\n❌MCP调用失败 {ret_result.get('msg')}")
        finally:
            await client.close()

if __name__ == "__main__":
    asyncio.run(main())
