from fastapi import APIRouter
from backend_gateway.schemas.request_schema import HitlResumeRequest
from backend_gateway.schemas.response_schema import ComplianceFinalResp
from backend_gateway.clients.langgraph_client import resume_hitl_review

router = APIRouter(prefix="/hitl", tags=["人工复核HITL"])


@router.post("/resume", response_model=ComplianceFinalResp)
async def hitl_resume(req: HitlResumeRequest):
    """人工审批：恢复被interrupt挂起的Agent线程"""
    final_state = await resume_hitl_review(
        thread_id=req.thread_id,
        human_approval=req.human_approval
    )
    return ComplianceFinalResp(
        thread_id=req.thread_id,
        report_markdown=final_state.get("report_markdown"),
        risk_level=final_state.get("risk_level"),
        violation_points=final_state.get("violation_points", [])
    )
