from __future__ import annotations

from src.models.workflow_state import QAStatus, WorkflowState


def determine_next_step(current_step: str, state: WorkflowState) -> str:
    if current_step == "intake":
        return "planner"
    if current_step == "planner":
        if state.requires_approval and state.approval_granted is None:
            return "pause_for_approval"
        return "execution"
    if current_step == "execution":
        return "qa"
    if current_step == "qa":
        qa_status = state.qa_result.get("status")
        if qa_status == QAStatus.FAIL and state.retry_count < state.max_retries:
            return "execution"
        return "judge"
    if current_step == "judge":
        action = str(state.judge_result.get("action", "accept")).lower()
        if action == "retry" and state.retry_count < state.max_retries:
            return "execution"
        return "delivery"
    if current_step == "delivery":
        return "end"
    return "end"
