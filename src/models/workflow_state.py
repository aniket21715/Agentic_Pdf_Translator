from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class QAStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


class WorkflowState(BaseModel):
    """Shared state object across the full workflow."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    source_language: str = "en"
    target_language: str = "es"
    document_type: str = "legal"
    page_count: int = 1
    raw_text: str = ""

    status: WorkflowStatus = WorkflowStatus.PENDING
    run_status: str = "pending"
    current_agent: str | None = None
    execution_plan: list[str] = Field(default_factory=list)
    route_history: list[str] = Field(default_factory=list)
    step_status: dict[str, str] = Field(default_factory=dict)
    events: list[dict] = Field(default_factory=list)

    normalized_request: dict = Field(default_factory=dict)
    translation_output: str | None = None
    translation_method: str | None = None
    qa_result: dict = Field(default_factory=dict)
    judge_result: dict = Field(default_factory=dict)
    final_output: dict = Field(default_factory=dict)

    retry_count: int = 0
    max_retries: int = 1

    start_time: datetime | None = None
    end_time: datetime | None = None
    agent_timings: dict[str, float] = Field(default_factory=dict)

    parallel_execution: bool = False
    requested_real_llm: bool = False
    requires_approval: bool = False
    approval_granted: bool | None = None
    pause_reason: str | None = None

    quality_threshold: float = 75.0
    force_qa_fail_once: bool = False

    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def add_error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def add_warning(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def set_step_status(self, step: str, status: str) -> None:
        self.step_status[step] = status

    def add_event(self, event: dict) -> None:
        self.events.append(event)
