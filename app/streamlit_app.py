from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on the path so `src` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st

from src.utils.document_parser import extract_text_from_pdf_bytes, extract_text_from_txt_bytes
from src.utils.mock_data import SAMPLE_LEGAL_TEXT
from src.utils.pdf_export import build_translated_document_pdf
from src.workflow.orchestrator import WorkflowOrchestrator

WORKFLOW_STEPS = ["intake", "planner", "execution", "qa", "judge", "delivery"]


st.set_page_config(
    page_title="Agentic Translation Workflow",
    page_icon="AT",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,500;9..144,700&display=swap');

:root {
  --ink: #102a43;
  --accent: #177e89;
  --accent-2: #f18f01;
  --surface: #f3f7f8;
  --surface-2: #e5eef2;
  --ok: #1f7a4f;
  --warn: #b45309;
  --fail: #b42318;
}

html, body, [class*="css"] {
  font-family: "IBM Plex Sans", sans-serif;
  color: var(--ink);
}

.hero {
  border-radius: 20px;
  padding: 20px 24px;
  background:
    radial-gradient(circle at 12% 10%, rgba(23,126,137,0.2) 0, rgba(23,126,137,0) 25%),
    radial-gradient(circle at 90% 30%, rgba(241,143,1,0.2) 0, rgba(241,143,1,0) 30%),
    linear-gradient(135deg, #f7fbfc 0%, #fef9f1 100%);
  border: 1px solid #cadbe3;
  margin-bottom: 1rem;
}

.hero h1 {
  margin: 0;
  font-family: "Fraunces", serif;
  font-size: 2rem;
  line-height: 1.1;
  color: #0f2740 !important;
}

.tagline {
  margin-top: 0.5rem;
  font-size: 0.95rem;
  color: #28455e !important;
}

.status-chip {
  display: inline-block;
  padding: 0.32rem 0.8rem;
  border-radius: 999px;
  font-size: 0.82rem;
  border: 1px solid transparent;
  font-weight: 600;
}

.status-completed {
  background: #e7f6ee;
  color: var(--ok);
  border-color: #acd7bf;
}

.status-warning {
  background: #fff4e8;
  color: var(--warn);
  border-color: #f6c89f;
}

.status-failed {
  background: #fdebec;
  color: var(--fail);
  border-color: #f5b6bb;
}

.panel {
  border: 1px solid #d6e2e8;
  background: var(--surface);
  border-radius: 14px;
  padding: 12px 14px;
}

.panel h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.95rem;
  color: #18344d !important;
}

.settings-note {
  background: var(--surface-2);
  border: 1px solid #c7d8e2;
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 0.86rem;
  color: #38586f;
}

[data-testid="stMetric"] {
  background: #f6fafc;
  border: 1px solid #d8e8f0;
  padding: 10px;
  border-radius: 12px;
  font-size: 0.82rem;
}

/* Fix dark-theme contrast issues inside light metric cards */
[data-testid="stMetric"] [data-testid="stMetricLabel"],
[data-testid="stMetric"] [data-testid="stMetricValue"],
[data-testid="stMetric"] [data-testid="stMetricDelta"],
[data-testid="stMetric"] label,
[data-testid="stMetric"] div,
[data-testid="stMetric"] span {
  color: #15354f !important;
}

[data-testid="stFileUploaderDropzone"] {
  background: #f5fafb !important;
  border: 1px dashed #8ea8b7 !important;
}

[data-testid="stFileUploaderDropzone"] * {
  color: #17364f !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] span {
  color: #17364f !important;
}

@media (max-width: 900px) {
  .hero h1 {
    font-size: 1.55rem;
  }
  .tagline {
    font-size: 0.9rem;
  }
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="hero">
  <h1>Agentic Translation Workflow</h1>
  <div class="tagline">Master/Worker orchestration with live step tracking, QA + Judge validation, SLA visibility, and export-ready reports.</div>
</div>
""",
    unsafe_allow_html=True,
)


def _default_step_status() -> dict[str, str]:
    return {step: "pending" for step in WORKFLOW_STEPS}


def _init_session_state() -> None:
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("last_request", None)
    st.session_state.setdefault("doc_text_input", "")
    st.session_state.setdefault("page_count_input", 3)
    st.session_state.setdefault("uploaded_text_cache", "")
    st.session_state.setdefault("uploaded_pages_cache", 1)
    st.session_state.setdefault("uploaded_filename", "")
    st.session_state.setdefault("queued_doc_text", None)
    st.session_state.setdefault("queued_page_count", None)
    st.session_state.setdefault("live_step_status", _default_step_status())
    st.session_state.setdefault("live_events", [])
    st.session_state.setdefault("live_run_active", False)


def _queue_input_update(text: str, page_count: int) -> None:
    st.session_state.queued_doc_text = text
    st.session_state.queued_page_count = max(1, int(page_count))


def _apply_queued_input_updates() -> None:
    queued_text = st.session_state.get("queued_doc_text")
    queued_page_count = st.session_state.get("queued_page_count")

    if queued_text is not None:
        st.session_state.doc_text_input = queued_text
        st.session_state.queued_doc_text = None
    if queued_page_count is not None:
        st.session_state.page_count_input = max(1, int(queued_page_count))
        st.session_state.queued_page_count = None


def _status_class(status: str) -> str:
    normalized = (status or "").lower()
    if normalized == "completed":
        return "status-completed"
    if normalized in {"completed_with_warnings", "paused", "in_progress"}:
        return "status-warning"
    return "status-failed"


def _render_step_table(placeholder, step_status: dict[str, str]) -> None:
    rows = []
    for step in WORKFLOW_STEPS:
        rows.append({"step": step, "status": step_status.get(step, "pending")})
    placeholder.table(rows)


def _render_event_table(placeholder, events: list[dict]) -> None:
    if not events:
        placeholder.info("No events yet.")
        return
    trimmed = events[-10:]
    rows = []
    for event in trimmed:
        rows.append(
            {
                "time": event.get("timestamp", "")[-8:],
                "step": event.get("step", ""),
                "status": event.get("status", ""),
                "level": event.get("level", ""),
                "message": event.get("message", ""),
            }
        )
    placeholder.table(rows)


def _progress_from_steps(step_status: dict[str, str]) -> float:
    total = len(WORKFLOW_STEPS)
    completed = sum(1 for status in step_status.values() if status == "completed")
    in_progress = sum(1 for status in step_status.values() if status == "in_progress")
    return min(1.0, (completed + (0.5 * in_progress)) / max(1, total))


_init_session_state()
_apply_queued_input_updates()

with st.sidebar:
    st.subheader("Execution Settings")
    env_file_exists = Path(".env").exists()
    if not env_file_exists:
        st.warning("`.env` not found. `.env.example` is template-only and not loaded at runtime.")

    use_real_llm = st.checkbox(
        "Use Gemini (real LLM)",
        value=False,
        help="Enable real translation through Gemini API.",
    )
    if use_real_llm and not env_file_exists:
        st.error("Create `.env` with GOOGLE_API_KEY to use real Gemini translation.")

    parallel_execution = st.checkbox(
        "Enable parallel chunk execution",
        value=True,
        help="Translates paragraph chunks concurrently for lower latency.",
    )
    force_qa_fail_once = st.checkbox(
        "Force first QA failure (demo retry)",
        value=False,
        help="Testing mode: intentionally fails initial QA to show retry routing.",
    )
    auto_approve = st.checkbox(
        "Auto-approve HITL pauses",
        value=True,
        help="If off, workflow can pause when planner requests manual approval.",
    )
    st.divider()
    st.caption("Model target: `gemini-2.5-flash`")
    st.markdown(
        """
        <div class="settings-note">
          Production defaults: real LLM on, forced QA failure off, and manual HITL approvals where needed.
        </div>
        """,
        unsafe_allow_html=True,
    )


tab_new, tab_monitor, tab_results, tab_arch = st.tabs(
    ["New Workflow", "Monitor", "Results", "Architecture"]
)

with tab_new:
    left_col, right_col = st.columns([1.8, 1.2], gap="large")

    with left_col:
        c1, c2 = st.columns(2)
        with c1:
            source_language = st.selectbox("Source language", ["en", "es", "fr", "de"], index=0)
            target_language = st.selectbox("Target language", ["es", "en", "de", "fr"], index=0)
        with c2:
            document_type = st.selectbox("Document type", ["legal", "medical", "technical"], index=0)
            st.caption("If your document is non-legal, set Document type to non-legal (medical/technical).")
            st.number_input(
                "Page count",
                min_value=1,
                max_value=500,
                key="page_count_input",
            )

        st.text_area(
            "Document text",
            key="doc_text_input",
            height=300,
            placeholder="Paste text here, or upload PDF/TXT and apply extracted text.",
        )

        b1, b2, b3 = st.columns([1.1, 1, 1.4])
        with b1:
            if st.button("Load sample", use_container_width=True):
                _queue_input_update(SAMPLE_LEGAL_TEXT, 3)
                st.rerun()
        with b2:
            if st.button("Clear text", use_container_width=True):
                _queue_input_update("", int(st.session_state.page_count_input))
                st.rerun()
        with b3:
            start_clicked = st.button("Run workflow", type="primary", use_container_width=True)

    with right_col:
        st.markdown("<div class='panel'><h4>Upload Document</h4></div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload PDF or TXT",
            type=["pdf", "txt"],
            accept_multiple_files=False,
            help="Upload your own document; extracted content can be injected into workflow input.",
        )

        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_bytes = uploaded_file.getvalue()
            extracted_text = ""
            extracted_pages = 1
            parse_error = None

            try:
                if file_name.lower().endswith(".pdf"):
                    extracted_text, extracted_pages = extract_text_from_pdf_bytes(file_bytes)
                else:
                    extracted_text = extract_text_from_txt_bytes(file_bytes)
            except Exception as exc:
                parse_error = str(exc)

            if parse_error:
                st.error(f"Could not parse `{file_name}`: {parse_error}")
            elif not extracted_text.strip():
                st.warning(f"`{file_name}` was parsed but no text was extracted.")
            else:
                st.session_state.uploaded_text_cache = extracted_text
                st.session_state.uploaded_pages_cache = extracted_pages
                st.session_state.uploaded_filename = file_name

                st.success(f"Loaded `{file_name}`")
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Pages", extracted_pages)
                with m2:
                    st.metric("Words", len(extracted_text.split()))
                with m3:
                    st.metric("Chars", len(extracted_text))

                with st.expander("Preview extracted text", expanded=False):
                    st.text_area(
                        "Extracted",
                        value=extracted_text[:3000],
                        height=180,
                        disabled=True,
                        label_visibility="collapsed",
                    )

                if st.button("Use extracted text in workflow", use_container_width=True):
                    _queue_input_update(extracted_text, extracted_pages)
                    st.rerun()
        else:
            st.info("No file uploaded. You can still paste text manually.")

    st.markdown("### Live Tracking")
    progress_placeholder = st.empty()
    step_table_placeholder = st.empty()
    event_table_placeholder = st.empty()
    _render_step_table(step_table_placeholder, st.session_state.live_step_status)
    _render_event_table(event_table_placeholder, st.session_state.live_events)

    if start_clicked:
        raw_text = st.session_state.doc_text_input.strip()
        if not raw_text:
            st.error("Document text is empty. Paste text or upload a file first.")
            st.stop()

        st.session_state.live_step_status = _default_step_status()
        st.session_state.live_events = []
        st.session_state.live_run_active = True

        request_payload = {
            "source_language": source_language,
            "target_language": target_language,
            "document_type": document_type,
            "page_count": int(st.session_state.page_count_input),
            "raw_text": raw_text,
            "max_retries": 1,
            "parallel_execution": parallel_execution,
            "force_qa_fail_once": force_qa_fail_once,
        }
        st.session_state.last_request = request_payload

        def progress_callback(event: dict, snapshot: dict) -> None:
            st.session_state.live_step_status = snapshot.get("step_status", _default_step_status())
            st.session_state.live_events.append(event)
            st.session_state.live_events = st.session_state.live_events[-120:]

            progress = _progress_from_steps(st.session_state.live_step_status)
            progress_placeholder.progress(
                progress,
                text=f"Workflow progress: {int(progress * 100)}% | Current: {snapshot.get('current_agent') or 'n/a'}",
            )
            _render_step_table(step_table_placeholder, st.session_state.live_step_status)
            _render_event_table(event_table_placeholder, st.session_state.live_events)

        with st.spinner("Executing workflow..."):
            orchestrator = WorkflowOrchestrator(use_real_llm=use_real_llm)
            st.session_state.last_result = orchestrator.execute_workflow_sync(
                request=request_payload,
                auto_approve=auto_approve,
                progress_callback=progress_callback,
            )

        st.session_state.live_run_active = False
        final_status = st.session_state.last_result.get("status", "unknown")
        if final_status in {"failed", "paused"}:
            st.error(f"Workflow ended with status: {final_status}")
        elif final_status == "completed_with_warnings":
            st.warning("Workflow completed with warnings. Review monitor details.")
        else:
            st.success("Workflow finished successfully.")

with tab_monitor:
    result = st.session_state.last_result
    live_step_status = st.session_state.live_step_status
    live_events = st.session_state.live_events

    if not result and not live_events:
        st.info("Run a workflow to view monitoring data.")
    else:
        status = (result or {}).get("status", "in_progress" if st.session_state.live_run_active else "unknown")
        css_class = _status_class(status)
        st.markdown(
            f"<span class='status-chip {css_class}'>Status: {status.upper()}</span>",
            unsafe_allow_html=True,
        )

        metadata = (result or {}).get("metadata", {})
        step_status = metadata.get("step_status", live_step_status)
        events = metadata.get("events", live_events)
        warnings = metadata.get("warnings", (result or {}).get("warnings", []))
        errors = metadata.get("errors", (result or {}).get("errors", []))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Retry count", metadata.get("retry_count", (result or {}).get("retry_count", 0)))
        with c2:
            st.metric("Processing time (s)", round(float(metadata.get("processing_time_seconds", 0.0)), 2))
        with c3:
            st.metric("Warnings", len(warnings))
        with c4:
            st.metric("Errors", len(errors))

        st.subheader("Step status")
        step_rows = [{"step": step, "status": step_status.get(step, "pending")} for step in WORKFLOW_STEPS]
        st.table(step_rows)

        st.subheader("Event timeline")
        _render_event_table(st.empty(), events)

        agent_timings = metadata.get("agent_timings", {})
        if agent_timings:
            labels = list(agent_timings.keys())
            values = list(agent_timings.values())
            fig = go.Figure(
                go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color=["#177e89", "#f18f01", "#177e89", "#f18f01", "#5f6caf", "#177e89"],
                )
            )
            fig.update_layout(
                title="Per-agent execution time",
                xaxis_title="Seconds",
                yaxis_title="Agent",
                height=340,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        qa_report = (result or {}).get("qa_report", {})
        failed_checks = qa_report.get("failed_checks", [])
        if failed_checks:
            st.error("QA failed checks: " + ", ".join(failed_checks))

        judge_report = (result or {}).get("judge_report", {})
        judge_action = str(judge_report.get("action", "")).lower()
        if judge_action and judge_action != "accept":
            st.warning(
                f"Judge action: {judge_action} | score={judge_report.get('score', 'n/a')} | {judge_report.get('rationale', '')}"
            )

        if warnings:
            st.warning("\n".join(warnings))
        if errors:
            st.error("\n".join(errors))

with tab_results:
    result = st.session_state.last_result
    if not result:
        st.info("No workflow output yet.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Original")
            st.text_area("Original text", value=result.get("original_text", ""), height=350, disabled=True)
        with c2:
            st.subheader("Translated")
            st.text_area("Translated text", value=result.get("translated_text", ""), height=350, disabled=True)

        st.subheader("QA Report")
        st.json(result.get("qa_report", {}))

        st.subheader("Judge Report")
        st.json(result.get("judge_report", {}))

        runtime_warnings = result.get("metadata", {}).get("warnings", [])
        if runtime_warnings:
            st.warning("\n".join(runtime_warnings))

        st.download_button(
            label="Download translated text (.txt)",
            data=result.get("translated_text", ""),
            file_name="translated_text.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.download_button(
            label="Download JSON output",
            data=json.dumps(result, indent=2),
            file_name="translation_output.json",
            mime="application/json",
            use_container_width=True,
        )

        try:
            pdf_bytes = build_translated_document_pdf(result)
            st.download_button(
                label="Download translated document (.pdf)",
                data=pdf_bytes,
                file_name="translated_document.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as exc:
            st.info(f"PDF export unavailable: {exc}")

with tab_arch:
    st.markdown(
        """
        `Master Agent` supervises state, routing, retries, and emits live events.
        `Worker Agents` are specialized executors: Intake, Planner, Execution, QA, Judge, Delivery.
        """
    )
    st.markdown(
        """
        <div class="panel">
          <h4>Branching Rules</h4>
          Intake -> Planner -> Execution -> QA -> Judge -> Delivery
          <br/>QA fail + retry budget: route back to Execution.
          <br/>Judge action retry + budget: route back to Execution.
          <br/>Any warnings/errors are preserved and surfaced in final report metadata.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.graphviz_chart(
        """
        digraph Workflow {
            rankdir=LR;
            node [shape=box, style=rounded];
            Master [label="Master Agent", color="#f18f01"];
            Intake [label="Intake"];
            Planner [label="Planner"];
            Execution [label="Execution"];
            QA [label="QA"];
            Judge [label="Judge"];
            Delivery [label="Delivery"];

            Master -> Intake;
            Intake -> Planner;
            Planner -> Execution;
            Execution -> QA;
            QA -> Judge [label="pass/last fail"];
            QA -> Execution [label="fail + retry", color="red"];
            Judge -> Execution [label="judge retry", color="red"];
            Judge -> Delivery [label="accept/review"];
            Delivery -> Master [label="complete"];
        }
        """
    )

save_path = Path("examples/example_outputs/latest_streamlit_output.json")
if st.session_state.last_result:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_text(json.dumps(st.session_state.last_result, indent=2), encoding="utf-8")
