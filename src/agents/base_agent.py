from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.models.workflow_state import WorkflowState
from src.utils.logger import setup_logger


class BaseWorkerAgent(ABC):
    """Base class for all worker agents. Workers never orchestrate other workers."""

    def __init__(self, name: str, llm: Any | None = None) -> None:
        self.name = name
        self.llm = llm
        self.logger = setup_logger(name)

    @abstractmethod
    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        raise NotImplementedError

    def _log_execution(self, state: WorkflowState, action: str) -> None:
        self.logger.info("[%s] %s", state.request_id, action)
