from __future__ import annotations

from datetime import datetime


class SLAMonitor:
    def __init__(self, target_seconds: int) -> None:
        self.target_seconds = target_seconds

    def elapsed_seconds(self, started_at: datetime | None, ended_at: datetime | None = None) -> float:
        if not started_at:
            return 0.0
        end = ended_at or datetime.utcnow()
        return (end - started_at).total_seconds()

    def is_breached(self, started_at: datetime | None, ended_at: datetime | None = None) -> bool:
        return self.elapsed_seconds(started_at, ended_at) > self.target_seconds
