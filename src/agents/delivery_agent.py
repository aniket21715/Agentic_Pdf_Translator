from __future__ import annotations

from datetime import datetime

from src.agents.base_agent import BaseWorkerAgent
from src.models.outputs import DeliveryOutput, JudgeReport, QAReport
from src.models.workflow_state import WorkflowState


class DeliveryAgent(BaseWorkerAgent):
    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Formatting final output")
        processing_time = 0.0
        if state.start_time:
            processing_time = ((state.end_time or datetime.utcnow()) - state.start_time).total_seconds()

        qa_report = QAReport(**state.qa_result)
        judge_report = JudgeReport(**state.judge_result) if state.judge_result else JudgeReport()
        output = DeliveryOutput(
            request_id=state.request_id,
            status=state.run_status or state.status.value,
            source_language=state.source_language,
            target_language=state.target_language,
            original_text=state.raw_text,
            translated_text=state.translation_output or "",
            qa_report=qa_report,
            judge_report=judge_report,
            metadata={
                "document_type": state.document_type,
                "page_count": state.page_count,
                "retry_count": state.retry_count,
                "processing_time_seconds": processing_time,
                "agent_timings": state.agent_timings,
                "route_history": state.route_history,
                "step_status": state.step_status,
                "events": state.events,
                "translation_method": state.translation_method,
                "warnings": state.warnings,
                "errors": state.errors,
            },
            timestamp=datetime.utcnow(),
        )
        return output.model_dump(mode="json")
