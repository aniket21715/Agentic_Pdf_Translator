import asyncio

from src.agents.delivery_agent import DeliveryAgent
from src.agents.execution_agent import ExecutionAgent
from src.agents.intake_agent import IntakeAgent
from src.agents.planner_agent import PlannerAgent
from src.agents.qa_agent import QAAgent
from src.models.workflow_state import WorkflowState
from src.utils.mock_data import SAMPLE_LEGAL_TEXT


def _base_state() -> WorkflowState:
    return WorkflowState(
        source_language="en",
        target_language="es",
        document_type="legal",
        page_count=3,
        raw_text=SAMPLE_LEGAL_TEXT,
        parallel_execution=True,
    )


def test_agent_pipeline_happy_path():
    state = _base_state()

    intake = IntakeAgent("intake")
    planner = PlannerAgent("planner")
    execution = ExecutionAgent("execution")
    qa = QAAgent("qa")
    delivery = DeliveryAgent("delivery")

    async def run_pipeline():
        state.normalized_request = await intake.execute(state)
        planner_result = await planner.execute(state)
        state.execution_plan = planner_result["plan"]
        state.requires_approval = planner_result["requires_approval"]

        execution_result = await execution.execute(state)
        state.translation_output = execution_result["translation"]

        qa_result = await qa.execute(state)
        state.qa_result = qa_result

        delivery_result = await delivery.execute(state)
        return qa_result, delivery_result

    qa_result, delivery_result = asyncio.run(run_pipeline())

    assert state.normalized_request["word_count"] > 0
    assert len(state.execution_plan) >= 3
    assert state.translation_output
    assert "quality_score" in qa_result
    assert delivery_result["request_id"] == state.request_id
