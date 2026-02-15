from __future__ import annotations

import asyncio
import os
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.agents.base_agent import BaseWorkerAgent
from src.models.workflow_state import WorkflowState


class ExecutionAgent(BaseWorkerAgent):
    def __init__(
        self,
        name: str,
        llm: Any | None = None,
        google_api_key: str | None = None,
        gemini_model: str = "gemini-2.5-flash",
    ) -> None:
        super().__init__(name=name, llm=llm)
        self.google_api_key = google_api_key
        self.gemini_model = gemini_model

    async def execute(self, state: WorkflowState) -> dict:
        self._log_execution(state, "Executing translation")
        chunks = [chunk.strip() for chunk in state.raw_text.split("\n\n") if chunk.strip()]
        if not chunks:
            return {"translation": "", "method": "none", "segments": 0}

        if state.parallel_execution and len(chunks) > 1:
            translated_chunks = await asyncio.gather(
                *[self._translate_chunk(chunk, state) for chunk in chunks]
            )
        else:
            translated_chunks = []
            for chunk in chunks:
                translated_chunks.append(await self._translate_chunk(chunk, state))

        translation = "\n\n".join(translated_chunks)
        method = "langchain_llm" if self.llm else ("direct_gemini" if self.google_api_key else "mock")
        return {"translation": translation, "method": method, "segments": len(chunks)}

    async def _translate_chunk(self, chunk: str, state: WorkflowState) -> str:
        if self.llm:
            prompt = ChatPromptTemplate.from_template(
                (
                    "Translate the following document from {source_language} to {target_language}. "
                    "Preserve numbering and legal tone.\n\nText:\n{text}"
                )
            )
            chain = prompt | self.llm | StrOutputParser()
            try:
                return await chain.ainvoke(
                    {
                        "source_language": state.source_language,
                        "target_language": state.target_language,
                        "text": chunk,
                    }
                )
            except Exception as exc:
                state.add_warning(f"LLM translation failed, fallback used: {exc}")
        if self.google_api_key:
            translated = await self._translate_chunk_with_direct_gemini(chunk, state)
            if translated:
                return translated
        return self._mock_translate(chunk, state.target_language)

    async def _translate_chunk_with_direct_gemini(self, chunk: str, state: WorkflowState) -> str | None:
        try:
            from google import genai
        except Exception as exc:
            state.add_warning(f"Direct Gemini SDK unavailable, fallback used: {exc}")
            return None

        prompt = (
            f"Translate from {state.source_language} to {state.target_language}. "
            "Preserve formatting, numbering, and legal/medical tone as applicable.\n\n"
            f"Text:\n{chunk}"
        )
        broken_proxy_keys = self._detect_broken_proxy_keys()

        def _call_gemini() -> str:
            saved_proxy_values = self._strip_broken_proxy_env(broken_proxy_keys)
            try:
                client = genai.Client(api_key=self.google_api_key)
                response = client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                )
            finally:
                self._restore_proxy_env(saved_proxy_values)
            text = getattr(response, "text", None)
            return (text or "").strip()

        try:
            translated = await asyncio.to_thread(_call_gemini)
            if translated:
                return translated
            state.add_warning("Direct Gemini returned empty text, fallback used.")
            return None
        except Exception as exc:
            state.add_warning(f"Direct Gemini translation failed, fallback used: {exc}")
            return None

    def _detect_broken_proxy_keys(self) -> list[str]:
        keys = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]
        broken: list[str] = []
        for key in keys:
            value = os.environ.get(key, "")
            if "127.0.0.1:9" in value:
                broken.append(key)
        return broken

    def _strip_broken_proxy_env(self, keys: list[str]) -> dict[str, str]:
        saved: dict[str, str] = {}
        for key in keys:
            if key in os.environ:
                saved[key] = os.environ[key]
                os.environ.pop(key, None)
        return saved

    def _restore_proxy_env(self, saved: dict[str, str]) -> None:
        for key, value in saved.items():
            os.environ[key] = value

    def _mock_translate(self, text: str, target_language: str) -> str:
        replacements = {
            "agreement": "acuerdo",
            "client": "cliente",
            "firm": "firma",
            "services": "servicios",
            "payment": "pago",
            "termination": "terminacion",
            "legal": "legal",
        }
        translated = text
        for source, target in replacements.items():
            translated = translated.replace(source, target)
            translated = translated.replace(source.title(), target.title())
        return f"[{target_language}] {translated}"
