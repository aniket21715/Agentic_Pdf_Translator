from __future__ import annotations

from src.agents.base_agent import BaseWorkerAgent
from src.models.workflow_state import WorkflowState


class PlannerAgent(BaseWorkerAgent):
    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Building execution plan")
        metadata = state.normalized_request
        word_count = int(metadata.get("word_count", len(state.raw_text.split())))
        complexity = metadata.get("estimated_complexity", "low")

        plan = ["normalize_content"]
        if state.parallel_execution or word_count > 500:
            plan.append("translate_chunks_parallel")
        else:
            plan.append("translate_single_pass")
        plan += ["run_quality_checks", "format_output"]

        estimated_seconds = self._estimate_duration(word_count, complexity)
        requires_approval = estimated_seconds > 60 or state.page_count > 15
        approval_reason = (
            "Estimated runtime exceeds approval threshold."
            if requires_approval
            else None
        )
        return {
            "plan": plan,
            "estimated_duration_seconds": estimated_seconds,
            "requires_approval": requires_approval,
            "approval_reason": approval_reason,
        }

    def _estimate_duration(self, word_count: int, complexity: str) -> int:
        base = max(5, word_count // 25)
        multiplier = {"low": 1.0, "medium": 1.5, "high": 2.0}.get(complexity, 1.0)
        return int(base * multiplier)
