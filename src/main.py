from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config.settings import get_settings
from src.workflow.orchestrator import WorkflowOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agentic translation workflow runner")
    parser.add_argument("--input-file", type=str, default="examples/sample_document.txt")
    parser.add_argument("--source-language", type=str, default=None)
    parser.add_argument("--target-language", type=str, default=None)
    parser.add_argument("--document-type", type=str, default=None)
    parser.add_argument("--page-count", type=int, default=3)
    parser.add_argument("--use-real-llm", action="store_true")
    parser.add_argument("--require-approval", action="store_true")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--force-qa-fail-once", action="store_true")
    parser.add_argument("--output-file", type=str, default="examples/example_outputs/latest_output.json")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    input_path = Path(args.input_file)
    raw_text = input_path.read_text(encoding="utf-8")

    request = {
        "source_language": args.source_language or settings.default_source_language,
        "target_language": args.target_language or settings.default_target_language,
        "document_type": args.document_type or settings.default_document_type,
        "page_count": args.page_count,
        "raw_text": raw_text,
        "max_retries": settings.default_max_retries,
        "parallel_execution": args.parallel,
        "force_qa_fail_once": args.force_qa_fail_once,
    }
    orchestrator = WorkflowOrchestrator(use_real_llm=args.use_real_llm)
    response = orchestrator.execute_workflow_sync(
        request=request,
        auto_approve=not args.require_approval,
    )

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(response, indent=2), encoding="utf-8")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
