from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable

from src.models.workflow_state import QAStatus, WorkflowState, WorkflowStatus
from src.utils.logger import setup_logger
from src.utils.metrics import SLAMonitor
from src.workflow.routing import determine_next_step
from src.workflow.state_manager import StateManager


class MasterAgent:
    """
    Supervisor that orchestrates worker agents.
    It is the only agent that controls workflow routing.
    """

    def __init__(self, worker_agents: dict[str, Any], sla_seconds: int = 120) -> None:
        self.worker_agents = worker_agents
        self.logger = setup_logger("master_agent")
        self.state_manager = StateManager()
        self.sla_monitor = SLAMonitor(sla_seconds)

    async def orchestrate(
        self,
        initial_request: dict,
        auto_approve: bool = True,
        progress_callback: Callable[[dict, dict], None] | None = None,
    ) -> WorkflowState:
        state = WorkflowState(**initial_request)
        state.start_time = datetime.utcnow()
        state.status = WorkflowStatus.IN_PROGRESS
        state.run_status = WorkflowStatus.IN_PROGRESS.value
        state.step_status = {step: "pending" for step in self.worker_agents.keys()}
        self.state_manager.save(state)
        self.logger.info("Starting workflow %s", state.request_id)
        self._emit_event(
            state,
            step="workflow",
            status="started",
            message="Workflow started.",
            level="info",
            progress_callback=progress_callback,
        )

        current_step = "intake"
        previous_step: str | None = None
        try:
            while current_step not in {"end", "delivery"}:
                if current_step == "pause_for_approval":
                    if auto_approve:
                        state.approval_granted = True
                        state.status = WorkflowStatus.IN_PROGRESS
                        state.run_status = WorkflowStatus.IN_PROGRESS.value
                        state.pause_reason = None
                        self._emit_event(
                            state,
                            step="approval",
                            status="auto_approved",
                            message="Approval gate auto-approved by configuration.",
                            level="info",
                            progress_callback=progress_callback,
                        )
                        current_step = "execution"
                        continue
                    state.status = WorkflowStatus.PAUSED
                    state.run_status = WorkflowStatus.PAUSED.value
                    state.pause_reason = "Awaiting human approval"
                    self._emit_event(
                        state,
                        step="approval",
                        status="paused",
                        message=state.pause_reason,
                        level="warning",
                        progress_callback=progress_callback,
                    )
                    self.state_manager.save(state)
                    return state

                if (
                    current_step == "execution"
                    and previous_step in {"qa", "judge"}
                    and self._retry_condition(previous_step, state)
                    and state.retry_count < state.max_retries
                ):
                    state.retry_count += 1
                    retry_message = f"Retrying translation, attempt {state.retry_count}"
                    state.add_warning(retry_message)
                    self._emit_event(
                        state,
                        step="execution",
                        status="retry",
                        message=retry_message,
                        level="warning",
                        progress_callback=progress_callback,
                    )

                state.route_history.append(current_step)
                state = await self._execute_step(current_step, state, progress_callback=progress_callback)
                self.state_manager.save(state)

                if self.sla_monitor.is_breached(state.start_time):
                    sla_warning = "SLA threshold exceeded"
                    if sla_warning not in state.warnings:
                        state.add_warning(sla_warning)
                        self._emit_event(
                            state,
                            step="workflow",
                            status="sla_warning",
                            message=sla_warning,
                            level="warning",
                            progress_callback=progress_callback,
                        )

                previous_step = current_step
                current_step = determine_next_step(current_step, state)

            if current_step == "delivery":
                state.route_history.append(current_step)
                state.status = WorkflowStatus.COMPLETED
                state.end_time = datetime.utcnow()
                state.run_status = self._derive_run_status(state)
                state = await self._execute_step("delivery", state, progress_callback=progress_callback)
                self.state_manager.save(state)

            state.status = WorkflowStatus.COMPLETED
            state.end_time = state.end_time or datetime.utcnow()
            state.run_status = self._derive_run_status(state)
            self._emit_event(
                state,
                step="workflow",
                status=state.run_status,
                message=f"Workflow finished with status: {state.run_status}",
                level="info",
                progress_callback=progress_callback,
            )
            self.state_manager.save(state)
            return state
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.end_time = datetime.utcnow()
            state.run_status = WorkflowStatus.FAILED.value
            state.add_error(str(exc))
            self._emit_event(
                state,
                step=state.current_agent or "workflow",
                status="failed",
                message=str(exc),
                level="error",
                progress_callback=progress_callback,
            )
            self.state_manager.save(state)
            self.logger.exception("Workflow failed: %s", exc)
            return state

    async def _execute_step(
        self,
        agent_name: str,
        state: WorkflowState,
        progress_callback: Callable[[dict, dict], None] | None = None,
    ) -> WorkflowState:
        if agent_name not in self.worker_agents:
            raise ValueError(f"Unknown agent: {agent_name}")

        state.current_agent = agent_name
        state.set_step_status(agent_name, "in_progress")
        self._emit_event(
            state,
            step=agent_name,
            status="in_progress",
            message=f"{agent_name} started.",
            level="info",
            progress_callback=progress_callback,
        )

        started = time.perf_counter()
        try:
            result = await self.worker_agents[agent_name].execute(state)
        except Exception as exc:
            state.set_step_status(agent_name, "failed")
            self._emit_event(
                state,
                step=agent_name,
                status="failed",
                message=str(exc),
                level="error",
                progress_callback=progress_callback,
            )
            raise

        elapsed = time.perf_counter() - started
        state.agent_timings[agent_name] = elapsed
        self._merge_result(state, agent_name, result)
        state.set_step_status(agent_name, "completed")
        self._emit_event(
            state,
            step=agent_name,
            status="completed",
            message=f"{agent_name} completed in {elapsed:.2f}s.",
            level="info",
            progress_callback=progress_callback,
        )
        if agent_name == "delivery":
            self._refresh_delivery_metadata(state)
        return state

    def _merge_result(self, state: WorkflowState, agent_name: str, result: dict) -> None:
        if agent_name == "intake":
            state.normalized_request = result
        elif agent_name == "planner":
            state.execution_plan = result.get("plan", [])
            state.requires_approval = result.get("requires_approval", False)
            if result.get("approval_reason"):
                state.pause_reason = result["approval_reason"]
        elif agent_name == "execution":
            state.translation_output = result.get("translation", "")
            state.translation_method = result.get("method")
            if state.translation_method == "mock" and state.requested_real_llm:
                state.add_warning("Mock translation path used.")
        elif agent_name == "qa":
            state.qa_result = result
            if self._qa_failed(state):
                state.add_warning("QA check failed. Workflow may retry or require review.")
        elif agent_name == "judge":
            state.judge_result = result
            action = str(result.get("action", "")).lower()
            if action == "retry":
                state.add_warning(
                    f"Judge requested action: {action} (score={result.get('score', 'n/a')})."
                )
        elif agent_name == "delivery":
            state.final_output = result

    def _retry_condition(self, previous_step: str | None, state: WorkflowState) -> bool:
        if previous_step == "qa":
            return self._qa_failed(state)
        if previous_step == "judge":
            return str(state.judge_result.get("action", "")).lower() == "retry"
        return False

    def _qa_failed(self, state: WorkflowState) -> bool:
        qa_status = state.qa_result.get("status")
        if isinstance(qa_status, QAStatus):
            return qa_status == QAStatus.FAIL
        return str(qa_status).lower() == QAStatus.FAIL.value

    def _derive_run_status(self, state: WorkflowState) -> str:
        if state.status == WorkflowStatus.FAILED:
            return WorkflowStatus.FAILED.value
        if state.status == WorkflowStatus.PAUSED:
            return WorkflowStatus.PAUSED.value

        qa_failed = self._qa_failed(state)
        judge_action = str(state.judge_result.get("action", "accept")).lower()
        if state.errors or state.warnings or qa_failed or judge_action != "accept" or state.retry_count > 0:
            return "completed_with_warnings"
        return WorkflowStatus.COMPLETED.value

    def _emit_event(
        self,
        state: WorkflowState,
        step: str,
        status: str,
        message: str,
        level: str,
        progress_callback: Callable[[dict, dict], None] | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "step": step,
            "status": status,
            "level": level,
            "message": message,
        }
        state.add_event(event)
        if progress_callback:
            snapshot = {
                "request_id": state.request_id,
                "current_agent": state.current_agent,
                "status": state.status.value,
                "run_status": state.run_status,
                "step_status": dict(state.step_status),
                "retry_count": state.retry_count,
                "warnings": list(state.warnings),
                "errors": list(state.errors),
            }
            progress_callback(event, snapshot)

    def _refresh_delivery_metadata(self, state: WorkflowState) -> None:
        if not state.final_output:
            return
        metadata = state.final_output.setdefault("metadata", {})
        metadata["step_status"] = dict(state.step_status)
        metadata["events"] = list(state.events)
        metadata["warnings"] = list(state.warnings)
        metadata["errors"] = list(state.errors)
        metadata["route_history"] = list(state.route_history)
        metadata["translation_method"] = state.translation_method
        state.final_output["status"] = state.run_status or state.status.value
