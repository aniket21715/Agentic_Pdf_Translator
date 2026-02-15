from __future__ import annotations

from src.agents.base_agent import BaseWorkerAgent
from src.models.workflow_state import QAStatus, WorkflowState


class QAAgent(BaseWorkerAgent):
    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Running QA checks")
        checks = {
            "length_check": self._check_length(state),
            "format_check": self._check_format(state),
            "terminology_check": self._check_terminology(state),
        }

        failed_checks = [name for name, result in checks.items() if not result["passed"]]
        warning_checks = [name for name, result in checks.items() if result.get("warning", False)]
        if state.force_qa_fail_once and state.retry_count == 0:
            failed_checks.append("forced_failure")
            checks["forced_failure"] = {"passed": False, "message": "Intentional first-pass failure"}

        quality_score = self._calculate_score(checks)
        status = QAStatus.PASS if not failed_checks and quality_score >= state.quality_threshold else QAStatus.FAIL
        return {
            "status": status,
            "checks": checks,
            "failed_checks": failed_checks,
            "warnings": warning_checks,
            "quality_score": quality_score,
            "recommendations": self._generate_recommendations(failed_checks, warning_checks),
        }

    def _check_length(self, state: WorkflowState) -> dict:
        if not state.translation_output:
            return {"passed": False, "ratio": 0.0, "message": "Translation is empty"}
        original_words = max(1, len(state.raw_text.split()))
        translated_words = len(state.translation_output.split())
        ratio = translated_words / original_words
        passed = 0.65 <= ratio <= 1.6
        return {"passed": passed, "ratio": ratio, "message": "Length check"}

    def _check_format(self, state: WorkflowState) -> dict:
        original_lines = state.raw_text.count("\n")
        translated_lines = (state.translation_output or "").count("\n")
        line_diff = abs(original_lines - translated_lines)
        # For long documents, strict absolute line matching creates false failures.
        dynamic_tolerance = max(4, int(max(1, original_lines) * 0.35))
        passed = line_diff <= dynamic_tolerance
        return {
            "passed": passed,
            "line_diff": line_diff,
            "tolerance": dynamic_tolerance,
            "message": "Format check",
        }

    def _check_terminology(self, state: WorkflowState) -> dict:
        if state.document_type.lower() != "legal":
            return {"passed": True, "message": "Terminology check skipped"}
        legal_terms = ["agreement", "contract", "party", "clause", "liability"]
        found = sum(1 for term in legal_terms if term in state.raw_text.lower())
        if found == 0:
            return {
                "passed": True,
                "warning": True,
                "terms_found": found,
                "message": "No known legal terms found. Treated as warning only.",
            }
        return {
            "passed": True,
            "warning": False,
            "terms_found": found,
            "message": "Legal terminology detected.",
        }



    def _calculate_score(self, checks: dict) -> float:
        total = len(checks)
        if total == 0:
            return 0.0
        passed = sum(1 for result in checks.values() if result["passed"])
        return (passed / total) * 100

    def _generate_recommendations(self, failed_checks: list[str], warning_checks: list[str]) -> list[str]:
        recommendations: list[str] = []
        if "length_check" in failed_checks:
            recommendations.append("Review translation length for missing or extra content.")
        if "format_check" in failed_checks:
            recommendations.append("Restore line/section formatting.")
        if "terminology_check" in failed_checks:
            recommendations.append("Validate domain terminology consistency.")
        if "terminology_check" in warning_checks:
            recommendations.append("Setting Document type to non-legal is recommended for non-legal documents.")
        if "forced_failure" in failed_checks:
            recommendations.append("Retry triggered as part of QA safety drill.")
        if not recommendations and failed_checks:
            recommendations.append("Perform manual reviewer spot-check.")
        return recommendations
