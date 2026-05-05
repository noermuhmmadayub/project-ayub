from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from typing import List, Optional

from google import genai

@dataclass(frozen=True)
class RetrievalChunk:
    source: str
    text: str
    score: int
    semantic_score: float = 0.0
    keyword_score: int = 0


class SimpleRAG:
    def __init__(
        self,
        knowledge_dir: str = "data/knowledge",
        api_key: str = "",
        embedding_model_name: str = "models/text-embedding-004",
        index_path: str = "data/rag_index.json",
    ) -> None:
        self.knowledge_dir = Path(knowledge_dir)
        self.api_key = api_key
        self.embedding_model_name = embedding_model_name
        self.index_path = Path(index_path)
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.chunks = self._load_chunks()
        self.embeddings: List[List[float]] = []
        if self.api_key and self.chunks:
            self.embeddings = self._load_or_build_embeddings()

    def _load_chunks(self) -> List[tuple[str, str]]:
        chunks: List[tuple[str, str]] = []
        if not self.knowledge_dir.exists():
            return chunks

        supported_extensions = {".txt", ".md"}
        for file_path in sorted(self.knowledge_dir.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in supported_extensions:
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                continue
            for part in self._split_text(content):
                chunks.append((file_path.name, part))
        return chunks

    def _signatures(self) -> List[str]:
        signatures: List[str] = []
        for source, text in self.chunks:
            digest = hashlib.sha1(f"{source}|{text}".encode("utf-8")).hexdigest()
            signatures.append(digest)
        return signatures

    def _load_or_build_embeddings(self) -> List[List[float]]:
        signatures = self._signatures()
        cached = self._load_cached_index()
        if cached and cached.get("signatures") == signatures:
            vectors = cached.get("embeddings", [])
            if len(vectors) == len(self.chunks):
                return vectors

        vectors = self._embed_texts([chunk_text for _, chunk_text in self.chunks])
        if vectors:
            self._write_cached_index(signatures, vectors)
        return vectors

    def _load_cached_index(self) -> Optional[dict]:
        if not self.index_path.exists():
            return None
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cached_index(self, signatures: List[str], vectors: List[List[float]]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"signatures": signatures, "embeddings": vectors}
        self.index_path.write_text(json.dumps(payload), encoding="utf-8")

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not self.client:
            return []
        try:
            vectors: List[List[float]] = []
            for text in texts:
                result = self.client.models.embed_content(
                    model=self.embedding_model_name,
                    contents=text,
                )
                embedding_object = getattr(result, "embeddings", None)
                if not embedding_object:
                    return []
                values = getattr(embedding_object[0], "values", [])
                if not values:
                    return []
                vectors.append(list(values))
            return vectors
        except Exception:
            return []

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(y * y for y in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _split_text(text: str, chunk_size: int = 700) -> List[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        return [normalized[i : i + chunk_size] for i in range(0, len(normalized), chunk_size)]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9_]{3,}", text.lower()))

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        source_substring: Optional[str] = None,
    ) -> List[RetrievalChunk]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        needle = (source_substring or "").strip().lower()

        query_embedding: List[float] = []
        if self.api_key and self.embeddings:
            query_embedding = self._embed_texts([query])
            query_embedding = query_embedding[0] if query_embedding else []

        scored: List[RetrievalChunk] = []
        for idx, (source, chunk) in enumerate(self.chunks):
            if needle and needle not in source.lower():
                continue
            chunk_tokens = self._tokenize(chunk)
            overlap = len(query_tokens.intersection(chunk_tokens))
            semantic_score = 0.0
            if query_embedding and idx < len(self.embeddings):
                semantic_score = self._cosine_similarity(query_embedding, self.embeddings[idx])

            combined_score = overlap + int(semantic_score * 100)
            if combined_score > 0:
                scored.append(
                    RetrievalChunk(
                        source=source,
                        text=chunk,
                        score=combined_score,
                        semantic_score=semantic_score,
                        keyword_score=overlap,
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def force_rebuild_embedding_cache(self) -> int:
        if self.index_path.exists():
            try:
                self.index_path.unlink()
            except OSError:
                pass
        self.embeddings = []
        if self.api_key and self.chunks:
            self.embeddings = self._load_or_build_embeddings()
        return len(self.embeddings)

    def build_context(
        self,
        query: str,
        top_k: int = 3,
        retrievals: Optional[List[RetrievalChunk]] = None,
    ) -> str:
        results = retrievals if retrievals is not None else self.retrieve(query=query, top_k=top_k)
        if not results:
            return ""

        lines = ["Konteks referensi eksternal (RAG):"]
        for idx, item in enumerate(results, start=1):
            lines.append(f"[{idx}] Sumber: {item.source}")
            lines.append(item.text)
        return "\n".join(lines)
