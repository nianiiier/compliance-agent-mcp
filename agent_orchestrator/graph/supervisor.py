"""
轻量化Supervisor，本项目业务是固定流水线，不做复杂动态路由
流水线顺序：检索 → 审查 → HITL人工判断 → 报告
"""

def supervisor_route(state):
    """
    本项目固定流水线，graph build层直接硬编码边；
    预留此文件，后续扩展复杂多分支业务时使用
    """
    raise NotImplementedError("当前版本使用固定顺序边，supervisor暂未启用，预留扩展")
