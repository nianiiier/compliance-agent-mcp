from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent_orchestrator.graph.state import ComplianceAgentState
from agent_orchestrator.graph.nodes.retrieval_node import retrieval_node
from agent_orchestrator.graph.nodes.review_node import review_node
from agent_orchestrator.graph.nodes.hitl_interrupt_node import hitl_interrupt_node
from agent_orchestrator.graph.nodes.report_node import report_node
from agent_orchestrator.graph.edges import check_after_hitl


def build_agent_graph(mcp_client):
    """
    构建合规审查Agent graph
    注意：MCP SSE连接在graph外层提前建立完成后传入，graph内部不创建连接，防止泄漏
    工作流：检索 → 审查 → HITL中断判断 →（resume恢复后）报告生成
    """
    graph_builder = StateGraph(ComplianceAgentState)

    # 包装节点注入mcp_client依赖
    async def wrapped_retrieval(state):
        return await retrieval_node(state, mcp_client)

    graph_builder.add_node("retrieval_node", wrapped_retrieval)
    graph_builder.add_node("review_node", review_node)
    graph_builder.add_node("hitl_interrupt_node", hitl_interrupt_node)
    graph_builder.add_node("report_node", report_node)

    # 固定流水线边
    graph_builder.set_entry_point("retrieval_node")
    graph_builder.add_edge("retrieval_node", "review_node")
    graph_builder.add_edge("review_node", "hitl_interrupt_node")

    # HITL节点出来走条件边
    graph_builder.add_conditional_edges(
        "hitl_interrupt_node",
        check_after_hitl,
        {
            "to_report": "report_node",
            "rejected": END,      # 驳回 → 结束
            "end_flow": END
        }
    )
    graph_builder.add_edge("report_node", END)

    # ✅增加内存检查点，支持interrupt、aget_state、resume
    memory_checkpointer = MemorySaver()
    compiled_graph = graph_builder.compile(checkpointer=memory_checkpointer)
    return compiled_graph
