"""
条件边判断逻辑
"""
def check_after_hitl(state):
    """
    HITL中断恢复后条件判断：必须human_approval不为None才允许流向报告节点
    """
    if state.human_approval is not None:
        return "to_report"
    return "end_flow"
