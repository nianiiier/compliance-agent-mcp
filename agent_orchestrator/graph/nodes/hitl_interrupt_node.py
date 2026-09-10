"""
HITL人工复核中断节点
当前langgraph版本：Command不支持interrupt参数；使用独立interrupt()函数
恢复执行时，从interrupt()语句的下一行继续运行
"""
from langgraph.types import Command, interrupt

async def hitl_interrupt_node(state):
    risk_level = state.risk_level
    if risk_level == "高":
        interrupt_payload = {
            "reason": "检测到高合规风险，需要人工复核审批",
            "risk_level": risk_level,
            "violation_points": state.violation_points
        }
        # 触发中断暂停；恢复时从这行之后继续执行
        interrupt(interrupt_payload)
        # --------恢复之后代码从这里继续往下执行--------
        return Command(goto="resume_input_node")

    # 非高风险直接流向报告节点
    return Command(goto="report_node")
