from pathlib import Path
import asyncio

from src.utils.mock_data import sample_request
from src.workflow.orchestrator import WorkflowOrchestrator


def test_retry_logic_runs_after_qa_failure():
    orchestrator = WorkflowOrchestrator(use_real_llm=False)
    request = sample_request()
    request["force_qa_fail_once"] = True

    result = asyncio.run(orchestrator.execute_workflow(request, auto_approve=True))

    assert result["status"] in {"completed", "completed_with_warnings"}
    assert result["metadata"]["retry_count"] == 1
    assert result["qa_report"]["status"] == "pass"


def test_state_snapshot_saved():
    orchestrator = WorkflowOrchestrator(use_real_llm=False)
    result = asyncio.run(orchestrator.execute_workflow(sample_request(), auto_approve=True))

    request_id = result["request_id"]
    snapshot = Path("logs/states") / f"{request_id}.json"
    assert snapshot.exists()
