import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
import asyncio
from dotenv import load_dotenv
from agent_orchestrator.mcp_client.mcp_tool_client import create_mcp_sse_client
from agent_orchestrator.graph.state import ComplianceAgentState
from agent_orchestrator.graph.build_graph import build_agent_graph
from langgraph.types import Command

load_dotenv()


async def main():
    thread_id = "e2e-real-001"
    config = {"configurable": {"thread_id": thread_id}}

    # ✅ 用真实 SSE 客户端
    async with create_mcp_sse_client(host="127.0.0.1", port=8005) as mcp_client:
        graph = build_agent_graph(mcp_client)

        init_state = ComplianceAgentState(
            user_input="企业虚开发票用于增值税进项抵扣",
            compliance_clauses=[],
            violation_points=[]
        )
        print("===== 发起真实审查 =====")
        await graph.ainvoke(init_state, config=config)

        snapshot = await graph.aget_state(config=config)
        is_interrupt = bool(snapshot.tasks and snapshot.tasks[0].interrupts)
        print(f"\n是否中断: {is_interrupt}")
        if is_interrupt:
            print(f"中断payload: {snapshot.tasks[0].interrupts[0].value}")
        print(f"检索到的法规条款数: {len(snapshot.values.get('compliance_clauses', []))}")
        print(f"风险等级: {snapshot.values.get('risk_level')}")

        if is_interrupt:
            print("\n===== 人工审批通过，resume =====")
            final = await graph.ainvoke(
                input=Command(resume=True),
                config=config
            )
            print(f"\nreport_markdown 前200字:\n{str(final.get('report_markdown'))[:200]}")


if __name__ == "__main__":
    asyncio.run(main())