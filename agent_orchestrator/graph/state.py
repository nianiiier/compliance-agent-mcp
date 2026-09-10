from typing import Optional, List
from pydantic import BaseModel

class ComplianceAgentState(BaseModel):
    user_input: str
    compliance_clauses: List[dict]
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    violation_points: List[str]
    report_markdown: Optional[str] = None
    human_approval: Optional[bool] = None

    class Config:
        extra = "forbid"
