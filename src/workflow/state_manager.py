from __future__ import annotations

import json
from pathlib import Path

from src.models.workflow_state import WorkflowState


class StateManager:
    def __init__(self, state_dir: str = "logs/states") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: WorkflowState) -> None:
        state_path = self.state_dir / f"{state.request_id}.json"
        state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    def load(self, request_id: str) -> WorkflowState | None:
        state_path = self.state_dir / f"{request_id}.json"
        if not state_path.exists():
            return None
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        return WorkflowState(**payload)
