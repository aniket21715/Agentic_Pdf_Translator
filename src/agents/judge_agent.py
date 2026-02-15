from __future__ import annotations

import re

from src.agents.base_agent import BaseWorkerAgent
from src.models.workflow_state import WorkflowState


class JudgeAgent(BaseWorkerAgent):
    """
    Translation judge that scores output fidelity/quality and recommends action.
    """

    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Running translation judge checks")
        source = state.raw_text or ""
        translated = state.translation_output or ""

        checks = {
            "non_empty_translation": self._check_non_empty(translated),
            "length_ratio": self._check_length_ratio(source, translated),
            "number_integrity": self._check_number_integrity(source, translated),
            "line_structure": self._check_line_structure(source, translated),
            "lexical_shift": self._check_lexical_shift(source, translated, state.source_language, state.target_language),
        }

        score = round(sum(check["score"] for check in checks.values()) / len(checks), 2)
        action = "accept"
        rationale = "Translation is acceptable."

        qa_failed_checks = state.qa_result.get("failed_checks", []) if state.qa_result else []
        if qa_failed_checks:
            action = "human_review"
            rationale = "QA reported failed checks: " + ", ".join(qa_failed_checks)
            return {
                "action": action,
                "score": score,
                "checks": checks,
                "rationale": rationale,
            }

        if score < 60:
            action = "retry"
            rationale = "Low translation quality score. Retry recommended."
        elif score < 80:
            action = "human_review"
            rationale = "Translation quality is borderline. Human review recommended."

        return {
            "action": action,
            "score": score,
            "checks": checks,
            "rationale": rationale,
        }

    def _check_non_empty(self, translated: str) -> dict:
        ok = bool(translated.strip())
        return {"passed": ok, "score": 100.0 if ok else 0.0, "message": "Non-empty translation"}

    def _check_length_ratio(self, source: str, translated: str) -> dict:
        source_words = max(1, len(source.split()))
        translated_words = len(translated.split())
        ratio = translated_words / source_words
        passed = 0.65 <= ratio <= 1.8
        score = 100.0 if passed else 40.0
        return {"passed": passed, "score": score, "ratio": ratio, "message": "Length ratio"}

    def _check_number_integrity(self, source: str, translated: str) -> dict:
        src_nums = re.findall(r"\d+(?:\.\d+)?", source)
        dst_nums = re.findall(r"\d+(?:\.\d+)?", translated)
        if not src_nums:
            return {"passed": True, "score": 100.0, "message": "No source numerics to compare"}
        overlap = sum(1 for n in src_nums if n in dst_nums)
        coverage = overlap / len(src_nums)
        passed = coverage >= 0.9
        score = round(coverage * 100, 2)
        return {
            "passed": passed,
            "score": score,
            "coverage": coverage,
            "source_numbers": len(src_nums),
            "matched_numbers": overlap,
            "message": "Numeric integrity",
        }

    def _check_line_structure(self, source: str, translated: str) -> dict:
        src_lines = source.count("\n")
        dst_lines = translated.count("\n")
        diff = abs(src_lines - dst_lines)
        passed = diff <= 4
        score = 100.0 if passed else max(35.0, 100.0 - (diff * 10))
        return {"passed": passed, "score": score, "line_diff": diff, "message": "Line structure preservation"}

    def _check_lexical_shift(self, source: str, translated: str, source_lang: str, target_lang: str) -> dict:
        src_tokens = set(token.lower() for token in re.findall(r"[A-Za-z]{3,}", source))
        dst_tokens = set(token.lower() for token in re.findall(r"[A-Za-z]{3,}", translated))
        if not src_tokens:
            return {"passed": True, "score": 100.0, "message": "Lexical shift skipped"}

        overlap_ratio = len(src_tokens.intersection(dst_tokens)) / len(src_tokens)
        # For same-language translation overlap can be high; only enforce this strongly when languages differ.
        threshold = 0.8 if source_lang.lower() == target_lang.lower() else 0.55
        passed = overlap_ratio <= threshold
        score = round(max(20.0, 100.0 - (overlap_ratio * 100.0)), 2)
        return {
            "passed": passed,
            "score": score,
            "overlap_ratio": overlap_ratio,
            "message": "Lexical shift between source and translation",
        }
