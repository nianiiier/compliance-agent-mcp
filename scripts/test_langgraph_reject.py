import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
import asyncio
import os
from dotenv import load_dotenv
from agent_orchestrator.mcp_client.mcp_tool_client import create_mcp_mock_client
from agent_orchestrator.graph.state import ComplianceAgentState
from agent_orchestrator.graph.build_graph import build_agent_graph
from langgraph.types import Command

load_dotenv()


async def main():
    thread_id = "test-reject-001"
    config = {"configurable": {"thread_id": thread_id}}

    async with create_mcp_mock_client() as mcp_client:
        graph = build_agent_graph(mcp_client)

        init_state = ComplianceAgentState(
            user_input="企业虚开发票用于增值税进项抵扣",
            compliance_clauses=[],
            violation_points=[]
        )
        await graph.ainvoke(init_state, config=config)
        print("=====挂起=====")

        # ✅ resume False，验证驳回分支
        final_result = await graph.ainvoke(
            input=Command(resume=False),
            config=config
        )
        print("\n===== 驳回后 final state =====")
        print(f"human_approval: {final_result.get('human_approval')}")
        print(f"report_markdown: {final_result.get('report_markdown')}")
        assert final_result.get("report_markdown") is None, "❌ 驳回却生成了报告！"
        assert final_result.get("human_approval") is False
        print("\n✅ 驳回分支正确：无报告，直接 END")


if __name__ == "__main__":
    asyncio.run(main())