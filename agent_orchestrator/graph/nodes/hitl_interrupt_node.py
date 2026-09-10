"""
HITL人工复核中断节点
官方标准用法：interrupt()的返回值就是人工审批输入
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
        # ✅ 接收恢复时传入的人工审批值；第一次运行在这里暂停抛异常；恢复后approved拿到外部传入的值
        approved = interrupt(interrupt_payload)
        # 将人工审批结果写入state更新
        return {
            "human_approval": approved
        }
    # 非高风险，直接允许流向报告
    return {
        "human_approval": True
    }
