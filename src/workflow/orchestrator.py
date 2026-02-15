from __future__ import annotations

import asyncio
from typing import Any

from src.agents.delivery_agent import DeliveryAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.intake_agent import IntakeAgent
from src.agents.judge_agent import JudgeAgent
from src.agents.master_agent import MasterAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.qa_agent import QAAgent
from src.config.settings import get_settings
from src.models.workflow_state import WorkflowState, WorkflowStatus
from src.utils.logger import setup_logger


class WorkflowOrchestrator:
    def __init__(self, use_real_llm: bool | None = None) -> None:
        settings = get_settings()
        self.logger = setup_logger("orchestrator")
        self.init_warnings: list[str] = []
        if use_real_llm is None:
            use_real_llm = settings.use_real_llm
        self.use_real_llm = bool(use_real_llm)

        llm = self._initialize_llm(self.use_real_llm, settings.google_api_key, settings.gemini_model)
        direct_gemini_key = settings.google_api_key if self.use_real_llm else None
        self.workers = {
            "intake": IntakeAgent("intake"),
            "planner": PlannerAgent("planner"),
            "execution": ExecutionAgent(
                "execution",
                llm=llm,
                google_api_key=direct_gemini_key,
                gemini_model=settings.gemini_model,
            ),
            "qa": QAAgent("qa"),
            "judge": JudgeAgent("judge"),
            "delivery": DeliveryAgent("delivery"),
        }
        self.master = MasterAgent(worker_agents=self.workers, sla_seconds=settings.sla_seconds)

    async def execute_workflow(
        self,
        request: dict[str, Any],
        auto_approve: bool = True,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        request_payload = dict(request)
        request_payload["requested_real_llm"] = self.use_real_llm
        if self.init_warnings:
            request_payload.setdefault("warnings", [])
            request_payload["warnings"].extend(self.init_warnings)
        final_state = await self.master.orchestrate(
            request_payload,
            auto_approve=auto_approve,
            progress_callback=progress_callback,
        )
        return self._to_response(final_state)

    def execute_workflow_sync(
        self,
        request: dict[str, Any],
        auto_approve: bool = True,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(
            self.execute_workflow(
                request,
                auto_approve=auto_approve,
                progress_callback=progress_callback,
            )
        )

    def _initialize_llm(self, use_real: bool, api_key: str | None, model_name: str) -> Any | None:
        if not use_real:
            return None
        if not api_key:
            message = "USE_REAL_LLM enabled but GOOGLE_API_KEY missing. Falling back to mock translation."
            self.logger.warning(message)
            self.init_warnings.append(message)
            return None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=0.2,
                google_api_key=api_key,
            )
        except Exception:
            # Silent fallback to direct Gemini SDK path in ExecutionAgent.
            return None

    def _to_response(self, state: WorkflowState) -> dict[str, Any]:
        if state.status == WorkflowStatus.PAUSED:
            return {
                "request_id": state.request_id,
                "status": state.run_status or state.status.value,
                "pause_reason": state.pause_reason,
                "current_agent": state.current_agent,
                "route_history": state.route_history,
                "step_status": state.step_status,
                "events": state.events,
                "warnings": state.warnings,
                "errors": state.errors,
            }
        if state.final_output:
            return state.final_output
        return {
            "request_id": state.request_id,
            "status": state.run_status or state.status.value,
            "errors": state.errors,
            "warnings": state.warnings,
        }
