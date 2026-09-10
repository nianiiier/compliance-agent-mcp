import sys
import os
from pathlib import Path

# Windows stdio管道兼容补丁
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import logging
from mcp.client.stdio import stdio_client, StdioServerParameters
from agent_orchestrator.mcp_client.mcp_tool_client import MCPToolClient
from agent_orchestrator.graph.state import ComplianceAgentState

logging.basicConfig(level=logging.INFO)

async def main():
    # 【关键】stdio_client放在脚本最外层，复用阶段1已经验证稳定的写法
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server/main.py", "--transport", "stdio"],
        env=os.environ.copy()
    )
    async with stdio_client(server_params) as (read, write):
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
