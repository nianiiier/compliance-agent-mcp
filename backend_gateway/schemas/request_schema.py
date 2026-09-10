from pydantic import BaseModel, Field
from typing import Optional


class SubmitComplianceRequest(BaseModel):
    """发起合规审查请求"""
    user_input: str = Field(description="待审查业务文本")


class HitlResumeRequest(BaseModel):
    """HITL人工复核恢复请求"""
    thread_id: str = Field(description="会话线程ID")
    human_approval: bool = Field(description="人工审批结果 True=通过 False=驳回")


class UploadFileRequest(BaseModel):
    pass
