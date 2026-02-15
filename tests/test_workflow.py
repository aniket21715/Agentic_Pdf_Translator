import asyncio

from src.utils.mock_data import sample_request
from src.workflow.orchestrator import WorkflowOrchestrator


def test_workflow_end_to_end_completes():
    orchestrator = WorkflowOrchestrator(use_real_llm=False)
    result = asyncio.run(orchestrator.execute_workflow(sample_request(), auto_approve=True))

    assert result["status"] == "completed"
    assert result["translated_text"]
    assert "qa_report" in result
    assert "judge_report" in result
    assert "metadata" in result
    assert "judge" in result["metadata"]["step_status"]


def test_workflow_can_pause_for_human_approval():
    orchestrator = WorkflowOrchestrator(use_real_llm=False)
    request = sample_request()
    request["page_count"] = 20
    result = asyncio.run(orchestrator.execute_workflow(request, auto_approve=False))

    assert result["status"] == "paused"
    assert "pause_reason" in result
