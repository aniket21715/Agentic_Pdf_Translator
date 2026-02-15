from __future__ import annotations

from src.agents.base_agent import BaseWorkerAgent
from src.models.workflow_state import WorkflowState


class IntakeAgent(BaseWorkerAgent):
    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Parsing and validating request")
        errors = self._validate_request(state)
        if errors:
            raise ValueError("; ".join(errors))

        word_count = len(state.raw_text.split())
        metadata = {
            "source_language": state.source_language.lower().strip(),
            "target_language": state.target_language.lower().strip(),
            "document_type": state.document_type.lower().strip(),
            "page_count": state.page_count,
            "word_count": word_count,
            "estimated_complexity": self._estimate_complexity(word_count, state.page_count),
        }
        return metadata

    def _validate_request(self, state: WorkflowState) -> list[str]:
        errors: list[str] = []
        if not state.raw_text.strip():
            errors.append("raw_text is required")
        if state.source_language.lower().strip() == state.target_language.lower().strip():
            errors.append("source and target language must differ")
        if state.page_count < 1:
            errors.append("page_count must be >= 1")
        return errors

    def _estimate_complexity(self, word_count: int, page_count: int) -> str:
        if page_count > 10 or word_count > 4000:
            return "high"
        if page_count > 3 or word_count > 1200:
            return "medium"
        return "low"
