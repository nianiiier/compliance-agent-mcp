import uuid
from typing import Optional, Dict, Any
from agent_orchestrator.server import ComplianceAgentService

# 模式现在统一在 agent_orchestrator/server.py 内部 MCP_TRANSPORT 控制
_agent_service: Optional[ComplianceAgentService] = None


async def get_agent_service() -> ComplianceAgentService:
    global _agent_service
    if _agent_service is None:
        svc = ComplianceAgentService()   # ✅不再传入host port
        await svc.init()
        _agent_service = svc
    return _agent_service


async def start_compliance_review(user_input: str) -> str:
    """发起合规审查，返回thread_id"""
    svc = await get_agent_service()
    thread_id = f"tg‑{uuid.uuid4()}"
    await svc.invoke_review(user_input=user_input, thread_id=thread_id)
    return thread_id


async def get_thread_status(thread_id: str) -> Dict[str, Any]:
    """获取线程快照状态"""
    svc = await get_agent_service()
    snapshot = await svc.get_thread_state(thread_id=thread_id)
    is_interrupt = bool(snapshot.tasks and snapshot.tasks[0].interrupts)
    interrupt_info = snapshot.tasks[0].interrupts[0].value if is_interrupt else None
    return {
        "thread_id": thread_id,
        "is_interrupt": is_interrupt,
        "interrupt_info": interrupt_info,
        "state_values": snapshot.values
    }


async def resume_hitl_review(thread_id: str, human_approval: bool) -> Dict[str, Any]:
    """HITL人工审批恢复工作流"""
    svc = await get_agent_service()
    final_state = await svc.resume_review(thread_id=thread_id, human_approval=human_approval)
    return final_state
