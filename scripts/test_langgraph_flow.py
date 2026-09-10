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
    thread_id = "test‑001"
    config = {"configurable": {"thread_id": thread_id}}

    async with create_mcp_mock_client() as mcp_client:
        graph = build_agent_graph(mcp_client)
        print("=====【场景：高风险输入，触发HITL interrupt中断】=====")
        init_state = ComplianceAgentState(
            user_input="企业虚开发票用于增值税进项抵扣",
            compliance_clauses=[],
            violation_points=[]
        )
        # 第一次执行，走到interrupt挂起
        await graph.ainvoke(init_state, config=config)

        # -----拿到快照之后-----
        snapshot = await graph.aget_state(config=config)
        print("\n✅线程挂起，快照信息：")
        print(f"中断原因: {snapshot.tasks[0].interrupts[0].value}")
        print("state快照：")
        print(snapshot.values)

        print("\n===== 模拟外部系统传入人工审批：human_approval=True，恢复执行 =====")
        # ✅恢复必须传入 Command(resume=xxx)，不能普通dict！
        final_result = await graph.ainvoke(
            input=Command(resume=True),
            config=config
        )



        print("\n===== 执行完成最终state =====")
        print(final_result)
        print("\n=====生成Markdown报告=====")
        print(final_result.get("report_markdown"))

if __name__ == "__main__":
    asyncio.run(main())
