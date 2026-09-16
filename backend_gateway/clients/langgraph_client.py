import asyncio
import uuid
from typing import Optional, Dict, Any
from agent_orchestrator.server import ComplianceAgentService

_agent_service: Optional[ComplianceAgentService] = None
_init_lock = asyncio.Lock()


async def get_agent_service() -> ComplianceAgentService:
    global _agent_service
    if _agent_service is None:
        async with _init_lock:
            if _agent_service is None:      # double-check
                svc = ComplianceAgentService()
                await svc.init()
                _agent_service = svc
    return _agent_service


async def shutdown_agent_service():
    """FastAPI shutdown 时调用，释放MCP连接"""
    global _agent_service
    if _agent_service is not None:
        await _agent_service.close()
        _agent_service = None


async def start_compliance_review(user_input: str) -> str:
    """发起合规审查，返回thread_id"""
    svc = await get_agent_service()
    thread_id = f"tg-{uuid.uuid4()}"
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
        "state_values": snapshot.values,
    }


async def resume_hitl_review(thread_id: str, human_approval: bool) -> Dict[str, Any]:
    """HITL人工审批恢复工作流"""
    svc = await get_agent_service()

    # ✅ 先校验线程是否真的处于中断状态，防止脏resume
    snapshot = await svc.get_thread_state(thread_id=thread_id)
    if not (snapshot.tasks and snapshot.tasks[0].interrupts):
        raise ValueError(f"线程 {thread_id} 当前不处于待人工复核状态")

    final_state = await svc.resume_review(
        thread_id=thread_id, human_approval=human_approval
    )
    return final_state
