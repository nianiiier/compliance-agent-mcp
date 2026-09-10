from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SubmitComplianceResp(BaseModel):
    thread_id: str
    msg: str


class ThreadStateResp(BaseModel):
    thread_id: str
    is_interrupt: bool
    interrupt_info: Optional[Dict[str, Any]] = None
    state_values: Dict[str, Any]


class ComplianceFinalResp(BaseModel):
    thread_id: str
    report_markdown: Optional[str]
    risk_level: Optional[str]
    violation_points: List[str]


class UploadResp(BaseModel):
    ok: bool
    msg: str
    doc_id: Optional[str] = None
