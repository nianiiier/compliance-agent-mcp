"""
条件边判断逻辑
"""
def check_after_hitl(state):
    """
    HITL中断恢复后条件判断：
      - True  → 生成报告
      - False → 驳回，直接结束（不生成报告）
      - None  → 未经过HITL节点（异常兜底），结束
    """
    if state.human_approval is True:
        return "to_report"
    if state.human_approval is False:
        return "rejected"
    return "end_flow"