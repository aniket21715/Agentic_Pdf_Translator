from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.workflow_state import QAStatus


class QAReport(BaseModel):
    status: QAStatus
    quality_score: float
    checks: dict = Field(default_factory=dict)
    failed_checks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class JudgeReport(BaseModel):
    score: float = 0.0
    checks: dict = Field(default_factory=dict)
    rationale: str = ""
    action: str = "accept"


class DeliveryOutput(BaseModel):
    request_id: str
    status: str
    source_language: str
    target_language: str
    original_text: str
    translated_text: str
    qa_report: QAReport
    judge_report: JudgeReport = Field(default_factory=JudgeReport)
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
