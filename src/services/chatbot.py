from __future__ import annotations

import time
from typing import Dict, Iterable, List

from google import genai

from src.config.settings import SYSTEM_INSTRUCTION, Settings
from src.services.rag import SimpleRAG


class GeminiChatbotService:
    def __init__(self, settings: Settings, rag: SimpleRAG) -> None:
        self.settings = settings
        self.rag = rag
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self._last_sources: List[str] = []

    @staticmethod
    def _build_history_text(messages: List[Dict[str, str]]) -> str:
        history_lines: List[str] = []
        for message in messages:
            role = "Pengguna" if message["role"] == "user" else "Asisten"
            history_lines.append(f"{role}: {message['content']}")
        return "\n".join(history_lines)

    def stream_answer(self, user_prompt: str, history: List[Dict[str, str]]) -> Iterable[str]:
        retrievals = self.rag.retrieve(user_prompt, top_k=3)
        self._last_sources = list(dict.fromkeys(item.source for item in retrievals))
        rag_context = self.rag.build_context(user_prompt, top_k=3, retrievals=retrievals)
        enriched_prompt = user_prompt
        if rag_context:
            enriched_prompt = (
                f"{rag_context}\n\n"
                "Gunakan konteks di atas hanya jika relevan dan faktual. "
                "Jika konteks tidak cukup, jelaskan keterbatasan jawaban.\n\n"
                f"Pertanyaan pengguna:\n{user_prompt}"
            )
        history_text = self._build_history_text(history)
        final_prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"Riwayat percakapan:\n{history_text if history_text else '(kosong)'}\n\n"
            f"{enriched_prompt}"
        )

        models = [self.settings.model_name] + (self.settings.fallback_models or [])
        seen: set[str] = set()
        ordered_models: List[str] = []
        for model in models:
            if model not in seen:
                ordered_models.append(model)
                seen.add(model)

        last_error: Exception | None = None
        for model_name in ordered_models:
            for attempt in range(self.settings.max_retry_attempts + 1):
                try:
                    stream = self.client.models.generate_content_stream(
                        model=model_name,
                        contents=final_prompt,
                    )
                    for chunk in stream:
                        text = getattr(chunk, "text", "") or ""
                        if text.strip():
                            yield text
                    return
                except Exception as exc:
                    last_error = exc
                    message = str(exc).upper()
                    is_capacity_issue = "503" in message or "UNAVAILABLE" in message or "HIGH DEMAND" in message
                    if is_capacity_issue and attempt < self.settings.max_retry_attempts:
                        time.sleep(self.settings.retry_delay_seconds)
                        continue
                    break

        if last_error is not None:
            raise last_error

    def get_last_sources(self) -> List[str]:
        return self._last_sources.copy()
