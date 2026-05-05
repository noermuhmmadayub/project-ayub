"""Smoke test retrieval RAG: cetak sumber teratas untuk beberapa query uji."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.config.settings import get_settings
from src.services.rag import SimpleRAG

SAMPLE_QUERIES = [
    "beasiswa STT Nurul Fikri",
    "program studi teknik informatika",
    "kontak kampus",
]


def main() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        print("GEMINI_API_KEY tidak diatur.")
        sys.exit(1)
    rag = SimpleRAG(
        knowledge_dir=str(ROOT / "data" / "knowledge"),
        api_key=settings.gemini_api_key,
        embedding_model_name=settings.embedding_model_name,
        index_path=str(ROOT / "data" / "rag_index.json"),
    )
    for q in SAMPLE_QUERIES:
        rows = rag.retrieve(q, top_k=3)
        print(f"\nQuery: {q!r}")
        if not rows:
            print("  (tidak ada hasil)")
            continue
        for r in rows:
            print(f"  - {r.source} | score={r.score}")


if __name__ == "__main__":
    main()
