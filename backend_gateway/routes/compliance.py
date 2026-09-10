from fastapi import APIRouter
from backend_gateway.schemas.request_schema import SubmitComplianceRequest
from backend_gateway.schemas.response_schema import SubmitComplianceResp, ThreadStateResp
from backend_gateway.clients.langgraph_client import start_compliance_review, get_thread_status

router = APIRouter(prefix="/compliance", tags=["合规审查"])


@router.post("/submit", response_model=SubmitComplianceResp)
async def submit_review(req: SubmitComplianceRequest):
    """提交待审查文本，启动Agent工作流"""
    thread_id = await start_compliance_review(user_input=req.user_input)
    return SubmitComplianceResp(thread_id=thread_id, msg="审查任务已提交")


@router.get("/thread/{thread_id}/status", response_model=ThreadStateResp)
async def query_thread_status(thread_id: str):
    """查询线程状态，判断是否HITL中断挂起"""
    data = await get_thread_status(thread_id)
    return ThreadStateResp(**data)
